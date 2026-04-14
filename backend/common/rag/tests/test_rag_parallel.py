"""并行双路检索单元测试。

验证 retrieve_regulations() 中的 ThreadPoolExecutor 并行逻辑：
- 本地检索和得理 API 同时启动
- 得理超时时降级为只用本地结果
- 得理 disabled 时不创建多余线程
- 同标题去重
- 本地 P0/P1 结果排在得理 P2 之前
"""
from __future__ import annotations

import time
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.common.rag.retriever import RegulationDoc, retrieve_regulations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(title: str, priority: str = "P0", jurisdiction: str = "cn") -> RegulationDoc:
    return RegulationDoc(
        id=f"id-{title}",
        title=title,
        article="第1条",
        content="内容",
        jurisdiction=jurisdiction,
        path="all",
        doc_type="law",
        usage_priority=priority,
    )


def _make_legal_service(hits: list[dict], delay: float = 0.0, enabled: bool = True) -> MagicMock:
    svc = MagicMock()
    svc.enabled = enabled

    def _search(query: str, size: int) -> list[dict]:
        if delay:
            time.sleep(delay)
        return hits

    svc.search_laws.side_effect = _search
    return svc


def _make_local_retrieve(docs: list[RegulationDoc], delay: float = 0.0):
    """返回一个 mock service，其 retrieve() 方法有延迟并返回指定文档。"""
    svc = MagicMock()

    def _retrieve(*args: Any, **kwargs: Any) -> list[RegulationDoc]:
        if delay:
            time.sleep(delay)
        return list(docs)

    svc.retrieve.side_effect = _retrieve
    return svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parallel_both_succeed() -> None:
    """本地(0.1s) + 得理(0.2s) 同时启动，总耗时应 < 0.35s（并行），结果合并正确。"""
    local_docs = [_make_doc("本地法规A"), _make_doc("本地法规B")]
    deli_hits = [{"title": "得理法规X", "summary": "摘要X"}]

    mock_svc = _make_local_retrieve(local_docs, delay=0.1)
    legal_svc = _make_legal_service(deli_hits, delay=0.2)

    with patch("backend.common.rag.retriever._service", return_value=mock_svc), \
         patch("backend.common.rag.retriever._get_default_legal_service", return_value=legal_svc):
        t0 = time.monotonic()
        docs = retrieve_regulations("数据出境", top_k=8, legal_service=legal_svc)
        elapsed = time.monotonic() - t0

    assert elapsed < 0.35, f"并行耗时应 < 0.35s，实际 {elapsed:.3f}s"
    titles = [d.title for d in docs]
    assert "本地法规A" in titles
    assert "本地法规B" in titles
    assert "得理法规X" in titles


def test_deli_timeout_graceful() -> None:
    """得理超时时，不抛异常，只返回本地结果。"""
    local_docs = [_make_doc("本地法规A")]
    # 延迟远超 timeout=12 的情况用 Exception 模拟（避免测试真等12秒）
    mock_svc = _make_local_retrieve(local_docs)
    legal_svc = MagicMock()
    legal_svc.enabled = True
    legal_svc.search_laws.side_effect = TimeoutError("模拟超时")

    with patch("backend.common.rag.retriever._service", return_value=mock_svc), \
         patch("backend.common.rag.retriever._get_default_legal_service", return_value=legal_svc):
        docs = retrieve_regulations("数据出境", top_k=8, legal_service=legal_svc)

    assert [d.title for d in docs] == ["本地法规A"]
    # 得理异常不影响返回值
    assert all(d.doc_type != "external" for d in docs)


def test_deli_disabled_no_external_call() -> None:
    """legal_service.enabled=False 时，search_laws 不被调用。"""
    local_docs = [_make_doc("本地法规A")]
    mock_svc = _make_local_retrieve(local_docs)
    legal_svc = _make_legal_service([], enabled=False)

    with patch("backend.common.rag.retriever._service", return_value=mock_svc), \
         patch("backend.common.rag.retriever._get_default_legal_service", return_value=legal_svc):
        docs = retrieve_regulations("数据出境", top_k=8, legal_service=legal_svc)

    legal_svc.search_laws.assert_not_called()
    assert len(docs) == 1
    assert docs[0].title == "本地法规A"


def test_dedup_by_title() -> None:
    """本地和得理返回同标题文档，合并后不重复。"""
    local_docs = [_make_doc("重叠法规")]
    deli_hits = [
        {"title": "重叠法规", "summary": "得理摘要"},  # 重复，应去重
        {"title": "新法规Y", "summary": "新摘要"},      # 新增
    ]
    mock_svc = _make_local_retrieve(local_docs)
    legal_svc = _make_legal_service(deli_hits)

    with patch("backend.common.rag.retriever._service", return_value=mock_svc), \
         patch("backend.common.rag.retriever._get_default_legal_service", return_value=legal_svc):
        docs = retrieve_regulations("数据出境", top_k=8, legal_service=legal_svc)

    titles = [d.title for d in docs]
    assert titles.count("重叠法规") == 1, "同标题文档不应重复"
    assert "新法规Y" in titles


def test_local_results_before_deli() -> None:
    """本地 P0/P1 文档始终排在得理 P2 文档之前。"""
    local_docs = [_make_doc("本地P0法规", priority="P0")]
    deli_hits = [{"title": "得理外部法规", "summary": "外部摘要"}]
    mock_svc = _make_local_retrieve(local_docs)
    legal_svc = _make_legal_service(deli_hits)

    with patch("backend.common.rag.retriever._service", return_value=mock_svc), \
         patch("backend.common.rag.retriever._get_default_legal_service", return_value=legal_svc):
        docs = retrieve_regulations("数据出境", top_k=8, legal_service=legal_svc)

    assert len(docs) >= 2
    # 本地结果在前
    assert docs[0].title == "本地P0法规"
    assert docs[0].usage_priority == "P0"
    # 得理结果在后
    assert docs[-1].title == "得理外部法规"
    assert docs[-1].usage_priority == "P2"
    assert docs[-1].doc_type == "external"
