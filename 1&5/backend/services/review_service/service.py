import asyncio

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.json_utils import dumps, loads
from backend.models.review import ReviewTaskModel, UploadedFileModel
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.review import (
    AggregatedReview,
    ContractType,
    CustomRuleInput,
    RevisedContractResponse,
    RevisionDiffItem,
    RevisionDiffResponse,
    ReviewAnalyzeResponse,
    ReviewArtifactAvailability,
    ReviewIssuesResponse,
    ReviewMode,
    ReviewReport,
    ReviewReportResponse,
    ReviewStance,
    ReviewTaskCreateRequest,
    ReviewTaskCreateResponse,
    ReviewTaskStatus,
    ReviewTaskStatusResponse,
    ReviewWorkspace,
    UploadedFileResponse,
)
from backend.services.file_service import FileService
from backend.services.legal_api_service import DeliLegalService
from backend.services.report_service import ReportService
from backend.services.review_service.clause_classifier import ClauseClassifier
from backend.services.review_service.clause_revision_planner import ClauseRevisionPlanner
from backend.services.review_service.clause_reviewer import ClauseReviewer
from backend.services.review_service.clause_rewriter import ClauseRewriter
from backend.services.review_service.clause_segmenter import ClauseSegmenter
from backend.services.review_service.document_parser import DocumentParser
from backend.services.review_service.document_recomposer import DocumentRecomposer
from backend.services.review_service.rag_provider import LocalRegulationKnowledgeBase
from backend.services.review_service.review_aggregator import ReviewAggregator
from backend.services.review_service.review_report_builder import ReviewReportBuilder
from backend.services.review_service.review_report_renderer import ReviewReportRenderer
from backend.services.review_service.revision_diff_builder import RevisionDiffBuilder


