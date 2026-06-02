import asyncio
import mimetypes
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.json_utils import dumps, loads
from backend.models.review import ReviewTaskModel, UploadedFileModel
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.review import (
    AggregatedReview,
    ReviewAnalyzeResponse,
    ReviewAsyncAccepted,
    ReviewAsyncStatus,
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
from backend.services.review_service.rulebook_loader import RulebookLoader
from backend.services.review_service.document_classifier import DocumentClassifier
from backend.services.review_service.scenario_extractor import ScenarioExtractor
from backend.services.review_service.missing_item_checker import MissingItemChecker
from backend.services.review_service.risk_scorer import RiskScorer
from backend.services.review_service.consistency_checker import (
    CrossDocConsistencyChecker,
    DocumentWithClauses,
)
from backend.services.review_service.structured_document_parser import (
    StructuredDocumentParser,
)
from backend.services.review_service.citation_relevance_checker import (
    CitationRelevanceChecker,
)
from backend.services.review_service.annotated_docx_builder import (
    AnnotatedDocxBuilder,
)
from backend.services.review_service.specialized_reviewers.privacy_policy_reviewer import (
    PrivacyPolicyReviewer,
)
from backend.services.review_service.specialized_reviewers.scc_contract_reviewer import (
    SccContractReviewer,
)
from backend.services.review_service.specialized_reviewers.dpa_reviewer import (
    DpaReviewer,
)
from backend.services.review_service.specialized_reviewers.data_security_agreement_reviewer import (
    DataSecurityAgreementReviewer,
)
from backend.schemas.review import (
    ReviewScenarioContext,
    ReviewTaskConfig,
    ReviewMethod,
)


_ENGLISH_REVIEW_SIGNAL_TERMS = (
    "access",
    "agree",
    "agrees",
    "breach",
    "consent",
    "delete",
    "deletion",
    "disclose",
    "disclosure",
    "encrypt",
    "encrypted",
    "encryption",
    "ensure",
    "implement",
    "must",
    "notify",
    "notification",
    "process",
    "processing",
    "protect",
    "retain",
    "retention",
    "security",
    "shall",
    "transfer",
    "transferred",
    "withdraw",
)

_HIGH_RISK_SHORT_PHRASES = (
    # Short phrases that always warrant LLM deep review regardless of length
    "香港法院", "境外法院", "外国法院", "境外仲裁",
    "其他协议优先", "以本协议为准", "以本合同为准",
    "责任总额不超过", "赔偿上限", "不承担间接损失",
    "暂缓处理", "自行判断", "无需另行同意",
    "由乙方负责完成合规手续", "受托方负责.*合规",
    "不适用", "免除.*全部.*责任",
)

_SHORT_STRUCTURAL_NOISE_PATTERNS = (
    re.compile(r"^\d+([.)、]|\.\d+)*$"),
    re.compile(r"^(第[一二三四五六七八九十百千万0-9]+[章节条]|[一二三四五六七八九十]+、)$"),
    re.compile(r"^(article|section|clause)\s+\d+(\.\d+)*\.?$", re.IGNORECASE),
    re.compile(r"^(table of contents|contents|目录)$", re.IGNORECASE),
    re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$"),
    re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE),
    re.compile(r"^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$"),
)


