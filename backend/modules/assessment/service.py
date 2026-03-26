import uuid

from backend.common.tasks.manager import InMemoryTaskManager, TaskSnapshot
from backend.modules.assessment.chapter_generator import AssessmentChapterGenerator
from backend.modules.assessment.consistency_checker import ConsistencyChecker
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.report_renderer import AssessmentReportRenderer
from backend.modules.assessment.retriever import AssessmentRetriever
from backend.modules.assessment.schema import (
    AssessmentAsyncAccepted,
    AssessmentAsyncStatus,
    AssessmentRequest,
    AssessmentResult,
)
from backend.modules.assessment.task_state import AssessmentTaskState


class AssessmentService:
    def __init__(self) -> None:
        self.extractor = ProfileExtractor()
        self.retriever = AssessmentRetriever()
        self.generator = AssessmentChapterGenerator()
        self.checker = ConsistencyChecker()
        self.renderer = AssessmentReportRenderer()
        self.tasks = InMemoryTaskManager(module="assessment")

    def generate_report(self, payload: AssessmentRequest) -> AssessmentResult:
        task_id = str(uuid.uuid4())

        profile = self.extractor.extract(payload)
        regulations = self.retriever.search(profile)
        chapters = self.generator.generate(profile, regulations)
        issues = self.checker.check(profile, chapters)
        outputs = self.renderer.render(payload.company_name, profile, regulations, chapters)

        return AssessmentResult(
            task_id=task_id,
            state=AssessmentTaskState.COMPLETED,
            report_path=outputs["docx"],
            output_files=outputs,
            profile=profile,
            regulations=regulations,
            chapters=chapters,
            consistency_issues=issues,
        )

    def submit_async(self, payload: AssessmentRequest) -> AssessmentAsyncAccepted:
        snapshot = self.tasks.submit(lambda: self.generate_report(payload))
        return self._snapshot_to_accepted(snapshot)

    def get_async_status(self, task_id: str) -> AssessmentAsyncStatus:
        snapshot = self.tasks.get_or_raise(task_id)
        return self._snapshot_to_status(snapshot)

    def retry_async(self, task_id: str) -> AssessmentAsyncStatus:
        snapshot = self.tasks.retry(task_id)
        return self._snapshot_to_status(snapshot)

    @staticmethod
    def _snapshot_to_accepted(snapshot: TaskSnapshot) -> AssessmentAsyncAccepted:
        return AssessmentAsyncAccepted(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
        )

    @staticmethod
    def _snapshot_to_status(snapshot: TaskSnapshot) -> AssessmentAsyncStatus:
        result = None
        if snapshot.result is not None:
            result = AssessmentResult.model_validate(snapshot.result)
        return AssessmentAsyncStatus(
            task_id=snapshot.task_id,
            module=snapshot.module,
            state=snapshot.state,
            attempts=snapshot.attempts,
            max_attempts=snapshot.max_attempts,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            error=snapshot.error,
            result=result,
        )
