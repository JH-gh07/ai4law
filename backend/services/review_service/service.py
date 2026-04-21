import asyncio
import mimetypes
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.json_utils import dumps, loads
from backend.models.review import ReviewTaskModel, UploadedFileModel
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.review import (
    AggregatedReview,
    ReviewAnalyzeResponse,
    ReviewGenerateResponse,
    ReviewIssuesResponse,
    ReviewReportResponse,
    ReviewTaskCreateResponse,
    ReviewTaskStatus,
    ReviewTaskStatusResponse,
    UploadedFileResponse,
)
from backend.common.llm.client import LLMClient
from backend.services.file_service import FileService
from backend.services.legal_api_service import DeliLegalService
from backend.services.report_service import ReportService
from backend.services.review_service.clause_classifier import ClauseClassifier
from backend.services.review_service.clause_reviewer import ClauseReviewer
from backend.services.review_service.clause_segmenter import ClauseSegmenter
from backend.services.review_service.rag_provider import LocalRegulationKnowledgeBase
from backend.services.review_service.review_aggregator import ReviewAggregator
from backend.services.review_service.review_report_renderer import ReviewReportRenderer


class ReviewService:
    def __init__(self, file_service: FileService, report_service: ReportService, task_dispatcher, websocket_manager, session_factory, legal_api_service: DeliLegalService, llm_client: LLMClient | None = None) -> None:
        self.repository = ReviewRepository()
        self.file_service = file_service
        self.report_service = report_service
        self.task_dispatcher = task_dispatcher
        self.websocket_manager = websocket_manager
        self.session_factory = session_factory
        self.segmenter = ClauseSegmenter()
        self.classifier = ClauseClassifier()
        self.knowledge_base = LocalRegulationKnowledgeBase(legal_api_service)
        self.reviewer = ClauseReviewer(self.knowledge_base, llm_client=llm_client)
        self.aggregator = ReviewAggregator()
        self.renderer = ReviewReportRenderer()

    def create_task(self, db: Session, user_id: str) -> ReviewTaskCreateResponse:
        task = self.repository.create_task(db, user_id)
        return ReviewTaskCreateResponse(id=task.id, status=ReviewTaskStatus(task.status), created_at=task.created_at)

    def upload_file(self, db: Session, user_id: str, task_id: str, upload: UploadFile) -> UploadedFileResponse:
        task = self._require_task(db, task_id, user_id)
        saved_path = self.file_service.save_upload(task_id, upload)
        extracted_text = self.file_service.extract_text(saved_path)
        record = UploadedFileModel(
            user_id=user_id,
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

    def analyze(self, db: Session, user_id: str, task_id: str) -> ReviewAnalyzeResponse:
        task = self._require_task(db, task_id, user_id)
        files = self.repository.list_files(db, task_id, user_id)
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded for review task")
        self.task_dispatcher.dispatch(self._run_pipeline, task_id, user_id)
        db.expire_all()
        refreshed = self._require_task(db, task_id, user_id)
        return ReviewAnalyzeResponse(id=refreshed.id, status=ReviewTaskStatus(refreshed.status), progress=refreshed.progress)

    def generate_from_uploaded_paths(self, db: Session, user_id: str, uploaded_files: list[str]) -> ReviewGenerateResponse:
        normalized_paths = [self._resolve_uploaded_path(path) for path in uploaded_files]
        if not normalized_paths:
            raise HTTPException(status_code=400, detail="No files uploaded for review task")

        task = self.repository.create_task(db, user_id)
        for file_path in normalized_paths:
            extracted_text = self.file_service.extract_text(file_path)
            mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            record = UploadedFileModel(
                user_id=user_id,
                task_id=task.id,
                filename=file_path.name,
                content_type=mime,
                storage_path=str(file_path),
                extracted_text=extracted_text,
            )
            self.repository.create_file(db, record)

        self._run_pipeline(task.id, user_id)

        refreshed = self._require_task(db, task.id, user_id)
        if refreshed.status != ReviewTaskStatus.COMPLETED.value:
            raise HTTPException(status_code=500, detail="Review generation failed")
        report = self.report_service.get_owner_artifact(db, user_id, "review", task.id, "docx")
        if not report:
            raise HTTPException(status_code=404, detail="Review report not found")
        summary = AggregatedReview.model_validate(loads(refreshed.summary_json, {}))
        return ReviewGenerateResponse(
            report_path=report.path,
            output_files={"docx": report.path, "report": report.path},
            risk_level=summary.overall_rating,
            result={
                "risk_level": summary.overall_rating,
                "summary": summary.summary,
                "issue_counts": summary.issue_counts,
            },
            consistency_issues=[],
        )

    def get_status(self, db: Session, user_id: str, task_id: str) -> ReviewTaskStatusResponse:
        task = self._require_task(db, task_id, user_id)
        raw_summary = loads(task.summary_json, {})
        summary = AggregatedReview.model_validate(raw_summary) if raw_summary else None
        return ReviewTaskStatusResponse(id=task.id, status=ReviewTaskStatus(task.status), progress=task.progress, summary=summary)

    def get_issues(self, db: Session, user_id: str, task_id: str) -> ReviewIssuesResponse:
        task = self._require_task(db, task_id, user_id)
        raw_issues = loads(task.issues_json, [])
        issues = raw_issues
        return ReviewIssuesResponse(task_id=task_id, issues=issues)

    def get_report(self, db: Session, user_id: str, task_id: str) -> ReviewReportResponse:
        task = self._require_task(db, task_id, user_id)
        if task.status != ReviewTaskStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Review report is not ready")
        report = self.report_service.get_owner_artifact(db, user_id, "review", task_id, "docx")
        if not report:
            raise HTTPException(status_code=404, detail="Review report not found")
        summary = AggregatedReview.model_validate(loads(task.summary_json, {}))
        return ReviewReportResponse(report=report, review=summary)

    def _run_pipeline(self, task_id: str, user_id: str) -> None:
        db = self.session_factory()
        try:
            task = self._require_task(db, task_id, user_id)
            files = self.repository.list_files(db, task_id, user_id)

            self._update_task(db, task, ReviewTaskStatus.SEGMENTING, 25)
            clauses = []
            for file in files:
                clauses.extend(self.segmenter.segment(file.id, file.extracted_text))

            self._update_task(db, task, ReviewTaskStatus.CLASSIFYING, 45)
            classified = [self.classifier.classify(clause) for clause in clauses]

            self._update_task(db, task, ReviewTaskStatus.REVIEWING, 70)
            issues = []
            for clause in classified:
                issues.extend(self.reviewer.review(clause))

            self._update_task(db, task, ReviewTaskStatus.AGGREGATING, 85)
            aggregated = self.aggregator.aggregate(issues)

            self._update_task(db, task, ReviewTaskStatus.RENDERING, 95)
            sections = self.renderer.build_sections(aggregated)
            self.report_service.create_docx_report(
                db,
                user_id,
                "review",
                task_id,
                "review_report.docx",
                sections,
                preview={"overall_rating": aggregated.overall_rating, "summary": aggregated.summary},
            )

            task.issues_json = dumps([issue.model_dump() for issue in aggregated.issues])
            task.summary_json = dumps(aggregated.model_dump())
            self._update_task(db, task, ReviewTaskStatus.COMPLETED, 100, persist=False)
            self.repository.save_task(db, task)
        except Exception:
            task = self._require_task(db, task_id, user_id)
            task.status = ReviewTaskStatus.FAILED.value
            self.repository.save_task(db, task)
            raise
        finally:
            db.close()

    def _update_task(self, db: Session, task: ReviewTaskModel, status: ReviewTaskStatus, progress: int, persist: bool = True) -> None:
        task.status = status.value
        task.progress = progress
        if persist:
            self.repository.save_task(db, task)
        self._publish_progress(task.id, status.value, progress)

    def _require_task(self, db: Session, task_id: str, user_id: str) -> ReviewTaskModel:
        task = self.repository.get_task(db, task_id, user_id)
        if not task:
            raise HTTPException(status_code=404, detail="Review task not found")
        return task

    def _resolve_uploaded_path(self, uploaded_path: str) -> Path:
        raw = Path(uploaded_path.strip())
        if not raw.as_posix():
            raise HTTPException(status_code=400, detail="Uploaded file path is empty")
        if raw.is_absolute():
            resolved = raw.resolve()
        else:
            resolved = (Path.cwd() / raw).resolve()

        allowed_root = self.file_service.settings.storage_dir.resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Uploaded file path is outside storage directory") from exc

        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail=f"Uploaded file not found: {uploaded_path}")
        return resolved

    def _publish_progress(self, task_id: str, status: str, progress: int) -> None:
        try:
            asyncio.run(self.websocket_manager.publish(task_id, {"task_id": task_id, "status": status, "progress": progress}))
        except RuntimeError:
            pass
