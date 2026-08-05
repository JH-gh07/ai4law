from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
from tempfile import TemporaryDirectory


def _set_contract_environment(workspace: Path) -> None:
    values = {
        "AI4LAW_APP_ENV": "test",
        "AI4LAW_LLM_PROVIDER": "none",
        "AI4LAW_LLM_API_KEY": "",
        "AI4LAW_SILICONFLOW_API_KEY": "",
        "AI4LAW_TENCENT_API_KEY": "",
        "AI4LAW_DELILEGAL_APP_ID": "",
        "AI4LAW_DELILEGAL_SECRET": "",
        "AI4LAW_RAG_AUTO_BUILD_INDEX": "false",
        "AI4LAW_DATABASE_URL": f"sqlite:///{workspace / 'contract.db'}",
        "AI4LAW_STORAGE_DIR": str(workspace / "storage"),
        "AI4LAW_TASK_MODE": "threaded",
    }
    os.environ.update(values)


def _build_contract_app():
    requested_root = os.environ.get("AI4LAW_CONTRACT_TMP_ROOT", "").strip()
    temp_parent = Path(requested_root).resolve() if requested_root else None
    if temp_parent is not None:
        temp_parent.mkdir(parents=True, exist_ok=True)
    workspace_owner = TemporaryDirectory(
        prefix="ai4law-contract-",
        dir=str(temp_parent) if temp_parent is not None else None,
    )
    workspace = Path(workspace_owner.name).resolve()
    original_cwd = Path.cwd()
    _set_contract_environment(workspace)
    os.chdir(workspace)

    from backend.app import create_app
    from backend.core.settings import Settings
    from backend.tests.contract_support import (
        LocalhostOnlyNetworkGuard,
        install_recording_execution,
    )

    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{workspace / 'contract.db'}",
        storage_dir=workspace / "storage",
        llm_provider="none",
        llm_api_key=None,
        siliconflow_api_key=None,
        tencent_api_key=None,
        delilegal_app_id=None,
        delilegal_secret=None,
        rag_auto_build_index=False,
        task_mode="threaded",
        _env_file=None,
    )
    app = create_app(settings)
    isolation = install_recording_execution(app)
    network_guard = LocalhostOnlyNetworkGuard()
    production_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def contract_lifespan(contract_app):
        network_guard.install()
        try:
            async with production_lifespan(contract_app):
                yield
        finally:
            network_guard.restore()
            isolation.restore()
            os.chdir(original_cwd)
            workspace_owner.cleanup()

    app.router.lifespan_context = contract_lifespan

    @app.get("/__contract__/state", include_in_schema=False)
    def contract_state() -> dict[str, int | bool]:
        return {
            "manager_count": len(isolation.manager_executors),
            "submission_count": isolation.submission_count,
            "external_network_blocked": network_guard.installed,
        }

    app.state.contract_isolation = isolation
    app.state.contract_network_guard = network_guard
    app.state.contract_workspace = workspace
    return app


app = _build_contract_app()
