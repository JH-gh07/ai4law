from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.v0.router import v0_router
from backend.api.v1.router import v1_router
from backend.core.container import AppContainer
from backend.core.runtime_settings import (
    apply_runtime_payload,
    load_runtime_overrides,
)
from backend.core.db import init_db
from backend.core.settings import Settings, get_settings
from backend.services.runtime_client_refresher import refresh_runtime_clients


@asynccontextmanager
async def lifespan(app: FastAPI):
    container: AppContainer = app.state.container
    init_db(container.engine)

    # 后台周期性清理 SSEManager 中已过期 task 的事件数据
    import asyncio as _asyncio
    from backend.common.events.manager import get_ssemanager

    get_ssemanager(container.session_factory)

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
        title="DataComplyFlow Backend",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.container = container
    app.include_router(v0_router, prefix="/api/v0")
    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
