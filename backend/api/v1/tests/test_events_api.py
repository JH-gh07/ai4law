"""Integration tests for SSE polling endpoint."""

import json
import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.common.events.manager import get_ssemanager
from backend.common.events.manager import SSEManager
from backend.common.trace.events import RunEvent
from backend.core.settings import Settings
from backend.core.db import build_engine, build_session_factory, init_db
from backend.services.task_access import claim_task_access


@pytest.fixture(autouse=True)
def reset_ssemanager():
    """每个测试前重置全局 SSEManager。"""
    import backend.common.events.manager as mod

    mod._ssemanager = None


def _register(client: TestClient, username: str, email: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "pass-12345678"},
    )
    assert response.status_code == 200
    payload = response.json()
    return payload["access_token"], payload["user"]["id"]


@pytest.fixture
def owned_task_client(tmp_path, monkeypatch):
    from backend.api.v1.endpoints import events as events_endpoint

    outputs_dir = tmp_path / "outputs"
    monkeypatch.setattr(events_endpoint, "OUTPUTS_DIR", outputs_dir)
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'events_access.db'}",
            storage_dir=tmp_path / "storage",
        )
    )
    with TestClient(app) as client:
        owner_token, owner_id = _register(client, "event-owner", "event-owner@test.local")
        other_token, _ = _register(client, "event-other", "event-other@test.local")
        session = app.state.container.session_factory()
        try:
            claim_task_access(
                session,
                task_id="task-1",
                user_id=owner_id,
                module="assessment",
            )
        finally:
            session.close()
        manifest_path = outputs_dir / "assessment" / "task-1" / "run_manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "run_id": "task-1",
                    "module": "assessment",
                    "status": "COMPLETED",
                    "observability": {"tokens": {"total_tokens": 12}},
                }
            ),
            encoding="utf-8",
        )
        yield client, owner_token, other_token


def test_polling_returns_events_since_for_owner(owned_task_client):
    client, owner_token, _ = owned_task_client
    sm = get_ssemanager()

    sm.publish("task-1", RunEvent(task_id="task-1", seq=1, event_type="status", summary="开始"))
    sm.publish("task-1", RunEvent(task_id="task-1", seq=2, event_type="thought", summary="路径判断"))

    resp = client.get(
        "/api/v1/events/task/task-1/events?since=0",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 2
    assert data["events"][0]["event_type"] == "status"
    assert data["latest_seq"] == 2

    resp2 = client.get(
        "/api/v1/events/task/task-1/events?since=1",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    data2 = resp2.json()
    assert len(data2["events"]) == 1
    assert data2["events"][0]["seq"] == 2


def test_polling_requires_authentication(owned_task_client):
    client, _, _ = owned_task_client
    response = client.get("/api/v1/events/task/task-1/events?since=0")

    assert response.status_code == 401


def test_polling_hides_task_from_other_user(owned_task_client):
    client, _, other_token = owned_task_client
    response = client.get(
        "/api/v1/events/task/task-1/events?since=0",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_polling_hides_nonexistent_task_from_authenticated_user(owned_task_client):
    client, owner_token, _ = owned_task_client
    response = client.get(
        "/api/v1/events/task/nonexistent/events?since=0",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 404


def test_publish_normalizes_non_monotonic_source_sequences():
    """状态事件和 trace 各自计数时，轮询游标仍不能漏掉后续事件。"""
    sm = get_ssemanager()

    sm.publish("task-mixed", RunEvent(task_id="task-mixed", seq=0, event_type="status", summary="已创建"))
    sm.publish("task-mixed", RunEvent(task_id="task-mixed", seq=0, event_type="status", summary="执行中"))
    sm.publish("task-mixed", RunEvent(task_id="task-mixed", seq=1, event_type="thought", summary="业务追踪"))

    events = sm.get_events_since("task-mixed", since=-1)
    assert [event.seq for event in events] == [0, 1, 2]
    assert [event.summary for event in sm.get_events_since("task-mixed", since=1)] == ["业务追踪"]


def test_polling_accepts_minus_one_as_the_initial_cursor(owned_task_client):
    client, owner_token, _ = owned_task_client
    sm = get_ssemanager()
    # This test exercises cursor semantics on the already-owned task.
    sm.publish("task-1", RunEvent(task_id="task-1", seq=0, event_type="status", summary="已创建"))

    response = client.get(
        "/api/v1/events/task/task-1/events?since=-1",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    assert [event["seq"] for event in response.json()["events"]] == [0]


def test_polling_paginates_persistent_events(owned_task_client):
    client, owner_token, _ = owned_task_client
    sm = get_ssemanager()
    for index in range(3):
        sm.publish(
            "task-1",
            RunEvent(
                task_id="task-1",
                seq=index,
                event_type="status",
                summary=f"event-{index}",
            ),
        )

    response = client.get(
        "/api/v1/events/task/task-1/events?since=-1&limit=2",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    assert [event["summary"] for event in response.json()["events"]] == [
        "event-0",
        "event-1",
    ]
    assert response.json()["has_more"] is True


def test_manifest_returns_persisted_accounting_for_owner(owned_task_client):
    client, owner_token, _ = owned_task_client

    response = client.get(
        "/api/v1/events/task/task-1/manifest",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == "task-1"
    assert response.json()["observability"]["tokens"]["total_tokens"] == 12


def test_manifest_is_hidden_from_other_user(owned_task_client):
    client, _, other_token = owned_task_client

    response = client.get(
        "/api/v1/events/task/task-1/manifest",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_stream_token_can_be_reused_for_eventsource_reconnect(owned_task_client):
    client, owner_token, _ = owned_task_client

    response = client.post(
        "/api/v1/events/task/task-1/token",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    token = payload["stream_token"]
    manager = get_ssemanager()
    first_verification = manager.verify_stream_token(token)
    second_verification = manager.verify_stream_token(token)
    assert first_verification is not None
    assert first_verification[0] == "task-1"
    assert second_verification == first_verification
    expires_at = datetime.fromisoformat(payload["expires_at"])
    assert (expires_at - datetime.now(timezone.utc)).total_seconds() > 240


def test_sse_catches_up_events_written_by_another_manager(tmp_path):
    from backend.api.v1.endpoints.events import _stream_events
    import backend.common.events.manager as manager_module

    engine = build_engine(f"sqlite:///{tmp_path / 'cross-worker.db'}")
    init_db(engine)
    session_factory = build_session_factory(engine)
    stream_manager = SSEManager(session_factory=session_factory)
    writer_manager = SSEManager(session_factory=session_factory)
    manager_module._ssemanager = stream_manager

    class ConnectedRequest:
        async def is_disconnected(self) -> bool:
            return False

    async def receive_cross_worker_event() -> str:
        generator = _stream_events("task-1", ConnectedRequest(), since=-1)
        next_frame = asyncio.create_task(anext(generator))
        await asyncio.sleep(0.05)
        writer_manager.publish(
            "task-1",
            RunEvent(task_id="task-1", seq=0, event_type="status", summary="cross-worker"),
        )
        try:
            return await asyncio.wait_for(next_frame, timeout=2)
        finally:
            await generator.aclose()

    frame = asyncio.run(receive_cross_worker_event())
    assert "cross-worker" in frame
