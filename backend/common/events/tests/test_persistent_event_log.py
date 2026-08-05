from backend.common.events.manager import SSEManager
from backend.common.trace.events import RunEvent
from backend.core.db import build_engine, build_session_factory, init_db


def _session_factory(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'events.db'}")
    init_db(engine)
    return build_session_factory(engine)


def test_events_survive_manager_recreation(tmp_path) -> None:
    session_factory = _session_factory(tmp_path)
    first_manager = SSEManager(session_factory=session_factory)
    first_manager.publish(
        "task-1",
        RunEvent(task_id="task-1", seq=0, event_type="status", summary="created"),
    )

    recreated_manager = SSEManager(session_factory=session_factory)

    events = recreated_manager.get_events_since("task-1", since=-1)
    assert [(event.seq, event.summary) for event in events] == [(0, "created")]


def test_database_assigns_monotonic_sequence_across_manager_instances(tmp_path) -> None:
    session_factory = _session_factory(tmp_path)
    first_manager = SSEManager(session_factory=session_factory)
    second_manager = SSEManager(session_factory=session_factory)

    first_manager.publish(
        "task-1",
        RunEvent(task_id="task-1", seq=0, event_type="status", summary="created"),
    )
    second_manager.publish(
        "task-1",
        RunEvent(task_id="task-1", seq=0, event_type="status", summary="running"),
    )

    events = second_manager.get_events_since("task-1", since=-1)
    assert [(event.seq, event.summary) for event in events] == [
        (0, "created"),
        (1, "running"),
    ]


def test_republishing_same_event_id_is_idempotent(tmp_path) -> None:
    session_factory = _session_factory(tmp_path)
    manager = SSEManager(session_factory=session_factory)
    event = RunEvent(
        event_id="stable-event-id",
        task_id="task-1",
        seq=0,
        event_type="status",
        summary="created",
    )

    manager.publish("task-1", event)
    manager.publish("task-1", event)

    events = manager.get_events_since("task-1", since=-1)
    assert [persisted.event_id for persisted in events] == ["stable-event-id"]


def test_stream_token_is_shared_across_manager_instances(tmp_path) -> None:
    session_factory = _session_factory(tmp_path)
    issuer = SSEManager(session_factory=session_factory)
    verifier = SSEManager(session_factory=session_factory)

    token = issuer.issue_stream_token("task-1", "user-1")

    assert verifier.verify_stream_token(token) == ("task-1", "user-1")
    assert verifier.stream_token_expires_at(token) is not None
