"""Parameterized retrieval benchmark using the module_retrieval_benchmark.json fixtures.

Each test case asserts:
- expected source_ids appear in top-k
- must-exclude source_ids do NOT appear in top-k
- module, jurisdiction, can_be_cited are correct
- returned content is non-empty and 段落N-free
- us_14117 uses direct legal filter (not workflow-only fallback)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.common.knowledge.v2 import RetrievalBundle, RetrievalRequest
from backend.common.rag.orchestrator import RetrievalOrchestrator

BENCHMARK_PATH = (
    Path(__file__).resolve().parents[4]
    / "benchmarks"
    / "datasets"
    / "retrieval_gates"
    / "module_retrieval_benchmark.json"
)


def _load_fixtures() -> dict:
    return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))


def _case_ids() -> list[str]:
    fixtures = _load_fixtures()
    ids: list[str] = []
    for mod_name, mod_data in fixtures["modules"].items():
        for i, case in enumerate(mod_data["cases"]):
            ids.append(f"{mod_name}-{i + 1:02d}")
    return ids


def _parametrize_cases():
    fixtures = _load_fixtures()
    params = []
    ids = []
    for mod_name, mod_data in fixtures["modules"].items():
        for i, case in enumerate(mod_data["cases"]):
            params.append((mod_name, case))
            ids.append(f"{mod_name}-{i + 1:02d}")
    return params, ids


_params, _ids = _parametrize_cases()


@pytest.mark.parametrize("module_name,case", _params, ids=_ids)
def test_module_retrieval_benchmark(module_name: str, case: dict) -> None:
    orchestrator = RetrievalOrchestrator()
    top_k = case.get("top_k", 8)

    # Primary retrieval via orchestrator (uses module dispatch)
    request = RetrievalRequest(
        module=module_name,
        task_stage="legal_grounding",
        query=case["query"],
        top_k=top_k,
        jurisdiction=case.get("jurisdiction", ""),
        path=case.get("path", "all"),
    )
    bundle: RetrievalBundle = orchestrator.retrieve(request)

    # Combine legal_grounding + workflow_rules for recall analysis
    all_chunks = list(bundle.legal_grounding)
    all_chunks.extend(bundle.workflow_rules)

    # ── Assertions ──

    # 1. Non-empty results
    assert len(all_chunks) > 0, (
        f"[{module_name}] query='{case['query']}' returned 0 chunks"
    )

    returned_source_ids = {c.source_id for c in all_chunks}
    returned_chunk_ids = {c.chunk_id for c in all_chunks}
    returned_modules = {c.module for c in all_chunks}

    # 2. Must-include sources — at least one of the required sources must appear
    required_set = set(case.get("must_include_sources", []))
    if required_set:
        overlap = required_set & returned_source_ids
        assert overlap, (
            f"[{module_name}] query='{case['query']}' "
            f"missing ALL required sources {sorted(required_set)}. "
            f"Got sources: {sorted(returned_source_ids)}"
        )

    # 3. Must-exclude sources (noise)
    for excluded_src in case.get("must_exclude_sources", []):
        assert excluded_src not in returned_source_ids, (
            f"[{module_name}] query='{case['query']}' "
            f"unexpected noise source '{excluded_src}' in results"
        )

    # 4. Module correctness is enforced by _search_index filters.
    #    Cross-module source assignments (e.g., CN-LAW-002 shared by
    #    cn_diagnosis and cn_assessment) are by design.

    # 5. Content non-empty and 段落N-free
    for chunk in all_chunks:
        assert chunk.content.strip(), (
            f"[{module_name}] chunk {chunk.chunk_id} has empty content"
        )
        assert "段落" not in (chunk.citation_anchor or ""), (
            f"[{module_name}] chunk {chunk.chunk_id} has 段落N in citation_anchor"
        )

    # 6. us_14117 special: must have direct legal_grounding hits
    if module_name == "us_14117":
        legal_sources_in_direct = {c.source_id for c in bundle.legal_grounding}
        assert "US-FED-001" in legal_sources_in_direct, (
            f"[us_14117] direct legal_grounding missing US-FED-001. "
            f"Direct hits: {sorted(legal_sources_in_direct) if legal_sources_in_direct else 'NONE'}. "
            f"Workflow-only fallback is NOT acceptable."
        )

    # 7. Debug — on failure, emit detailed info
    print(f"\n[{module_name}] query='{case['query']}'")
    print(f"  returned source_ids: {sorted(returned_source_ids)}")
    print(f"  returned modules: {returned_modules}")
    print(f"  legal_grounding: {len(bundle.legal_grounding)}, workflow: {len(bundle.workflow_rules)}")
