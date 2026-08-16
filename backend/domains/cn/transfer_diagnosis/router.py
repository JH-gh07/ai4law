import logging
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.artifact_registry import register_module_result_artifacts
from backend.services.runtime_health import require_healthy_llm
from backend.common.trace.tracer import trace_sync
from backend.core.dependencies import get_container, get_current_user, get_db
from backend.domains.cn.transfer_diagnosis.report_renderer import DiagnosisReportRenderer
from backend.domains.cn.transfer_diagnosis.schema import (
    DiagnosisAnswers,
    DiagnosisReportRequest,
    DiagnosisReportResponse,
    DiagnosisResult,
)
from backend.schemas.auth import AuthUser
from backend.domains.cn.transfer_diagnosis.service import DiagnosisService

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])
service = DiagnosisService()
renderer = DiagnosisReportRenderer()
logger = logging.getLogger(__name__)


@router.post("/evaluate", response_model=DiagnosisResult)
def evaluate(answers: DiagnosisAnswers) -> DiagnosisResult:
    return service.evaluate(answers)


@router.post("/report", response_model=DiagnosisReportResponse, dependencies=[Depends(require_healthy_llm)])
def generate_report(
    payload: DiagnosisReportRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
    container=Depends(get_container),
) -> DiagnosisReportResponse:
    try:
        result = trace_sync(
            "diagnosis",
            lambda: service.evaluate(payload.answers, control=payload.control),
        )
        outputs = renderer.render(payload.company_name, payload.answers, result)
        register_module_result_artifacts(
            db=db,
            container=container,
            user=current_user,
            module_key="diagnosis",
            result=SimpleNamespace(report_path=str(outputs["html"]), output_files={k: str(v) for k, v in outputs.items()}),
        )
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
