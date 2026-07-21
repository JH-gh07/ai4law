from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeProviderConfig(BaseModel):
    id: str
    name: str
    provider_type: str = "openai_compatible"
    api_key: str = ""
    api_url: str = ""
    model: str = ""
    enabled: bool = True
    timeout: int = 60
    api_key_configured: bool = False


class DeliLegalConfig(BaseModel):
    base_url: str
    app_id: str = ""
    secret: str = ""
    enabled: bool = False
    secret_configured: bool = False


class LLMConfig(BaseModel):
    active_provider_id: str = ""
    providers: list[RuntimeProviderConfig] = Field(default_factory=list)
    provider: str = ""
    api_key: str = ""
    api_url: str = ""
    model: str = ""
    model_options: list[str] = Field(default_factory=list)
    enabled: bool = False


class RuntimeSettingsResponse(BaseModel):
    delilegal: DeliLegalConfig
    llm: LLMConfig


class RuntimeSettingsUpdateRequest(BaseModel):
    delilegal: DeliLegalConfig
    llm: LLMConfig


class RuntimeProviderTestRequest(BaseModel):
    provider: RuntimeProviderConfig


class RuntimeProviderTestResponse(BaseModel):
    ok: bool
    provider_id: str
    provider_type: str = "openai_compatible"
    model: str = ""
    latency_ms: int | None = None
    usage: dict[str, int | str] = Field(default_factory=dict)
    error_code: str = ""
    error_category: str = ""
    error: str = ""
    model_discovery: str = "unsupported_or_failed"
    available_models: list[str] = Field(default_factory=list)


class DeliLegalTestRequest(BaseModel):
    config: DeliLegalConfig


class DeliLegalTestResponse(BaseModel):
    ok: bool
    base_url: str = ""
    latency_ms: int | None = None
    result_count: int = 0
    error_code: str = ""
    error_category: str = ""
    error: str = ""
