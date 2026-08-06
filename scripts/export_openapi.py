from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


_ISOLATED_ENV = {
    "AI4LAW_APP_ENV": "test",
    "AI4LAW_LLM_PROVIDER": "none",
    "AI4LAW_LLM_API_KEY": "",
    "AI4LAW_SILICONFLOW_API_KEY": "",
    "AI4LAW_TENCENT_API_KEY": "",
    "AI4LAW_DELILEGAL_APP_ID": "",
    "AI4LAW_DELILEGAL_SECRET": "",
    "AI4LAW_RAG_AUTO_BUILD_INDEX": "false",
}


def export_openapi(output: Path) -> dict[str, str | bool]:
    output = output.resolve()
    original_cwd = Path.cwd()
    original_env = {key: os.environ.get(key) for key in _ISOLATED_ENV}

    with TemporaryDirectory(prefix="ai4law-openapi-") as raw_workspace:
        workspace = Path(raw_workspace).resolve()
        try:
            os.environ.update(_ISOLATED_ENV)
            os.chdir(workspace)

            from backend.app import create_app
            from backend.core.settings import Settings

            settings = Settings(
                app_env="test",
                database_url=f"sqlite:///{workspace / 'openapi.db'}",
                storage_dir=workspace / "storage",
                llm_provider="none",
                llm_api_key=None,
                siliconflow_api_key=None,
                tencent_api_key=None,
                delilegal_app_id=None,
                delilegal_secret=None,
                rag_auto_build_index=False,
                _env_file=None,
            )
            schema: dict[str, Any] = create_app(settings).openapi()
        finally:
            os.chdir(original_cwd)
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "llm_provider": settings.resolved_llm_provider,
        "rag_auto_build_index": settings.rag_auto_build_index,
        "delilegal_configured": bool(settings.delilegal_app_id and settings.delilegal_secret),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the isolated FastAPI OpenAPI schema.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    export_openapi(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
