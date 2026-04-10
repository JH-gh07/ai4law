from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.diagnosis import router as diagnosis_router

app_instance = FastAPI()
app_instance.include_router(diagnosis_router.router, prefix="/api/v1")
client = TestClient(app_instance)


def test_diagnosis_report_outputs_html_pdf() -> None:
    # 避免测试依赖外部 LLM 网络调用。
    diagnosis_router.renderer.llm_client._enabled = False

    response = client.post(
        "/api/v1/diagnosis/report",
        json={
            "company_name": "DiagApiCo",
            "answers": {
                "q1_is_ciio": "no",
                "q2_has_important_data": "no",
                "q3_pii_count": 200000,
                "q4_spi_count": 300,
                "q5_no_personal_info": "no",
                "q6_scenario": "contract_performance",
                "q7_receiver_type": "third_party",
                "q8_purpose": "境外客服与系统运维",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()

    html_path = payload["html_report_path"]
    pdf_path = payload["pdf_report_path"]
    assert html_path.endswith(".html")
    assert pdf_path.endswith(".pdf")
    assert payload["report_path"] == html_path

    assert Path(html_path).exists()
    assert Path(pdf_path).exists()
    assert "html" in payload["output_files"]
    assert "pdf" in payload["output_files"]
