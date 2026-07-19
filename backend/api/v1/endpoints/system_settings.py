from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.core.dependencies import get_current_user
from backend.core.runtime_settings import (
    apply_runtime_payload,
    build_effective_runtime_payload,
    build_provider_test_result,
)
from backend.schemas.auth import AuthUser
from backend.schemas.system_settings import (
    RuntimeProviderTestRequest,
    RuntimeProviderTestResponse,
    RuntimeSettingsResponse,
    RuntimeSettingsUpdateRequest,
)
from backend.services.runtime_client_refresher import refresh_runtime_clients

router = APIRouter()


@router.get("/settings/runtime", response_model=RuntimeSettingsResponse)
def get_runtime_settings(
    request: Request,
    _current_user: AuthUser = Depends(get_current_user),
) -> RuntimeSettingsResponse:
    container = request.app.state.container
    payload = build_effective_runtime_payload(container.settings)
    return RuntimeSettingsResponse.model_validate(payload)


@router.put("/settings/runtime", response_model=RuntimeSettingsResponse)
def update_runtime_settings(
    body: RuntimeSettingsUpdateRequest,
    request: Request,
    _current_user: AuthUser = Depends(get_current_user),
) -> RuntimeSettingsResponse:
    container = request.app.state.container
    payload = apply_runtime_payload(container.settings, body.model_dump())
    refresh_runtime_clients(container)
    return RuntimeSettingsResponse.model_validate(payload)


@router.post("/settings/llm/test-provider", response_model=RuntimeProviderTestResponse)
def test_runtime_provider(
    body: RuntimeProviderTestRequest,
    request: Request,
    _current_user: AuthUser = Depends(get_current_user),
) -> RuntimeProviderTestResponse:
    payload = build_provider_test_result(
        body.provider.model_dump(),
        request.app.state.container.settings,
    )
    return RuntimeProviderTestResponse.model_validate(payload)
