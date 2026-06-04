from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router import api_router
from backend.core.container import AppContainer
from backend.core.runtime_settings import (
    apply_runtime_payload,
    load_runtime_overrides,
    refresh_runtime_clients,
)
from backend.core.db import init_db
from backend.core.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    container: AppContainer = app.state.container
    init_db(container.engine)

    # 后台周期性清理 SSEManager 中已过期 task 的事件数据
    import asyncio as _asyncio
    from backend.common.events.manager import get_ssemanager

    async def _cleanup_loop():
        while True:
            await _asyncio.sleep(600)  # 每 10 分钟执行一次
            try:
                get_ssemanager().cleanup_expired()
            except Exception:
                pass

    cleanup_task = _asyncio.create_task(_cleanup_loop())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except _asyncio.CancelledError:
        pass


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    container = AppContainer(resolved_settings)
    runtime_overrides = load_runtime_overrides(container.settings)
    if runtime_overrides:
        apply_runtime_payload(container.settings, runtime_overrides)
    refresh_runtime_clients(container)

    app = FastAPI(
        title="AI4Law Backend MVP",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.container = container
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
