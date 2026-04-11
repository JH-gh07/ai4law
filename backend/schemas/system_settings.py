from __future__ import annotations

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "tencent_hunyuan"
    api_key: str = ""
    api_url: str = ""
    model: str = ""
    model_options: list[str] = Field(default_factory=list)
    enabled: bool = False


class DeliLegalConfig(BaseModel):
    base_url: str
    app_id: str = ""
    secret: str = ""
    enabled: bool = False


class CustomProviderConfig(BaseModel):
    id: str
    name: str
    api_key: str = ""
    api_url: str = ""
    model: str = ""
    enabled: bool = False


class RuntimeSettingsResponse(BaseModel):
    delilegal: DeliLegalConfig
    llm: LLMConfig
    custom_providers: list[CustomProviderConfig] = Field(default_factory=list)


class RuntimeSettingsUpdateRequest(BaseModel):
    delilegal: DeliLegalConfig
    llm: LLMConfig
    custom_providers: list[CustomProviderConfig] = Field(default_factory=list)
