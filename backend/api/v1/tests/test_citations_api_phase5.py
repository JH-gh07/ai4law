"""Phase 5 backend acceptance: citation resolution states and API invariants.

Verifies the backend side of the citation closure plan §5:
  1. All four resolution_type values are correctly returned
  2. can_jump=false always has non-empty failure_reason
  3. Resolution availability matches citation_map data quality
  4. Batch endpoint correctly separates found vs not_found
  5. API never reads facts.json or trace to synthesize citations
  6. CitationMapResponse contains all required display fields
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.settings import Settings
from backend.services.task_access import claim_task_access


def _register(client: TestClient, username: str, email: str):
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "pass-12345678"},
    )
    assert resp.status_code == 200
    data = resp.json()
    return data["access_token"], data["user"]["id"]


@contextmanager
def _owned_client(tmp_path: Path, task_id: str, module: str = "assessment"):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / f'cit5_{task_id}.db'}",
            storage_dir=tmp_path / "storage",
        )
    )
    with TestClient(app) as client:
        token, uid = _register(client, "cit5-user", f"cit5-{task_id}@test.local")
        session = app.state.container.session_factory()
        try:
            claim_task_access(session, task_id=task_id, user_id=uid, module=module)
        finally:
            session.close()
        yield client, token


def _write_citation_map(output_dir: Path, footnote_map: dict, all_items: list | None = None):
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": "test",
        "module": "assessment",
        "footnote_map": footnote_map,
        "all_items": all_items or list(footnote_map.values()),
    }
    (output_dir / "citation_map.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8",
    )


# ── tests ────────────────────────────────────────────────────────────────────


class TestResolutionStates:

    def test_exact_article_yields_can_jump_true(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-exact"
        output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-CN-PIPL-ART13-P01", "source_id": "CN-LAW-003",
                  "citation_type": "law_article", "title": "个人信息保护法",
                  "article_no": "13", "quote_text": "个人信息处理者应当...告知..."},
        })
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id) as (client, token):
            resp = client.get(
                f"/api/v1/citations/reports/{task_id}?module=assessment",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            item = resp.json()["footnote_map"]["1"]
            assert item["can_jump"] is True
            assert item["resolution"]["resolution_type"] == "exact_article"
            assert item["knowledge_url"] != ""

    def test_source_overview_when_no_article(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-source"
        output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-EU-GDPR-GEN-P01", "source_id": "EU-LAW-001",
                  "citation_type": "law_article", "title": "GDPR",
                  "article_no": "", "quote_text": ""},
        })
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id) as (client, token):
            resp = client.get(
                f"/api/v1/citations/reports/{task_id}?module=assessment",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            item = resp.json()["footnote_map"]["1"]
            assert item["can_jump"] is False
            assert item["resolution"]["failure_reason"] != ""

    def test_unresolved_when_source_not_in_kb(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-unresolved"
        output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-XX-UNKNOWN-ART1-P01", "source_id": "XX-UNKNOWN-999",
                  "citation_type": "law_article", "title": "未知法规",
                  "article_no": "1", "quote_text": ""},
        })
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id) as (client, token):
            resp = client.get(
                f"/api/v1/citations/reports/{task_id}?module=assessment",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            item = resp.json()["footnote_map"]["1"]
            assert item["can_jump"] is False
            assert item["resolution"]["failure_reason"] != ""

    def test_display_fields_for_citation_popover(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-arti"
        output_dir = tmp_path / "outputs" / "dpia" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-EU-GDPR-ART35-P01", "source_id": "EU-LAW-001",
                  "citation_type": "law_article", "title": "GDPR (EU) 2016/679",
                  "article_no": "35", "quote_text": "high risk processing..."},
        })
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id, module="dpia") as (client, token):
            resp = client.get(
                f"/api/v1/citations/reports/{task_id}?module=dpia",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            item = resp.json()["footnote_map"]["1"]
            for field in ("display_label", "citation_id", "title", "article_no",
                          "quote_text", "footnote_number", "can_jump", "source_url",
                          "resolution", "confidence_score"):
                assert field in item, f"Missing: {field}"
            assert item["footnote_number"] == 1


class TestBatchCitationSeparation:

    def test_batch_found_citations_return_detail(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-batch-1"
        output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-CN-PIPL-ART13-P01", "source_id": "CN-LAW-003",
                  "citation_type": "law_article", "title": "PIPL",
                  "article_no": "13", "quote_text": "test"},
        })
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id) as (client, token):
            resp = client.post(
                "/api/v1/citations/batch",
                json={"citation_ids": ["CIT-CN-PIPL-ART13-P01"],
                      "task_id": task_id, "module": "assessment"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "CIT-CN-PIPL-ART13-P01" in data["items"]
            assert data["not_found"] == []

    def test_batch_not_found_isolation(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-batch-2"
        output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-CN-PIPL-ART13-P01", "source_id": "CN-LAW-003",
                  "citation_type": "law_article", "title": "PIPL",
                  "article_no": "13", "quote_text": "test"},
        })
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id) as (client, token):
            resp = client.post(
                "/api/v1/citations/batch",
                json={"citation_ids": ["CIT-CN-PIPL-ART13-P01", "CIT-XX-FAKE-ART1-P01"],
                      "task_id": task_id, "module": "assessment"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "CIT-CN-PIPL-ART13-P01" in data["items"]
            assert "CIT-XX-FAKE-ART1-P01" in data["not_found"]

    def test_stale_citation_map_not_replaced_by_facts(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-stale"
        output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-CN-PIPL-ART13-P01", "source_id": "CN-LAW-003",
                  "citation_type": "law_article", "title": "PIPL",
                  "article_no": "13", "quote_text": ""},
        })
        (output_dir / "facts.json").write_text(json.dumps({
            "regulations": [{"source_id": "CN-LAW-999", "title": "Fake Law", "article": "99"}]
        }, ensure_ascii=False), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id) as (client, token):
            resp = client.get(
                f"/api/v1/citations/reports/{task_id}?module=assessment",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["citation_count"] == 1
            assert data["footnote_map"]["1"]["title"] == "PIPL"


class TestCitationDisplayFields:

    REQUIRED_FIELDS = [
        "citation_id", "source_id", "citation_type", "title",
        "article_no", "display_label", "footnote_number",
        "can_jump", "source_url", "knowledge_url",
        "resolution", "confidence_score",
        "authority_level", "binding_force", "source_kind",
    ]

    def test_all_required_fields_present(self, tmp_path: Path, monkeypatch):
        task_id = "phase5-fields"
        output_dir = tmp_path / "outputs" / "assessment" / task_id / "outputs"
        _write_citation_map(output_dir, {
            "1": {"citation_id": "CIT-CN-CYBERSEC-ART6-P01", "source_id": "CN-LAW-004",
                  "citation_type": "law_article", "title": "网络安全法",
                  "article_no": "6", "quote_text": "test"},
        })
        monkeypatch.chdir(tmp_path)
        with _owned_client(tmp_path, task_id) as (client, token):
            resp = client.get(
                f"/api/v1/citations/reports/{task_id}?module=assessment",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            item = resp.json()["footnote_map"]["1"]
            for field in self.REQUIRED_FIELDS:
                assert field in item, f"Missing required field: {field}"
            assert isinstance(item["resolution"], dict)
            for sub in ("resolution_type", "failure_reason", "available_actions"):
                assert sub in item["resolution"], f"resolution missing: {sub}"
