from fastapi import APIRouter

from backend.modules.assessment.schema import AssessmentRequest, AssessmentResult
from backend.modules.assessment.service import AssessmentService

router = APIRouter(tags=["assessment"])
service = AssessmentService()


@router.post("/assessment/generate", response_model=AssessmentResult)
def generate_assessment(payload: AssessmentRequest) -> AssessmentResult:
    return service.generate_report(payload)
