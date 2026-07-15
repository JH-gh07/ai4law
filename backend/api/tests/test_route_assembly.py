import json
from collections import defaultdict
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings

BASELINE_PATH = Path(__file__).with_name("route_baseline.json")
IGNORED_METHODS = {"HEAD", "OPTIONS"}


def _route_snapshot(app: FastAPI) -> list[dict[str, str]]:
    openapi = app.openapi()
    rows: list[dict[str, str]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or set()):
            if method in IGNORED_METHODS:
                continue
            operation = openapi["paths"][route.path][method.lower()]
            rows.append(
                {
                    "method": method,
                    "path": route.path,
                    "route_name": route.name,
                    "endpoint_module": route.endpoint.__module__,
                    "operation_id": operation["operationId"],
                }
            )

    return sorted(rows, key=lambda row: (row["path"], row["method"]))


def _duplicate_routes(rows: list[dict[str, str]]) -> list[str]:
    routes_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        routes_by_key[(row["method"], row["path"])].append(row)

    conflicts: list[str] = []
    for (method, path), routes in routes_by_key.items():
        if len(routes) < 2:
            continue
        details = ", ".join(
            (
                f"name={route['route_name']} "
                f"module={route['endpoint_module']} "
                f"operation_id={route['operation_id']}"
            )
            for route in routes
        )
        conflicts.append(f"{method} {path}: {details}")
    return conflicts


@pytest.fixture
def complete_app(tmp_path: Path) -> FastAPI:
    database_path = tmp_path / "route-assembly.db"
    settings = Settings(database_url=f"sqlite:///{database_path}")
    return create_app(settings)


def test_create_app_matches_route_baseline(complete_app: FastAPI) -> None:
    expected = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    actual = _route_snapshot(complete_app)

    assert actual == expected
    assert len(actual) == 104


def test_routes_have_no_method_path_conflicts(complete_app: FastAPI) -> None:
    routes = _route_snapshot(complete_app)
    conflicts = _duplicate_routes(routes)
    operation_ids = [route["operation_id"] for route in routes]

    assert not conflicts, "Duplicate routes:\n" + "\n".join(conflicts)
    assert len(operation_ids) == len(set(operation_ids))


def test_version_prefixes_and_diagnosis_compatibility_routes(
    complete_app: FastAPI,
) -> None:
    route_keys = {
        (row["method"], row["path"])
        for row in _route_snapshot(complete_app)
    }

    assert ("GET", "/health") in route_keys
    assert ("POST", "/api/v0/tasks") in route_keys
    assert ("POST", "/api/v1/assessment/generate") in route_keys
    assert ("POST", "/api/v1/diagnosis/report") in route_keys
    assert ("POST", "/api/v1/diagnosis/sessions") in route_keys
    assert (
        "GET",
        "/api/v1/diagnosis/sessions/{session_id}/handoff/assessment",
    ) in route_keys
    assert all(
        path == "/health" or path.startswith(("/api/v0/", "/api/v1/"))
        for _, path in route_keys
    )


def test_lifespan_health_and_openapi(complete_app: FastAPI) -> None:
    with TestClient(complete_app) as client:
        health_response = client.get("/health")
        openapi_response = client.get("/openapi.json")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert openapi_response.status_code == 200
    assert "/api/v1/diagnosis/report" in openapi_response.json()["paths"]
