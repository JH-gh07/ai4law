"""Local-only application used by the PIPIA browser acceptance test."""

from __future__ import annotations

from contextlib import asynccontextmanager

from backend.app import create_app
from backend.core.settings import Settings


class DeterministicPIPIALLM:
    enabled = True

    def __init__(self) -> None:
        self.calls = 0

    def chat(self, **kwargs) -> str:
        self.calls += 1
        marker = next(
            line.split(" = ", 1)[0]
            for line in kwargs["user"].splitlines()
            if line.startswith("{{CIT-")
        )
        return (
            f"第{self.calls}章本地浏览器验收结论：当前材料需要在备案前完成复核。"
            f"{marker}"
        )


settings = Settings(
    app_env="test",
    llm_provider="none",
    llm_api_key=None,
    siliconflow_api_key=None,
    tencent_api_key=None,
    delilegal_app_id=None,
    delilegal_secret=None,
    rag_auto_build_index=False,
    schema_first_pipia_enabled=True,
    task_mode="threaded",
    _env_file=None,
)
app = create_app(settings)
production_lifespan = app.router.lifespan_context


@asynccontextmanager
async def pipia_browser_lifespan(browser_app):
    async with production_lifespan(browser_app):
        from backend.domains.cn.pipia.router import service

        original_client = service.llm_client
        original_schema_first = service.renderer.schema_first_enabled
        service.llm_client = DeterministicPIPIALLM()
        service.renderer.schema_first_enabled = True
        try:
            yield
        finally:
            service.llm_client = original_client
            service.renderer.schema_first_enabled = original_schema_first


app.router.lifespan_context = pipia_browser_lifespan
