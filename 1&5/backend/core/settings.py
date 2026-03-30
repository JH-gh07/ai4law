from functools import lru_cache
from pathlib import Path

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

    model_config = SettingsConfigDict(env_prefix="AI4LAW_", extra="ignore")

    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / self.upload_dir_name

    @property
    def report_dir(self) -> Path:
        return self.storage_dir / self.report_dir_name


@lru_cache
def get_settings() -> Settings:
    return Settings()
