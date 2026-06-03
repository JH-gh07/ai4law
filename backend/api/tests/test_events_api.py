"""Integration tests for SSE polling endpoint."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.common.events.manager import get_ssemanager
from backend.common.trace.events import RunEvent
from backend.main import app


@pytest.fixture(autouse=True)
def reset_ssemanager():
    """每个测试前重置全局 SSEManager。"""
    import backend.common.events.manager as mod

    mod._ssemanager = None


def test_polling_returns_events_since():
    client = TestClient(app)
    sm = get_ssemanager()

    sm.publish("task-1", RunEvent(task_id="task-1", seq=1, event_type="status", summary="开始"))
    sm.publish("task-1", RunEvent(task_id="task-1", seq=2, event_type="thought", summary="路径判断"))

    resp = client.get("/api/v1/events/task/task-1/events?since=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 2
    assert data["events"][0]["event_type"] == "status"
    assert data["latest_seq"] == 2

    resp2 = client.get("/api/v1/events/task/task-1/events?since=1")
    data2 = resp2.json()
    assert len(data2["events"]) == 1
    assert data2["events"][0]["seq"] == 2


def test_polling_empty_when_no_events():
    client = TestClient(app)
    resp = client.get("/api/v1/events/task/nonexistent/events?since=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["latest_seq"] == 0
