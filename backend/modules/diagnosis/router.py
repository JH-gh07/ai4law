import logging

from fastapi import APIRouter, HTTPException

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
logger = logging.getLogger(__name__)


@router.post("/diagnosis/evaluate", response_model=DiagnosisResult)
def evaluate(answers: DiagnosisAnswers) -> DiagnosisResult:
    return service.evaluate(answers)


@router.post("/diagnosis/report", response_model=DiagnosisReportResponse)
def generate_report(payload: DiagnosisReportRequest) -> DiagnosisReportResponse:
    try:
        result = service.evaluate(payload.answers)
        outputs = renderer.render(payload.company_name, payload.answers, result)
        return DiagnosisReportResponse(
            report_path=str(outputs["html"]),
            html_report_path=str(outputs["html"]),
            pdf_report_path=str(outputs["pdf"]),
            output_files={name: str(path) for name, path in outputs.items()},
            result=result,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("diagnosis report generation failed")
        raise HTTPException(
            status_code=500,
            detail=f"diagnosis report generation failed: {exc.__class__.__name__}: {exc}",
        ) from exc
