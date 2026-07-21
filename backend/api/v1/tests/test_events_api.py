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


def test_publish_normalizes_non_monotonic_source_sequences():
    """状态事件和 trace 各自计数时，轮询游标仍不能漏掉后续事件。"""
    sm = get_ssemanager()

    sm.publish("task-mixed", RunEvent(task_id="task-mixed", seq=0, event_type="status", summary="已创建"))
    sm.publish("task-mixed", RunEvent(task_id="task-mixed", seq=0, event_type="status", summary="执行中"))
    sm.publish("task-mixed", RunEvent(task_id="task-mixed", seq=1, event_type="thought", summary="业务追踪"))

    events = sm.get_events_since("task-mixed", since=-1)
    assert [event.seq for event in events] == [0, 1, 2]
    assert [event.summary for event in sm.get_events_since("task-mixed", since=1)] == ["业务追踪"]


def test_polling_accepts_minus_one_as_the_initial_cursor():
    client = TestClient(app)
    sm = get_ssemanager()
    sm.publish("task-initial", RunEvent(task_id="task-initial", seq=0, event_type="status", summary="已创建"))

    response = client.get("/api/v1/events/task/task-initial/events?since=-1")

    assert response.status_code == 200
    assert [event["seq"] for event in response.json()["events"]] == [0]