class ReviewService:
    def __init__(self, file_service: FileService, report_service: ReportService, task_dispatcher, websocket_manager, session_factory, legal_api_service: DeliLegalService, llm_client: LLMClient | None = None) -> None:
        self.repository = ReviewRepository()
        self.file_service = file_service
        self.report_service = report_service
        self.task_dispatcher = task_dispatcher
        self.websocket_manager = websocket_manager
        self.session_factory = session_factory

        # ── Enhanced pipeline components ──
        self.rulebook = RulebookLoader()
        self.segmenter = ClauseSegmenter()
        self.classifier = ClauseClassifier(rulebook_loader=self.rulebook, llm_client=llm_client)
        self.knowledge_base = LocalRegulationKnowledgeBase(legal_api_service)
        self.document_classifier = DocumentClassifier(llm_client=llm_client)
        self.scenario_extractor = ScenarioExtractor(llm_client=llm_client)
        self.specialized_reviewers = {
            "privacy_policy": PrivacyPolicyReviewer(rulebook_loader=self.rulebook),
            "scc_contract": SccContractReviewer(rulebook_loader=self.rulebook),
            "dpa": DpaReviewer(rulebook_loader=self.rulebook),
            "other": DataSecurityAgreementReviewer(rulebook_loader=self.rulebook),
        }
        self.reviewer = ClauseReviewer(
            self.knowledge_base,
            llm_client=llm_client,
            rulebook_loader=self.rulebook,
            specialized_reviewers=self.specialized_reviewers,
        )
        self.risk_scorer = RiskScorer(rulebook_loader=self.rulebook)
        self.missing_checker = MissingItemChecker(rulebook_loader=self.rulebook)
        self.cross_doc_checker = CrossDocConsistencyChecker(llm_client=llm_client)
        self.aggregator = ReviewAggregator(
            risk_scorer=self.risk_scorer,
            rulebook_loader=self.rulebook,
        )
        self.renderer = ReviewReportRenderer()
        self.structured_parser = StructuredDocumentParser()
        self.citation_checker = CitationRelevanceChecker()
        self.annotated_builder = AnnotatedDocxBuilder()

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
        self._require_task(db, task_id, user_id)
        files = self.repository.list_files(db, task_id, user_id)
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded for review task")
        self.task_dispatcher.dispatch(self._run_pipeline, task_id, user_id)
        db.expire_all()
        refreshed = self._require_task(db, task_id, user_id)
        return ReviewAnalyzeResponse(id=refreshed.id, status=ReviewTaskStatus(refreshed.status), progress=refreshed.progress)

    def submit_async_from_uploaded_paths(self, db: Session, user_id: str, uploaded_files: list[str]) -> ReviewAsyncAccepted:
        task = self._create_task_with_uploaded_paths(db, user_id, uploaded_files)
        self.task_dispatcher.dispatch(self._run_pipeline, task.id, user_id)
        refreshed = self._require_task(db, task.id, user_id)
        return self._to_async_accepted(refreshed)

    def generate_from_uploaded_paths(self, db: Session, user_id: str, uploaded_files: list[str]) -> ReviewGenerateResponse:
        task = self._create_task_with_uploaded_paths(db, user_id, uploaded_files)
        self._run_pipeline(task.id, user_id)

        refreshed = self._require_task(db, task.id, user_id)
        if refreshed.status != ReviewTaskStatus.COMPLETED.value:
            raise HTTPException(status_code=500, detail="Review generation failed")
        return self._build_generate_response(db, user_id, refreshed)

    def get_async_status(self, db: Session, user_id: str, task_id: str) -> ReviewAsyncStatus:
        task = self._require_task(db, task_id, user_id)
        result = None
        error = "Review generation failed" if task.status == ReviewTaskStatus.FAILED.value else None
        if task.status == ReviewTaskStatus.COMPLETED.value:
            result = self._build_generate_response(db, user_id, task)
        return self._to_async_status(task, result=result, error=error)

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
        """Enhanced 8‑stage pipeline: PREPARING → SEGMENTING → CLASSIFYING →
        MISSING_CHECK → REVIEWING → CROSS_DOC_CHECK → AGGREGATING → RENDERING."""
        db = self.session_factory()
        try:
            task = self._require_task(db, task_id, user_id)
            files = self.repository.list_files(db, task_id, user_id)

            # ── Stage 0: PREPARING (0‑10%) — doc classification + scenario extraction ──
            self._update_task(db, task, ReviewTaskStatus.PREPARING, 2)

            # Parse request context from task metadata (if available)
            raw_ctx = loads(task.summary_json, {})
            scenario_ctx = None
            doc_type = raw_ctx.get("document_type") or "other"
            review_config = ReviewTaskConfig(
                review_depth=raw_ctx.get("review_depth", "standard"),
                max_llm_clauses=raw_ctx.get("max_llm_clauses", 20),
            )

            # Classify first document's text if user didn't specify type
            structured_docs: dict[str, object] = {}
            if files:
                # ── StructuredDocumentParser: extract tables, appendix fields ──
                combined_text_parts: list[str] = []
                for f in files:
                    try:
                        storage_path = Path(f.storage_path) if f.storage_path else None
                        if storage_path and storage_path.exists():
                            sdoc = self.structured_parser.parse(f.id, storage_path)
                            structured_docs[f.id] = sdoc
                            combined_text_parts.append(sdoc.plain_text)
                        else:
                            combined_text_parts.append(f.extracted_text or "")
                    except Exception:
                        combined_text_parts.append(f.extracted_text or "")

                combined_text = "\n\n".join(combined_text_parts)[:6000]
                first_file = files[0]

                if doc_type == "other" or not doc_type:
                    classification = self.document_classifier.classify(
                        combined_text,
                        user_document_type=doc_type if doc_type != "other" else None,
                        filename=first_file.filename,
                    )
                    doc_type = classification.document_type.value
                else:
                    classification = self.document_classifier.classify(
                        combined_text,
                        user_document_type=doc_type,
                        filename=first_file.filename,
                    )

                scenario_ctx = self.scenario_extractor.extract(
                    combined_text,
                    user_context=(
                        ReviewScenarioContext(**raw_ctx.get("scenario_context", {}))
                        if raw_ctx.get("scenario_context") else None
                    ),
                    document_classification=classification,
                )

                # ── Inject structured appendix fields into scenario ──
                for sdoc in structured_docs.values():
                    if hasattr(sdoc, "appendix_fields") and sdoc.appendix_fields:
                        for field_name, field_value in sdoc.appendix_fields.items():
                            if field_value and field_name not in scenario_ctx.auto_extracted_facts:
                                scenario_ctx.auto_extracted_facts[f"appendix_{field_name}"] = field_value

            self._update_task(db, task, ReviewTaskStatus.PREPARING, 10)

            # ── Stage 1: SEGMENTING (10‑25%) ──
            self._update_task(db, task, ReviewTaskStatus.SEGMENTING, 12)
            clauses = []
            for file in files:
                clauses.extend(self.segmenter.segment(file.id, file.extracted_text))
            self._update_task(db, task, ReviewTaskStatus.SEGMENTING, 25)

            # ── Stage 2: CLASSIFYING (25‑45%) ──
            self._update_task(db, task, ReviewTaskStatus.CLASSIFYING, 28)
            classified = [self.classifier.classify(clause) for clause in clauses]
            self._update_task(db, task, ReviewTaskStatus.CLASSIFYING, 45)

            # ── Stage 3: MISSING_CHECK (45‑55%) [NEW] ──
            # Build scenario dict for checker + reviewer
            scenario_dict = scenario_ctx.model_dump() if scenario_ctx else {}

            self._update_task(db, task, ReviewTaskStatus.MISSING_CHECK, 48)
            missing_items = self.missing_checker.check(
                classified, doc_type, scenario=scenario_dict,
            )
            self._update_task(db, task, ReviewTaskStatus.MISSING_CHECK, 55)

            # ── Stage 4: REVIEWING (55‑80%) — risk‑triggered LLM ──
            self._update_task(db, task, ReviewTaskStatus.REVIEWING, 57)
            issues = []
            reviewable = [c for c in classified if self._is_reviewable_clause(c)]
            llm_clause_ids = self._select_llm_candidates(reviewable, review_config)

            checkpoints = self._review_progress_checkpoints(len(reviewable))
            for index, clause in enumerate(reviewable, start=1):
                use_llm = clause.clause_id in llm_clause_ids
                issues.extend(
                    self.reviewer.review(
                        clause,
                        use_llm=use_llm,
                        document_type=doc_type,
                        scenario_context=scenario_dict,
                    )
                )
                if index in checkpoints:
                    progress = 57 + int((index / max(len(reviewable), 1)) * 22)
                    self._update_task(db, task, ReviewTaskStatus.REVIEWING, min(progress, 79))

            # ── Citation relevance check ──
            for issue in issues:
                relevance = self.citation_checker.check(issue)
                if not relevance.get("relevant", True):
                    issue.risk_analysis += (
                        f" ｜ 引用相关性警告：{'; '.join(relevance.get('issues', []))}"
                    )

            self._update_task(db, task, ReviewTaskStatus.REVIEWING, 80)

            # ── Stage 5: CROSS_DOC_CHECK (80‑85%) [NEW] ──
            self._update_task(db, task, ReviewTaskStatus.CROSS_DOC_CHECK, 82)
            consistency_warnings: list[str] = []
            if review_config.enable_cross_document_check and len(files) > 1:
                docs_with_clauses = [
                    DocumentWithClauses(
                        file_id=f.id,
                        filename=f.filename,
                        document_type=doc_type,
                        clauses=[c for c in classified if c.file_id == f.id],
                        issues=[i for i in issues if i.file_id == f.id],
                    )
                    for f in files
                ]
                consistency_warnings = self.cross_doc_checker.check(docs_with_clauses)
            self._update_task(db, task, ReviewTaskStatus.CROSS_DOC_CHECK, 85)

            # ── Stage 6: AGGREGATING (85‑92%) ──
            self._update_task(db, task, ReviewTaskStatus.AGGREGATING, 87)
            review_mode = "llm" if (self.reviewer.llm_client and self.reviewer.llm_client.enabled) else "rule_only"
            aggregated = self.aggregator.aggregate(
                issues,
                missing_items=missing_items,
                consistency_warnings=consistency_warnings,
                classified_clauses=classified,
                document_type=doc_type,
                document_title=(
                    scenario_ctx.document_title if scenario_ctx else None
                ),
                review_mode=review_mode,
            )
            self._update_task(db, task, ReviewTaskStatus.AGGREGATING, 92)

            # ── Stage 7: RENDERING (92‑100%) ──
            self._update_task(db, task, ReviewTaskStatus.RENDERING, 95)
            sections = self.renderer.build_sections(aggregated)
            self.report_service.create_docx_report(
                db,
                user_id,
                "review",
                task_id,
                "review_report.docx",
                sections,
                preview={
                    "overall_rating": aggregated.overall_rating,
                    "overall_risk_score": aggregated.overall_risk_score,
                    "summary": aggregated.summary,
                    "document_type": doc_type,
                    "review_mode": review_mode,
                },
            )

            # ── Annotated DOCX (source doc with inline comments) ──
            annotated_output_dir = Path("outputs/review") / task_id / "outputs"
            annotated_output_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                try:
                    storage_path = Path(f.storage_path) if f.storage_path else None
                    if storage_path and storage_path.exists() and storage_path.suffix == ".docx":
                        annotated_path = annotated_output_dir / f"annotated_{f.filename}"
                        self.annotated_builder.build(
                            source_docx_path=storage_path,
                            issues=[i for i in aggregated.issues if i.file_id == f.id],
                            output_path=annotated_path,
                        )
                except Exception:
                    pass  # Annotated DOCX is best-effort; don't fail the whole pipeline

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

    def _create_task_with_uploaded_paths(self, db: Session, user_id: str, uploaded_files: list[str]) -> ReviewTaskModel:
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
        task.status = ReviewTaskStatus.UPLOADED.value
        task.progress = 10
        self.repository.save_task(db, task)
        return task

    def _build_generate_response(self, db: Session, user_id: str, task: ReviewTaskModel) -> ReviewGenerateResponse:
        report = self.report_service.get_owner_artifact(db, user_id, "review", task.id, "docx")
        if not report:
            raise HTTPException(status_code=404, detail="Review report not found")
        summary = AggregatedReview.model_validate(loads(task.summary_json, {}))
        return ReviewGenerateResponse(
            report_path=report.file_path,
            output_files={"docx": report.file_path, "report": report.file_path},
            risk_level=summary.overall_rating,
            result={
                "risk_level": summary.overall_rating,
                "summary": summary.summary,
                "issue_counts": summary.issue_counts,
            },
            consistency_issues=[],
        )

    @staticmethod
    def _to_async_accepted(task: ReviewTaskModel) -> ReviewAsyncAccepted:
        return ReviewAsyncAccepted(
            task_id=task.id,
            module="review",
            state=task.status,
            progress=task.progress,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def _to_async_status(
        task: ReviewTaskModel,
        result: ReviewGenerateResponse | None = None,
        error: str | None = None,
    ) -> ReviewAsyncStatus:
        return ReviewAsyncStatus(
            task_id=task.id,
            module="review",
            state=task.status,
            progress=task.progress,
            created_at=task.created_at,
            updated_at=task.updated_at,
            error=error,
            result=result,
        )

    @staticmethod
    def _review_progress_checkpoints(total: int) -> set[int]:
        if total <= 0:
            return set()
        if total <= 4:
            return set(range(1, total + 1))
        return {
            max(1, total // 4),
            max(1, total // 2),
            max(1, (total * 3) // 4),
            total,
        }

    @staticmethod
    def _is_reviewable_clause(clause) -> bool:
        text = clause.text.strip()
        if not text:
            return False
        if ReviewService._looks_like_short_structural_noise(text):
            return False
        if clause.clause_type.value == "OTHER" and not clause.matched_keywords and len(text) < 120:
            return ReviewService._has_english_review_signal(text)
        return True

    @staticmethod
    def _has_english_review_signal(text: str) -> bool:
        lowered = text.lower()
        return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in _ENGLISH_REVIEW_SIGNAL_TERMS)

    @staticmethod
    def _looks_like_short_structural_noise(text: str) -> bool:
        # English contracts can express material duties in very short sentences.
        # Only skip short ASCII-like text when it clearly looks like structure, metadata, or navigation noise.
        if len(text) >= 64 or ReviewService._has_english_review_signal(text):
            return False
        return any(pattern.fullmatch(text) for pattern in _SHORT_STRUCTURAL_NOISE_PATTERNS)

    def _select_llm_candidates(self, classified: list, review_config: ReviewTaskConfig | None = None) -> set[str]:
        """Risk‑triggered LLM selection (replaces top‑8 approach).

        Returns clause_ids that should get LLM review.
        Always sends:
        - All HIGH_PRIORITY_TYPES clauses (CROSS_BORDER_TRANSFER, SENSITIVE_PI, etc.)
        - MEDIUM_PRIORITY_TYPES clauses with text ≥ 120 chars
        - All clauses when review_depth=deep (up to max_llm_clauses cap)
        """
        high_types = set(self.rulebook.get_high_priority_types())
        medium_types = set(self.rulebook.get_medium_priority_types())
        max_cap = (review_config.max_llm_clauses if review_config else 20) or 20

        candidates: list[tuple[str, int]] = []  # (clause_id, priority_score)

        for clause in classified:
            ct = clause.clause_type.value
            text_len = len(clause.text.strip())

            # High‑risk short phrase check — override length threshold
            has_high_risk_phrase = any(
                re.search(phrase, clause.text) for phrase in _HIGH_RISK_SHORT_PHRASES
            )

            if ct == "OTHER" and not has_high_risk_phrase:
                continue
            if text_len < 40 and not has_high_risk_phrase:
                continue

            if has_high_risk_phrase:
                priority = 12  # highest priority
            elif ct in high_types:
                priority = 10
            elif ct in medium_types and text_len >= 120:
                priority = 5
            elif review_config and review_config.review_depth.value == "deep":
                priority = 3
            else:
                priority = 1

            candidates.append((clause.clause_id, priority))

        # Sort by priority (desc), then by clause_type weight
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = {cid for cid, _ in candidates[:max_cap]}

        # Always include deep mode: also add medium types regardless of length
        if review_config and review_config.review_depth.value == "deep":
            for clause in classified:
                ct = clause.clause_type.value
                if ct in medium_types and len(clause.text.strip()) >= 80:
                    selected.add(clause.clause_id)

        return selected

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
