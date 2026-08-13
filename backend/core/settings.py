from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field
from pydantic import PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.common.knowledge.paths import regulation_articles_jsonl_path


class Settings(BaseSettings):
    _runtime_llm_providers: list[dict[str, Any]] | None = PrivateAttr(default=None)
    _runtime_llm_active_provider_id: str = PrivateAttr(default="")
    _runtime_provider_health: dict[str, dict[str, Any]] = PrivateAttr(default_factory=dict)

    app_env: str = "development"
    database_url: str = "sqlite:///./storage/ai4law.db"
    storage_dir: Path = Path("storage")
    upload_dir_name: str = "uploads"
    report_dir_name: str = "reports"
    task_mode: str = "threaded"
    delilegal_base_url: str = "https://openapi.delilegal.com"
    delilegal_app_id: str | None = None
    delilegal_secret: str | None = None
    rag_source_jsonl: Path = Field(default_factory=regulation_articles_jsonl_path)
    rag_index_path: Path = Path("storage/rag/regulation_index_v2.json")
    rag_user_materials_index_path: Path = Path("storage/rag/user_materials_index_v2.json")
    rag_v3_dir: Path = Path("storage/rag/v3")
    rag_embedding_dimension: int = 384
    rag_candidate_pool_size: int = 24
    rag_rerank_candidate_count: int = 12
    rag_auto_build_index: bool = True
    # Schema-first validation is opt-in per module until module snapshots pass.
    schema_first_assessment_enabled: bool = False
    schema_first_dpia_enabled: bool = False
    schema_first_tia_enabled: bool = False
    schema_first_pipia_enabled: bool = False
    schema_first_bcr_enabled: bool = False
    # Task067 T09 — when True (and schema_first_bcr_enabled), the *formal* BCR
    # output_files point at the IR renderer (report.md/docx/pdf) + render manifest,
    # and legacy template files are parked under shadow_legacy/ instead of being
    # registered as user artifacts. False keeps the legacy template outputs as the
    # official artifacts while the IR version is shadow-rendered to shadow_ir/.
    # TEMPORARY shadow switch — REMOVE by 2026-09-01 (task067 §T11). It exists
    # only until the two environment gates in status/check/task067/task067_验收报告.md
    # pass: ① licensed+hashed CJK font (pdf_font_embedding) and ② LibreOffice
    # headless (DOCX visual). On removal: default this flag to True, archive the
    # legacy templates, and delete the shadow_legacy/shadow_ir directory branches
    # in service.py.
    bcr_report_ir_rendering_enabled: bool = False
    # task068 T11 — two-flag shadow/switch discipline for the vertical modules.
    # ``schema_first_<module>_enabled`` builds + compiles the DocumentIR (fail-closed);
    # ``<module>_report_ir_rendering_enabled`` then decides whether the *official*
    # outputs point at the IR renderer (True) or stay legacy while the IR is
    # shadow-rendered to ``shadow_ir/`` (False). Keeping both off is the legacy
    # writer, so rollback is "turn the rendering flag off" — never delete IR artifacts.
    cpra_report_ir_rendering_enabled: bool = False
    eo14117_report_ir_rendering_enabled: bool = False
    dpia_report_ir_rendering_enabled: bool = False
    review_report_ir_rendering_enabled: bool = False
    schema_first_scc_enabled: bool = False
    schema_first_cpra_enabled: bool = False
    schema_first_eo14117_enabled: bool = False
    schema_first_document_review_enabled: bool = False

    # OpenAI-compatible LLM config. Provider order in auto mode:
    # generic LLM_* -> SiliconFlow -> legacy Tencent Hunyuan.
    llm_provider: str = Field(
        default="auto",
        validation_alias=AliasChoices("LLM_PROVIDER", "AI4LAW_LLM_PROVIDER"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "AI4LAW_LLM_API_KEY"),
    )
    llm_api_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("LLM_API_URL", "AI4LAW_LLM_API_URL"),
    )
    tencent_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TENCENT_API_KEY",
            "AI4LAW_TENCENT_API_KEY",
        ),
    )
    tencent_api_url: str = Field(
        default="https://tokenhub.tencentmaas.com/v1",
        validation_alias=AliasChoices(
            "TENCENT_API_URL",
            "AI4LAW_TENCENT_API_URL",
        ),
    )
    tencent_model: str = Field(
        default="hy3-preview",
        validation_alias=AliasChoices(
            "TENCENT_MODEL",
            "AI4LAW_TENCENT_MODEL",
        ),
    )
    siliconflow_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SILICONFLOW_API_KEY",
            "SICICONFLOW_API_KEY",
            "AI4LAW_SILICONFLOW_API_KEY",
            "AI4LAW_SICICONFLOW_API_KEY",
        ),
    )
    siliconflow_api_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        validation_alias=AliasChoices(
            "SILICONFLOW_API_URL",
            "SICICONFLOW_API_URL",
            "AI4LAW_SILICONFLOW_API_URL",
            "AI4LAW_SICICONFLOW_API_URL",
        ),
    )
    siliconflow_model: str = Field(
        default="deepseek-ai/DeepSeek-V3.2",
        validation_alias=AliasChoices(
            "SILICONFLOW_MODEL",
            "SICICONFLOW_MODEL",
            "AI4LAW_SILICONFLOW_MODEL",
            "AI4LAW_SICICONFLOW_MODEL",
        ),
    )
    llm_model: str = Field(
        default="deepseek-ai/DeepSeek-V3.2",
        validation_alias=AliasChoices("LLM_MODEL", "AI4LAW_LLM_MODEL"),
    )

    model_config = SettingsConfigDict(
        env_prefix="AI4LAW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / self.upload_dir_name

    @property
    def report_dir(self) -> Path:
        return self.storage_dir / self.report_dir_name

    @property
    def resolved_llm_provider(self) -> str:
        provider = (self.llm_provider or "auto").strip().lower()
        if provider != "auto":
            return provider
        if self.llm_api_key:
            return "generic"
        if self.siliconflow_api_key:
            return "siliconflow"
        if self.tencent_api_key:
            return "tencent_hunyuan"
        return "none"

    @property
    def resolved_llm_api_key(self) -> str | None:
        provider = self.resolved_llm_provider
        if provider == "siliconflow":
            return self.siliconflow_api_key or self.llm_api_key
        if provider in {"tencent", "tencent_hunyuan"}:
            return self.tencent_api_key or self.llm_api_key
        if provider == "none":
            return None
        return self.llm_api_key or self.siliconflow_api_key or self.tencent_api_key

    @property
    def resolved_llm_api_url(self) -> str:
        provider = self.resolved_llm_provider
        if provider == "siliconflow":
            return self._normalize_openai_base_url(self.siliconflow_api_url)
        if provider in {"tencent", "tencent_hunyuan"}:
            return self._normalize_openai_base_url(self.tencent_api_url)
        return self._normalize_openai_base_url(self.llm_api_url)

    @property
    def resolved_llm_model(self) -> str:
        provider = self.resolved_llm_provider
        if provider == "siliconflow":
            return self.siliconflow_model
        if provider in {"tencent", "tencent_hunyuan"}:
            return self.tencent_model
        return self.llm_model

    @staticmethod
    def _normalize_openai_base_url(url: str) -> str:
        normalized = (url or "").strip().rstrip("/")
        suffix = "/chat/completions"
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
