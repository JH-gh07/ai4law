from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.models.review import ReviewTaskModel
from backend.core.settings import Settings
from backend.schemas.review import ClausePosition, ClauseType, ClassifiedClause
from backend.domains.cn.document_review.service import ReviewService
from backend.schemas.review import ReviewGenerateRequest, ReviewGenerateResponse


@contextmanager
def _make_client(tmp_path: Path):
    storage_dir = tmp_path / "storage"
    db_path = tmp_path / "review_async_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=storage_dir,
        task_mode="threaded",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client, app


def _register(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "review_async_user",
            "email": "review_async_user@example.com",
            "password": "review-pass-123",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    return payload["access_token"], payload["user"]["id"]


def test_review_generate_async_status_returns_completed_result(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, app):
        token, user_id = _register(client)
        container = app.state.container
        review_service = container.review_service
        scheduled: dict[str, object] = {}

        def capture_dispatch(func, *args, **kwargs):
            scheduled["func"] = func
            scheduled["args"] = args
            scheduled["kwargs"] = kwargs
            return None

        review_service.task_dispatcher.dispatch = capture_dispatch
        review_service.reviewer.review = (
            lambda clause, use_llm=True, document_type="other", scenario_context=None: []
        )

        sample = container.settings.upload_dir / "sample_review_contract.md"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_text(
            "\n".join(
                [
                    "# 简版数据处理协议",
                    "",
                    "第一条 处理目的",
                    "乙方仅可基于甲方书面指令处理客服工单中的个人信息，不得超出约定目的另作使用。",
                    "",
                    "第二条 数据出境安排",
                    "双方确认相关个人信息将传输至新加坡客服中心处理，乙方应披露存储地点并限制再传输。",
                ]
            ),
            encoding="utf-8",
        )

        accepted = client.post(
            "/api/v1/review/generate_async",
            headers={"Authorization": f"Bearer {token}"},
            json={"uploaded_files": [str(sample)]},
        )
        assert accepted.status_code == 200
        accepted_payload = accepted.json()
        assert accepted_payload["module"] == "review"
        assert accepted_payload["state"] == "UPLOADED"
        assert accepted_payload["progress"] == 10

        task_id = accepted_payload["task_id"]
        assert scheduled["args"] == (task_id, user_id)

        scheduled["func"](*scheduled["args"], **scheduled["kwargs"])

        status = client.get(
            f"/api/v1/review/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status.status_code == 200
        payload = status.json()
        assert payload["module"] == "review"
        assert payload["state"] == "COMPLETED"
        assert payload["progress"] == 100
        assert payload["error"] is None
        assert payload["result"]["output_files"]["docx"].endswith("review_report.docx")
        assert payload["result"]["output_files"]["pdf"].endswith("review_report.pdf")
        assert Path(payload["result"]["report_path"]).exists()
        events = client.get(
            f"/api/v1/events/task/{task_id}/events?since=-1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert events.status_code == 200
        event_payload = events.json()["events"]
        assert event_payload
        assert event_payload[-1]["detail"]["state"] == "COMPLETED"
        assert any(event["event_type"] == "tool_start" for event in event_payload)
        assert any(event["event_type"] == "tool_result" for event in event_payload)
        pdf_path = Path(payload["result"]["output_files"]["pdf"])
        assert pdf_path.read_bytes().startswith(b"%PDF")

        from pypdf import PdfReader

        assert len(PdfReader(pdf_path).pages) >= 1


def test_review_service_restart_marks_incomplete_task_failed(tmp_path: Path) -> None:
    storage_dir = tmp_path / "storage"
    db_path = tmp_path / "review_restart_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=storage_dir,
        task_mode="threaded",
    )

    first_app = create_app(settings)
    with TestClient(first_app) as first_client:
        token, user_id = _register(first_client)
        with first_app.state.container.session_factory() as db:
            db.add_all(
                [
                    ReviewTaskModel(
                        id="stale-review-task",
                        user_id=user_id,
                        status="REVIEWING",
                        progress=57,
                    ),
                    ReviewTaskModel(
                        id="uploaded-review-task",
                        user_id=user_id,
                        status="UPLOADED",
                        progress=10,
                    ),
                ]
            )
            db.commit()

    restarted_app = create_app(settings)
    with TestClient(restarted_app) as restarted_client:
        status = restarted_client.get(
            "/api/v1/review/tasks/stale-review-task",
            headers={"Authorization": f"Bearer {token}"},
        )
        uploaded_status = restarted_client.get(
            "/api/v1/review/tasks/uploaded-review-task",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert status.status_code == 200
    assert status.json()["state"] == "FAILED"
    assert status.json()["progress"] == 57
    assert status.json()["error"] == "Review generation failed"
    assert uploaded_status.status_code == 200
    assert uploaded_status.json()["state"] == "UPLOADED"


def test_review_sync_generation_refreshes_session_after_pipeline(monkeypatch) -> None:
    class FakeSession:
        expired = False

        def expire_all(self) -> None:
            self.expired = True

    db = FakeSession()
    service = object.__new__(ReviewService)
    task = SimpleNamespace(id="review-task", status="UPLOADED")
    monkeypatch.setattr(service, "_create_task_from_request", lambda *_args: task)
    monkeypatch.setattr(service, "_run_pipeline", lambda *_args: None)
    monkeypatch.setattr(
        service,
        "_require_task",
        lambda *_args: SimpleNamespace(
            id="review-task",
            status="COMPLETED" if db.expired else "UPLOADED",
        ),
    )
    expected = ReviewGenerateResponse(
        report_path="report.docx",
        output_files={"docx": "report.docx"},
        risk_level="LOW",
    )
    monkeypatch.setattr(service, "_build_generate_response", lambda *_args: expected)

    result = service.generate_from_request(
        db,
        "user-1",
        ReviewGenerateRequest(uploaded_files=["input.md"]),
    )

    assert db.expired is True
    assert result == expected


def test_review_dev_preset_copies_current_legal_resource_into_storage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "resources" / "legal" / "sources" / "cn" / "snapshots" / "privacy.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Privacy policy fixture", encoding="utf-8")
    upload_dir = tmp_path / "storage" / "uploads"

    service = object.__new__(ReviewService)
    service.file_service = SimpleNamespace(
        settings=SimpleNamespace(storage_dir=tmp_path / "storage", upload_dir=upload_dir),
        allowed_extensions={".md"},
    )

    copied = service._resolve_uploaded_path(str(source))

    assert copied.is_file()
    assert copied.read_text(encoding="utf-8") == "# Privacy policy fixture"
    assert copied.is_relative_to(upload_dir)


def test_review_dev_preset_copies_external_file_into_storage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "private" / "secret.md"
    source.parent.mkdir(parents=True)
    source.write_text("secret", encoding="utf-8")

    upload_dir = tmp_path / "storage" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    service = object.__new__(ReviewService)
    service.file_service = SimpleNamespace(
        settings=SimpleNamespace(storage_dir=tmp_path / "storage", upload_dir=upload_dir),
        allowed_extensions={".md"},
    )

    copied = service._resolve_uploaded_path(str(source))

    assert copied.is_file()
    assert copied.read_text(encoding="utf-8") == "secret"
    assert copied.is_relative_to(upload_dir)


def test_review_dev_preset_rejects_unsupported_extension(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "private" / "secret.exe"
    source.parent.mkdir(parents=True)
    source.write_text("binary", encoding="utf-8")

    upload_dir = tmp_path / "storage" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    service = object.__new__(ReviewService)
    service.file_service = SimpleNamespace(
        settings=SimpleNamespace(storage_dir=tmp_path / "storage", upload_dir=upload_dir),
        allowed_extensions={".md"},
    )

    with pytest.raises(HTTPException) as exc_info:
        service._resolve_uploaded_path(str(source))

    assert exc_info.value.status_code == 400


def test_select_llm_candidates_caps_non_other_clauses() -> None:
    service = ReviewService(
        file_service=None,
        report_service=None,
        task_dispatcher=None,
        websocket_manager=None,
        session_factory=None,
        legal_api_service=None,
        llm_client=None,
    )
    clauses = [
        ClassifiedClause(
            clause_id=f"clause-{index}",
            file_id="file-1",
            text="跨境传输" * 30,
            heading=f"条款 {index}",
            position=ClausePosition(page=1, paragraph=index + 1, clause_number=str(index + 1)),
            clause_type=ClauseType.CROSS_BORDER_TRANSFER if index < 10 else ClauseType.OTHER,
            matched_keywords=["跨境传输", "接收方"] if index < 10 else [],
        )
        for index in range(12)
    ]

    selected = service._select_llm_candidates(clauses)

    assert len(selected) == 10
    assert set(selected) == {f"clause-{index}" for index in range(10)}


def _make_classified_clause(
    text: str,
    clause_type: ClauseType = ClauseType.OTHER,
    matched_keywords: list[str] | None = None,
) -> ClassifiedClause:
    return ClassifiedClause(
        clause_id="clause-test",
        file_id="file-1",
        text=text,
        heading=text[:80],
        position=ClausePosition(page=1, paragraph=1, clause_number=None),
        clause_type=clause_type,
        matched_keywords=matched_keywords or [],
    )


def test_reviewable_clause_keeps_short_english_obligations() -> None:
    assert ReviewService._is_reviewable_clause(_make_classified_clause("Data shall be encrypted."))
    assert ReviewService._is_reviewable_clause(_make_classified_clause("The processor must notify breaches."))
    assert ReviewService._is_reviewable_clause(_make_classified_clause("Users may withdraw consent."))


def test_reviewable_clause_filters_short_structural_noise() -> None:
    for text in ["1.2", "Article 1", "Table of Contents", "2024/05/01", "www.example.com"]:
        assert not ReviewService._is_reviewable_clause(_make_classified_clause(text))


def test_reviewable_clause_keeps_keyword_clause_and_skips_short_other() -> None:
    assert not ReviewService._is_reviewable_clause(_make_classified_clause("This agreement starts today."))
    assert ReviewService._is_reviewable_clause(
        _make_classified_clause(
            "Encryption required.",
            clause_type=ClauseType.SECURITY_MEASURES,
            matched_keywords=["encryption"],
        )
    )


def test_review_input_manifest_endpoint_returns_controlled_view(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, app):
        token, user_id = _register(client)
        container = app.state.container
        review_service = container.review_service

        review_service.task_dispatcher.dispatch = lambda func, *args, **kwargs: None
        review_service.reviewer.review = (
            lambda clause, use_llm=True, document_type="other", scenario_context=None: []
        )

        sample = container.settings.upload_dir / "sample_manifest_contract.md"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_text("# 数据处理协议\n第一条 处理目的\n", encoding="utf-8")

        accepted = client.post(
            "/api/v1/review/generate_async",
            headers={"Authorization": f"Bearer {token}"},
            json={"uploaded_files": [str(sample)]},
        )
        assert accepted.status_code == 200
        task_id = accepted.json()["task_id"]

        manifest = client.get(
            f"/api/v1/review/tasks/{task_id}/input-manifest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert manifest.status_code == 200
        payload = manifest.json()
        assert payload["module_key"] == "review"
        assert payload["task_id"] == task_id
        assert payload["integrity"]["manifest_hash"]

        entries = payload["entries"]
        assert entries, "input manifest should record the submitted file"
        file_entry = entries[0]
        assert file_entry["source_kind"] == "uploaded"
        assert file_entry["consumed_by_service"] is True
        assert file_entry["sha256"]
        # storage_uri must never leak through the public view
        assert "storage_uri" not in file_entry
        assert file_entry["public_locator"]


def test_review_input_manifest_denies_other_user(tmp_path: Path) -> None:
    with _make_client(tmp_path) as (client, app):
        token_a, _ = _register(client)

        sample = app.state.container.settings.upload_dir / "manifest_owner.md"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_text("# 合同\n", encoding="utf-8")

        accepted = client.post(
            "/api/v1/review/generate_async",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"uploaded_files": [str(sample)]},
        )
        assert accepted.status_code == 200
        task_id = accepted.json()["task_id"]

        # register a second user; they must not read user A's manifest
        register = client.post(
            "/api/v1/auth/register",
            json={
                "username": "review_manifest_other",
                "email": "review_manifest_other@example.com",
                "password": "review-pass-123",
            },
        )
        assert register.status_code == 200
        token_b = register.json()["access_token"]

        forbidden = client.get(
            f"/api/v1/review/tasks/{task_id}/input-manifest",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert forbidden.status_code == 404


def test_review_schema_first_registers_markdown_artifact(tmp_path: Path) -> None:
    import hashlib

    storage_dir = tmp_path / "storage"
    db_path = tmp_path / "review_md_artifact_test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}",
        storage_dir=storage_dir,
        task_mode="threaded",
        schema_first_document_review_enabled=True,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        token, user_id = _register(client)
        container = app.state.container
        review_service = container.review_service
        # The schema-first flag is read from the module-global settings cache in
        # ReviewService.__init__; force it on for this T04 artifact test.
        review_service.schema_first_enabled = True

        scheduled: dict[str, object] = {}

        def capture_dispatch(func, *args, **kwargs):
            scheduled["func"] = func
            scheduled["args"] = args
            scheduled["kwargs"] = kwargs
            return None

        review_service.task_dispatcher.dispatch = capture_dispatch
        review_service.reviewer.review = (
            lambda clause, use_llm=True, document_type="other", scenario_context=None: []
        )

        sample = container.settings.upload_dir / "sample_md_artifact.md"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_text("# 数据处理协议\n第一条 处理目的\n", encoding="utf-8")

        accepted = client.post(
            "/api/v1/review/generate_async",
            headers={"Authorization": f"Bearer {token}"},
            json={"uploaded_files": [str(sample)]},
        )
        assert accepted.status_code == 200
        task_id = accepted.json()["task_id"]
        assert scheduled["args"] == (task_id, user_id)
        scheduled["func"](*scheduled["args"], **scheduled["kwargs"])

        with container.session_factory() as db:
            artifact = review_service.report_service.get_owner_artifact(
                db, user_id, "review", task_id, "markdown"
            )
        assert artifact is not None
        assert artifact.file_path.endswith("review_report.md")
        assert Path(artifact.file_path).exists()

        preview = artifact.preview
        assert preview["ir_sha256"]
        assert preview["render_sha256"]
        assert preview["finding_ids"] == []
        assert len(preview["section_ids"]) == 10
        assert preview["citation_ids"] == []

        on_disk = Path(artifact.file_path).read_text(encoding="utf-8")
        assert hashlib.sha256(on_disk.encode("utf-8")).hexdigest() == preview["render_sha256"]

        # T05 — the canonical IR is registered and exposed as report_ir by the
        # controlled artifact preview API.
        with container.session_factory() as db:
            ir_artifact = review_service.report_service.get_owner_artifact(
                db, user_id, "review", task_id, "document_ir_json"
            )
        assert ir_artifact is not None
        assert ir_artifact.file_path.endswith("document_ir.json")
        assert Path(ir_artifact.file_path).exists()

        preview_resp = client.get(
            "/api/v1/artifacts/preview",
            params={"path": ir_artifact.file_path},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert preview_resp.status_code == 200
        payload = preview_resp.json()
        assert payload["render_mode"] == "report_ir"
        assert payload["kind"] == "document_ir_json"
        assert payload["content"] == ""
        assert payload["report_ir"]["report_type"] == "review"
        assert len(payload["report_ir"]["sections"]) == 10

        # T06 — the DOCX report is rendered from the canonical IR (native OOXML),
        # not the legacy string sections writer. Its preview records the IR hash.
        from docx import Document as _DocxDocument

        with container.session_factory() as db:
            docx_artifact = review_service.report_service.get_owner_artifact(
                db, user_id, "review", task_id, "docx"
            )
        assert docx_artifact is not None
        assert docx_artifact.file_path.endswith("review_report.docx")
        assert Path(docx_artifact.file_path).exists()
        assert docx_artifact.preview["ir_sha256"] == ir_artifact.preview["ir_sha256"]

        doc = _DocxDocument(docx_artifact.file_path)
        heading_texts = [
            p.text for p in doc.paragraphs
            if p.style.name.startswith("Heading") or p.style.name == "Title"
        ]
        assert any("执行摘要" in t for t in heading_texts)
        assert any("逐条问题" in t for t in heading_texts)

        # T07 — the PDF report is rendered from the canonical IR (fixed-layout
        # renderer), not the legacy Markdown-line writer. preview records the IR
        # hash. The CJK font stays BLOCKED_BY_FONT (STSong-Light emb=no) until a
        # licensed asset is tracked, so only magic bytes + extractability are
        # asserted here — not font embedding.
        from pypdf import PdfReader

        with container.session_factory() as db:
            pdf_artifact = review_service.report_service.get_owner_artifact(
                db, user_id, "review", task_id, "pdf"
            )
        assert pdf_artifact is not None
        assert pdf_artifact.file_path.endswith("review_report.pdf")
        assert Path(pdf_artifact.file_path).exists()
        assert pdf_artifact.preview["ir_sha256"] == ir_artifact.preview["ir_sha256"]

        pdf_bytes = Path(pdf_artifact.file_path).read_bytes()
        assert pdf_bytes.startswith(b"%PDF")
        pdf_text = "\n".join(
            page.extract_text() or "" for page in PdfReader(pdf_artifact.file_path).pages
        )
        assert "执行摘要" in pdf_text
