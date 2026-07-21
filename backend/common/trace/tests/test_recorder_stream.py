import tempfile
from pathlib import Path
from backend.common.trace.recorder import TraceRecorder


def test_recorder_writes_file_and_pushes_event():
    received: list = []
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TraceRecorder(trace_dir=Path(tmpdir), task_id="test-task")
        recorder.subscribe(lambda e: received.append(e))
        recorder.record("tool_start", {"summary": "测试工具", "detail": {"key": "val"}})
        recorder.record("tool_result", {"summary": "测试结果"})

        # 验证文件也已写入（在 tmpdir 被清理前检查）
        trace_files = list(Path(tmpdir).glob("*.json"))
        assert len(trace_files) >= 2

    assert len(received) == 2
    assert received[0].event_type == "tool_start"
    assert received[0].task_id == "test-task"
    assert received[0].summary == "测试工具"
    assert received[0].detail == {"key": "val", "raw_name": "tool_start"}
    assert received[1].event_type == "tool_result"
    assert received[1].seq == 2


def test_subscriber_exception_does_not_block_writing():
    received: list = []
    def bad_subscriber(event):
        if event.event_type == "tool_result":
            raise RuntimeError("boom")
        received.append(event)

    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TraceRecorder(trace_dir=Path(tmpdir), task_id="t")
        recorder.subscribe(bad_subscriber)
        recorder.record("tool_start", {"summary": "s1"})
        recorder.record("tool_result", {"summary": "s2"})
        recorder.record("tool_start", {"summary": "s3"})

    # bad_subscriber 在 tool_result 时抛异常，但后续事件仍正常
    assert len(received) == 2
    assert received[0].event_type == "tool_start"
    assert received[1].event_type == "tool_start"


def test_subscribe_is_idempotent_for_the_same_callback():
    received: list = []

    def receive(event):
        received.append(event)

    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TraceRecorder(trace_dir=Path(tmpdir), task_id="test-task")
        recorder.subscribe(receive)
        recorder.subscribe(receive)
        recorder.record("status", {"summary": "started"})

    assert len(received) == 1


def test_legacy_name_mapping():
    received: list = []
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TraceRecorder(trace_dir=Path(tmpdir), task_id="t")
        recorder.subscribe(lambda e: received.append(e))
        recorder.record("diagnosis", {"summary": "路径判断"})
        recorder.record("profile_extracted", {"summary": "提取完成"})
        recorder.record("path_validation", {"summary": "路径警告"})

    assert received[0].event_type == "thought"
    assert received[1].event_type == "intermediate"
    assert received[2].event_type == "warning"
    assert received[0].detail == {"raw_name": "diagnosis"}
    assert received[1].detail == {"raw_name": "profile_extracted"}
