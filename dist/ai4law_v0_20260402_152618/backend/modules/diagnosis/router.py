from fastapi import APIRouter

from backend.modules.diagnosis.report_renderer import DiagnosisReportRenderer
from backend.modules.diagnosis.schema import (
    DiagnosisAnswers,
    DiagnosisReportRequest,
    DiagnosisReportResponse,
    DiagnosisResult,
)
from backend.modules.diagnosis.service import DiagnosisService

router = APIRouter(tags=["diagnosis"])
service = DiagnosisService()
renderer = DiagnosisReportRenderer()


@router.post("/diagnosis/evaluate", response_model=DiagnosisResult)
def evaluate(answers: DiagnosisAnswers) -> DiagnosisResult:
    return service.evaluate(answers)


@router.post("/diagnosis/report", response_model=DiagnosisReportResponse)
def generate_report(payload: DiagnosisReportRequest) -> DiagnosisReportResponse:
    result = service.evaluate(payload.answers)
    path = renderer.render(payload.company_name, payload.answers, result)
    return DiagnosisReportResponse(report_path=str(path), result=result)
