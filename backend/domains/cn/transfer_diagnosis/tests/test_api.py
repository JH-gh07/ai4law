from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.domains.cn.transfer_diagnosis import router as diagnosis_router
from backend.api.v1.endpoints import auth as auth_router
from backend.core.container import AppContainer
from backend.core.db import init_db
from backend.core.settings import Settings


def _build_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "diagnosis_api_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=tmp_path / "storage",
    )
    app = FastAPI()
    app.state.container = AppContainer(settings)
    init_db(app.state.container.engine)
    app.include_router(auth_router.router, prefix="/api/v1/auth")
    app.include_router(diagnosis_router.router, prefix="/api/v1")
    return TestClient(app)


def test_diagnosis_report_outputs_html_pdf(tmp_path: Path) -> None:
    # 避免测试依赖外部 LLM 网络调用。
    diagnosis_router.renderer.llm_client._enabled = False

    with _build_client(tmp_path) as client:
        register = client.post(
            "/api/v1/auth/register",
            json={
                "username": "diag-user",
                "email": "diag-user@example.com",
                "password": "diag-pass-123",
            },
        )
        assert register.status_code == 200
        token = register.json()["access_token"]

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
            headers={"Authorization": f"Bearer {token}"},
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
