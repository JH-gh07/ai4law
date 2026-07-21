from pathlib import Path

from fastapi.testclient import TestClient
from fastapi.routing import APIRoute

from backend.app import create_app
from backend.common.llm.provider_registry import LLMProviderRegistry
from backend.core.runtime_settings import apply_runtime_payload
from backend.core.settings import Settings
from backend.domains.cn.security_assessment import router as assessment_router
from backend.domains.cn.security_assessment.schema import AssessmentAsyncAccepted
from backend.services.runtime_health import record_llm_health, require_healthy_llm


def _production_client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            app_env="production",
            database_url=f"sqlite:///{tmp_path / 'runtime-health.db'}",
            storage_dir=tmp_path / "storage",
            _env_file=None,
        )
    )
    return TestClient(app)


def _assessment_payload() -> dict[str, object]:
    return {
        "company_name": "Health Gate Co",
        "industry": "SaaS",
        "is_ciio": False,
        "contains_important_data": False,
        "pii_count": 150000,
        "spi_count": 500,
        "transfer_purpose": "support",
        "receiver_country": "Singapore",
        "force_override_path": True,
        "uploaded_files": [],
    }


def test_production_task_is_blocked_before_submission_without_healthy_llm(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def unexpected_submit(_payload):
        raise AssertionError("task submission must not run before readiness passes")

    monkeypatch.setattr(assessment_router.service, "submit_async", unexpected_submit)
    with _production_client(tmp_path) as client:
        auth = client.post(
            "/api/v1/auth/register",
            json={
                "username": "health-gate-user",
                "email": "health-gate@example.com",
                "password": "health-gate-password",
            },
        )
        client.headers["Authorization"] = f"Bearer {auth.json()['access_token']}"
        response = client.post(
            "/api/v1/assessment/generate_async",
            json=_assessment_payload(),
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "LLM_PROVIDER_UNHEALTHY"


def test_production_task_starts_after_matching_health_probe(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        assessment_router.service,
        "submit_async",
        lambda _payload: AssessmentAsyncAccepted(
            task_id="healthy-task",
            module="assessment",
            state="CREATED",
            attempts=0,
            max_attempts=1,
        ),
    )
    with _production_client(tmp_path) as client:
        settings = client.app.state.container.settings
        apply_runtime_payload(
            settings,
            {
                "llm": {
                    "active_provider_id": "healthy",
                    "providers": [
                        {
                            "id": "healthy",
                            "name": "Healthy",
                            "provider_type": "openai_compatible",
                            "api_key": "test-key",
                            "api_url": "https://example.com/v1",
                            "model": "test-model",
                            "enabled": True,
                            "timeout": 30,
                        }
                    ],
                }
            },
        )
        provider = LLMProviderRegistry(settings).get_active_provider()
        record_llm_health(settings, provider, {"ok": True})
        auth = client.post(
            "/api/v1/auth/register",
            json={
                "username": "healthy-user",
                "email": "healthy@example.com",
                "password": "healthy-password",
            },
        )
        client.headers["Authorization"] = f"Bearer {auth.json()['access_token']}"
        response = client.post(
            "/api/v1/assessment/generate_async",
            json=_assessment_payload(),
        )

    assert response.status_code == 200
    assert response.json()["task_id"] == "healthy-task"


def test_all_llm_task_entry_routes_apply_the_production_health_gate(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'route-health.db'}",
            storage_dir=tmp_path / "route-storage",
            _env_file=None,
        )
    )
    expected_paths = {
        "/api/v0/tasks",
        "/api/v1/assessment/generate",
        "/api/v1/assessment/generate_async",
        "/api/v1/assessment/tasks/{task_id}/retry",
        "/api/v1/pipia/generate",
        "/api/v1/pipia/generate_async",
        "/api/v1/pipia/tasks/{task_id}/retry",
        "/api/v1/eu_scc/generate",
        "/api/v1/eu_scc/generate_async",
        "/api/v1/eu_scc/tasks/{task_id}/retry",
        "/api/v1/bcr/generate",
        "/api/v1/bcr/generate_async",
        "/api/v1/bcr/tasks/{task_id}/retry",
        "/api/v1/dpia/generate",
        "/api/v1/dpia/generate_async",
        "/api/v1/dpia/tasks/{task_id}/retry",
        "/api/v1/tia/generate",
        "/api/v1/tia/generate_async",
        "/api/v1/tia/tasks/{task_id}/retry",
        "/api/v1/cpra/generate",
        "/api/v1/cpra/generate_async",
        "/api/v1/cpra/tasks/{task_id}/retry",
        "/api/v1/us_14117/generate",
        "/api/v1/us_14117/generate_async",
        "/api/v1/us_14117/tasks/{task_id}/retry",
        "/api/v1/cn-flow/generate",
        "/api/v1/cn-flow/generate_async",
        "/api/v1/cn-flow/tasks/{task_id}/retry",
        "/api/v1/diagnosis/report",
        "/api/v1/review/generate",
        "/api/v1/review/generate_async",
        "/api/v1/review/tasks/{task_id}/analyze",
    }
    guarded_paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and any(
            dependency.call is require_healthy_llm
            for dependency in route.dependant.dependencies
        )
    }

    assert guarded_paths == expected_paths
