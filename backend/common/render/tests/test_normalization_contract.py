import json
from pathlib import Path

import pytest

from backend.common.llm.postprocess import normalize_legal_markdown_structure

CASES_PATH = Path(__file__).parents[1] / "normalization_test_cases.json"
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))["test_cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_backend_matches_normalization_contract(case: dict[str, str]) -> None:
    assert normalize_legal_markdown_structure(case["input"]) == case["expected"]