class ReviewService:
    def __init__(
        self,
        file_service: FileService,
        report_service: ReportService,
        task_dispatcher,
        websocket_manager,
        session_factory,
        legal_api_service: DeliLegalService,
    ) -> None:
        self.repository = ReviewRepository()
        self.file_service = file_service
        self.report_service = report_service
        self.task_dispatcher = task_dispatcher
        self.websocket_manager = websocket_manager
        self.session_factory = session_factory
        self.parser = DocumentParser()
        self.segmenter = ClauseSegmenter()
        self.classifier = ClauseClassifier()
        self.knowledge_base = LocalRegulationKnowledgeBase(legal_api_service)
        self.reviewer = ClauseReviewer(self.knowledge_base)
        self.aggregator = ReviewAggregator()
        self.report_builder = ReviewReportBuilder()
        self.report_renderer = ReviewReportRenderer()
        self.revision_planner = ClauseRevisionPlanner()
        self.rewriter = ClauseRewriter()
        self.recomposer = DocumentRecomposer()
        self.diff_builder = RevisionDiffBuilder()

    def create_task(self, db: Session, payload: ReviewTaskCreateRequest) -> ReviewTaskCreateResponse:
        task = self.repository.create_task(
            db,
            review_mode=payload.review_mode.value,
            contract_type=payload.contract_type.value,
            review_stance=payload.review_stance.value,
            custom_rule_text=payload.custom_rule_text,
            custom_rule_ids_json=dumps(payload.custom_rule_ids),
        )
        return ReviewTaskCreateResponse(
            id=task.id,
            status=ReviewTaskStatus(task.status),
            created_at=task.created_at,
            review_mode=ReviewMode(task.review_mode),
            contract_type=ContractType(task.contract_type),
            review_stance=ReviewStance(task.review_stance),
        )

    def upload_file(self, db: Session, task_id: str, upload: UploadFile) -> UploadedFileResponse:
        task = self._require_task(db, task_id)
        saved_path = self.file_service.save_upload(task_id, upload)
        extracted_text = self.file_service.extract_text(saved_path)
        record = UploadedFileModel(
            task_id=task_id,
            filename=upload.filename or saved_path.name,
            content_type=upload.content_type or "application/octet-stream",
            storage_path=str(saved_path),
            extracted_text=extracted_text,
        )
        created = self.repository.create_file(db, record)
        task.status = ReviewTaskStatus.UPLOADED.value
        task.progress = 10
        self.repository.save_task(db, task)
        return UploadedFileResponse(
            id=created.id,
            task_id=created.task_id,
            filename=created.filename,
            content_type=created.content_type,
        )

    def analyze(self, db: Session, task_id: str) -> ReviewAnalyzeResponse:
        task = self._require_task(db, task_id)
        files = self.repository.list_files(db, task_id)
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded for review task")
        self.task_dispatcher.dispatch(self._run_pipeline, task_id)
        db.expire_all()
        refreshed = self._require_task(db, task_id)
        return ReviewAnalyzeResponse(
            id=refreshed.id,
            status=ReviewTaskStatus(refreshed.status),
            progress=refreshed.progress,
            review_mode=ReviewMode(refreshed.review_mode),
        )

    def get_status(self, db: Session, task_id: str) -> ReviewTaskStatusResponse:
        task = self._require_task(db, task_id)
        raw_summary = loads(task.summary_json, {})
        summary = AggregatedReview.model_validate(raw_summary) if raw_summary else None
        workspace_payload = loads(task.workspace_json, {})
        workspace = ReviewWorkspace.model_validate(workspace_payload) if workspace_payload else None
        return ReviewTaskStatusResponse(
            id=task.id,
            status=ReviewTaskStatus(task.status),
            progress=task.progress,
            review_mode=ReviewMode(task.review_mode),
            contract_type=ContractType(task.contract_type),
            review_stance=ReviewStance(task.review_stance),
            custom_rules=CustomRuleInput(ids=loads(task.custom_rule_ids_json, []), text=task.custom_rule_text),
            summary=summary,
            workspace=workspace,
            artifacts=self._artifact_availability(db, task),
        )

    def get_issues(self, db: Session, task_id: str) -> ReviewIssuesResponse:
        task = self._require_task(db, task_id)
        raw_issues = loads(task.issues_json, [])
        issues = raw_issues
        return ReviewIssuesResponse(task_id=task_id, issues=issues)

    def get_report(self, db: Session, task_id: str) -> ReviewReportResponse:
        task = self._require_task(db, task_id)
        if ReviewMode(task.review_mode) != ReviewMode.REPORT:
            raise HTTPException(status_code=400, detail="Structured review report is only available for REPORT mode")
        if task.status != ReviewTaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Review report is not ready")
        report = self.report_service.get_owner_artifact(db, "review_report", task_id, "docx")
        if not report:
            raise HTTPException(status_code=404, detail="Review report not found")
        summary = AggregatedReview.model_validate(loads(task.summary_json, {}))
        report_content = ReviewReport.model_validate(report.preview.get("report_content", {}))
        return ReviewReportResponse(report=report, review=summary, report_content=report_content)

    def get_revised_contract(self, db: Session, task_id: str) -> RevisedContractResponse:
        task = self._require_task(db, task_id)
        if ReviewMode(task.review_mode) != ReviewMode.REDLINE:
            raise HTTPException(status_code=400, detail="Revised contract is only available for REDLINE mode")
        if task.status != ReviewTaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Revised contract is not ready")
        artifact = self.report_service.get_owner_artifact(db, "review_revised", task_id, "docx")
        if not artifact:
            raise HTTPException(status_code=404, detail="Revised contract not found")
        diff_items = loads(task.diff_json, [])
        return RevisedContractResponse(
            task_id=task_id,
            review_mode=ReviewMode(task.review_mode),
            artifact=artifact,
            diff_count=len(diff_items),
        )

    def get_diff(self, db: Session, task_id: str) -> RevisionDiffResponse:
        task = self._require_task(db, task_id)
        items = [RevisionDiffItem.model_validate(item) for item in loads(task.diff_json, [])]
        return RevisionDiffResponse(task_id=task_id, review_mode=ReviewMode(task.review_mode), items=items)

    def _run_pipeline(self, task_id: str) -> None:
        db = self.session_factory()
        try:
            task = self._require_task(db, task_id)
            review_mode = ReviewMode(task.review_mode)
            contract_type = ContractType(task.contract_type)
            review_stance = ReviewStance(task.review_stance)
            custom_rules = CustomRuleInput(ids=loads(task.custom_rule_ids_json, []), text=task.custom_rule_text)
            files = self.repository.list_files(db, task_id)

            self._update_task(db, task, ReviewTaskStatus.PARSING, 15)
            parsed_files = [self.parser.parse(file) for file in files]

            self._update_task(db, task, ReviewTaskStatus.SEGMENTING, 30)
            clauses = []
            for parsed in parsed_files:
                clauses.extend(self.segmenter.segment(parsed["file_id"], parsed["text"]))

            workspace = ReviewWorkspace(
                task_id=task_id,
                review_mode=review_mode,
                contract_type=contract_type,
                review_stance=review_stance,
                custom_rules=custom_rules,
                source_filenames=[parsed["filename"] for parsed in parsed_files],
                clause_count=len(clauses),
                appendix_count=sum(1 for clause in clauses if clause.appendix_id),
            )
            task.workspace_json = dumps(workspace.model_dump())
            self.repository.save_task(db, task)

            self._update_task(db, task, ReviewTaskStatus.CLASSIFYING, 45)
            classified = [self.classifier.classify(clause) for clause in clauses]

            self._update_task(db, task, ReviewTaskStatus.REVIEWING, 65)
            issues = []
            for clause in classified:
                issues.extend(self.reviewer.review(clause, contract_type, review_stance, custom_rules))

            self._update_task(db, task, ReviewTaskStatus.AGGREGATING, 78)
            aggregated = self.aggregator.aggregate(issues)
            task.issues_json = dumps([issue.model_dump() for issue in aggregated.issues])
            task.summary_json = dumps(aggregated.model_dump())
            self.repository.save_task(db, task)

            if review_mode == ReviewMode.REPORT:
                self._render_report_mode(db, task, workspace, aggregated)
            else:
                self._render_redline_mode(db, task, workspace, clauses, aggregated)

            self._update_task(db, task, ReviewTaskStatus.COMPLETED, 100, persist=False)
            self.repository.save_task(db, task)
        except Exception:
            task = self._require_task(db, task_id)
            task.status = ReviewTaskStatus.FAILED.value
            self.repository.save_task(db, task)
            raise
        finally:
            db.close()

    def _render_report_mode(
        self,
        db: Session,
        task: ReviewTaskModel,
        workspace: ReviewWorkspace,
        aggregated: AggregatedReview,
    ) -> None:
        self._update_task(db, task, ReviewTaskStatus.RENDERING, 92)
        report = self.report_builder.build(
            filenames=workspace.source_filenames,
            aggregated=aggregated,
            contract_type=workspace.contract_type,
            review_stance=workspace.review_stance,
            custom_rule_text=workspace.custom_rules.text,
        )
        sections = self.report_renderer.build_sections(report)
        self.report_service.create_docx_report(
            db,
            "review_report",
            task.id,
            "review_report.docx",
            sections,
            preview={
                "overall_rating": aggregated.overall_rating,
                "summary": aggregated.summary,
                "report_content": report.model_dump(),
            },
        )

    def _render_redline_mode(
        self,
        db: Session,
        task: ReviewTaskModel,
        workspace: ReviewWorkspace,
        clauses,
        aggregated: AggregatedReview,
    ) -> None:
        self._update_task(db, task, ReviewTaskStatus.PLANNING, 84)
        instructions = self.revision_planner.plan(clauses, aggregated.issues, workspace.contract_type)

        self._update_task(db, task, ReviewTaskStatus.REWRITING, 90)
        revised_clauses = self.rewriter.rewrite(clauses, instructions, aggregated.issues)

        self._update_task(db, task, ReviewTaskStatus.RECOMPOSING, 95)
        sections = self.recomposer.build_sections(revised_clauses)
        diffs = self.diff_builder.build(clauses, revised_clauses, aggregated.issues)
        task.diff_json = dumps([item.model_dump() for item in diffs])
        self.repository.save_task(db, task)

        self._update_task(db, task, ReviewTaskStatus.RENDERING, 98)
        self.report_service.create_docx_report(
            db,
            "review_revised",
            task.id,
            "revised_contract.docx",
            sections,
            preview={
                "overall_rating": aggregated.overall_rating,
                "summary": aggregated.summary,
                "diff_count": len(diffs),
                "review_mode": workspace.review_mode.value,
            },
        )

    def _artifact_availability(self, db: Session, task: ReviewTaskModel) -> ReviewArtifactAvailability:
        report_ready = self.report_service.get_owner_artifact(db, "review_report", task.id, "docx") is not None
        revised_ready = self.report_service.get_owner_artifact(db, "review_revised", task.id, "docx") is not None
        diff_ready = bool(loads(task.diff_json, []))
        return ReviewArtifactAvailability(
            report_ready=report_ready,
            revised_contract_ready=revised_ready,
            diff_ready=diff_ready,
        )

    def _update_task(
        self,
        db: Session,
        task: ReviewTaskModel,
        status: ReviewTaskStatus,
        progress: int,
        persist: bool = True,
    ) -> None:
        task.status = status.value
        task.progress = progress
        if persist:
            self.repository.save_task(db, task)
        self._publish_progress(task.id, status.value, progress)

    def _require_task(self, db: Session, task_id: str) -> ReviewTaskModel:
        task = self.repository.get_task(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Review task not found")
        return task

    def _publish_progress(self, task_id: str, status: str, progress: int) -> None:
        try:
            asyncio.run(self.websocket_manager.publish(task_id, {"task_id": task_id, "status": status, "progress": progress}))
        except RuntimeError:
            pass
