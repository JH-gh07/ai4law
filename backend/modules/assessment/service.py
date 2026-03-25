import uuid

from backend.modules.assessment.chapter_generator import AssessmentChapterGenerator
from backend.modules.assessment.consistency_checker import ConsistencyChecker
from backend.modules.assessment.profile_extractor import ProfileExtractor
from backend.modules.assessment.report_renderer import AssessmentReportRenderer
from backend.modules.assessment.retriever import AssessmentRetriever
from backend.modules.assessment.schema import AssessmentRequest, AssessmentResult
from backend.modules.assessment.task_state import AssessmentTaskState


class AssessmentService:
    def __init__(self) -> None:
        self.extractor = ProfileExtractor()
        self.retriever = AssessmentRetriever()
        self.generator = AssessmentChapterGenerator()
        self.checker = ConsistencyChecker()
        self.renderer = AssessmentReportRenderer()

    def generate_report(self, payload: AssessmentRequest) -> AssessmentResult:
        task_id = str(uuid.uuid4())

        profile = self.extractor.extract(payload)
        regulations = self.retriever.search(profile)
        chapters = self.generator.generate(profile, regulations)
        issues = self.checker.check(profile, chapters)
        report_path = self.renderer.render(payload.company_name, profile, regulations, chapters)

        return AssessmentResult(
            task_id=task_id,
            state=AssessmentTaskState.COMPLETED,
            report_path=str(report_path),
            profile=profile,
            regulations=regulations,
            chapters=chapters,
            consistency_issues=issues,
        )
