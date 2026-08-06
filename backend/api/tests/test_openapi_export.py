from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.export_openapi import export_openapi


EXPECTED_REQUEST_PATHS = {
    "/api/v1/diagnosis/report",
    "/api/v1/assessment/generate_async",
    "/api/v1/review/generate_async",
    "/api/v1/pipia/generate_async",
    "/api/v1/bcr/generate_async",
    "/api/v1/dpia/generate_async",
    "/api/v1/tia/generate_async",
    "/api/v1/cn-flow/generate_async",
    "/api/v1/us_14117/generate_async",
    "/api/v1/eu_scc/generate_async",
    "/api/v1/cpra/generate_async",
}


def test_export_openapi_is_deterministic_and_complete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AI4LAW_LLM_API_KEY", "must-not-be-used")
    monkeypatch.setenv("AI4LAW_DELILEGAL_SECRET", "must-not-be-used")
    first = tmp_path / "first.json"
    second = tmp_path / "nested" / "second.json"

    first_metadata = export_openapi(first)
    second_metadata = export_openapi(second)

    assert first.read_bytes() == second.read_bytes()
    schema = json.loads(first.read_text(encoding="utf-8"))
    assert EXPECTED_REQUEST_PATHS <= schema["paths"].keys()
    assert "/__contract__/state" not in schema["paths"]
    assert first_metadata == second_metadata == {
        "llm_provider": "none",
        "rag_auto_build_index": False,
        "delilegal_configured": False,
    }


def test_export_openapi_is_callable_from_a_clean_python_process(tmp_path: Path) -> None:
    output = tmp_path / "subprocess.json"
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "from scripts.export_openapi import export_openapi; "
                f"export_openapi(Path({str(output)!r}))"
            ),
        ],
        check=True,
        cwd=Path(__file__).parents[3],
    )
    assert output.exists()
