import json

from backend.common.trace.events import RunEvent


def test_run_event_serialize():
    event = RunEvent(
        task_id="test-task-1",
        seq=1,
        event_type="tool_start",
        summary="开始法规检索",
        detail={"tool": "CPRALegalRetriever", "query": "CPRA §1798.100"},
    )
    data = event.model_dump()
    assert data["event_type"] == "tool_start"
    assert data["summary"] == "开始法规检索"
    assert data["detail"]["tool"] == "CPRALegalRetriever"


def test_run_event_deserialize():
    raw = '{"event_type":"thought","summary":"路径判断完成","task_id":"t1","seq":5}'
    event = RunEvent.model_validate_json(raw)
    assert event.event_type == "thought"
    assert event.summary == "路径判断完成"


def test_run_event_json_serializable():
    event = RunEvent(task_id="t2", seq=1, event_type="status", summary="开始执行")
    text = event.model_dump_json()
    parsed = json.loads(text)
    assert parsed["event_type"] == "status"


def test_all_event_types():
    valid_types = {
        "status",
        "thought",
        "tool_start",
        "tool_result",
        "intermediate",
        "warning",
        "final",
        "final_brief",
    }
    for et in valid_types:
        event = RunEvent(task_id="t", seq=0, event_type=et, summary=et)
        assert event.event_type == et
