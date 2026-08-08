"""Local-only application used by the BCR browser acceptance test."""

from __future__ import annotations

from contextlib import asynccontextmanager

from backend.app import create_app
from backend.core.settings import Settings
from backend.domains.eu.bcr_review.service import BCRService


class DisabledBCRBrowserLLM:
    """Keep browser acceptance deterministic after the real-provider CLI run."""

    enabled = False

    def chat(self, **_kwargs) -> str:
        raise AssertionError("BCR browser acceptance must not call an external LLM")


settings = Settings(
    app_env="test",
    llm_provider="none",
    llm_api_key=None,
    siliconflow_api_key=None,
    tencent_api_key=None,
    delilegal_app_id=None,
    delilegal_secret=None,
    rag_auto_build_index=False,
    schema_first_bcr_enabled=True,
    task_mode="threaded",
    _env_file=None,
)
app = create_app(settings)
production_lifespan = app.router.lifespan_context


@asynccontextmanager
async def bcr_browser_lifespan(browser_app):
    async with production_lifespan(browser_app):
        from backend.domains.eu.bcr_review import router as bcr_router

        original_service = bcr_router.service
        browser_service = BCRService(llm_client=DisabledBCRBrowserLLM())
        browser_service.schema_first_enabled = True
        bcr_router.service = browser_service
        try:
            yield
        finally:
            bcr_router.service = original_service


app.router.lifespan_context = bcr_browser_lifespan
