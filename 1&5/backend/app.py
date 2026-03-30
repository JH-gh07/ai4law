from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router import api_router
from backend.core.container import AppContainer
from backend.core.db import init_db
from backend.core.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    container: AppContainer = app.state.container
    init_db(container.engine)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    container = AppContainer(resolved_settings)

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
