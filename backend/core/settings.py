from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./storage/ai4law.db"
    storage_dir: Path = Path("storage")
    upload_dir_name: str = "uploads"
    report_dir_name: str = "reports"
    task_mode: str = "inline"
    delilegal_base_url: str = "https://openapi.delilegal.com"
    delilegal_app_id: str | None = None
    delilegal_secret: str | None = None
    rag_source_jsonl: Path = Path("doc/knowledge/normalized/regulation_articles.jsonl")
    rag_index_path: Path = Path("storage/rag/regulation_index_v2.json")
    rag_embedding_dimension: int = 384
    rag_candidate_pool_size: int = 24
    rag_rerank_candidate_count: int = 12
    rag_auto_build_index: bool = True

    # 腾讯混元 LLM — 兼容无 AI4LAW_ 前缀的环境变量
    tencent_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TENCENT_API_KEY", "AI4LAW_TENCENT_API_KEY"),
    )
    tencent_api_url: str = Field(
        default="https://api.hunyuan.cloud.tencent.com/v1",
        validation_alias=AliasChoices("TENCENT_API_URL", "AI4LAW_TENCENT_API_URL"),
    )
    llm_model: str = "hunyuan-turbos-latest"

    model_config = SettingsConfigDict(
        env_prefix="AI4LAW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / self.upload_dir_name

    @property
    def report_dir(self) -> Path:
        return self.storage_dir / self.report_dir_name


@lru_cache
def get_settings() -> Settings:
    return Settings()
