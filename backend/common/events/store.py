from __future__ import annotations

import hashlib
import time

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.common.trace.events import RunEvent
from backend.models.event import RunEventModel, StreamTokenModel


class EventLog:
    """Append-only persistent event log backed by the application database."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def append(self, task_id: str, event: RunEvent) -> RunEvent:
        for _attempt in range(5):
            with self._session_factory() as db:
                existing = db.get(RunEventModel, event.event_id)
                if existing is not None:
                    return self._to_event(existing)

                latest_seq = db.execute(
                    select(func.max(RunEventModel.seq)).where(
                        RunEventModel.task_id == task_id
                    )
                ).scalar_one()
                next_seq = max(event.seq, (latest_seq if latest_seq is not None else -1) + 1)
                row = RunEventModel(
                    event_id=event.event_id,
                    task_id=task_id,
                    seq=next_seq,
                    correlation_id=event.correlation_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    summary=event.summary,
                    detail=event.detail,
                    level=event.level,
                )
                db.add(row)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    continue
                db.refresh(row)
                return self._to_event(row)
        raise RuntimeError(f"Unable to allocate event sequence for task {task_id}")

    def list_since(self, task_id: str, since: int, limit: int | None = None) -> list[RunEvent]:
        statement = (
            select(RunEventModel)
            .where(RunEventModel.task_id == task_id, RunEventModel.seq > since)
            .order_by(RunEventModel.seq)
        )
        if limit is not None:
            statement = statement.limit(limit)
        with self._session_factory() as db:
            rows = db.execute(statement).scalars().all()
            return [self._to_event(row) for row in rows]

    def delete_task(self, task_id: str) -> None:
        with self._session_factory() as db:
            db.execute(delete(RunEventModel).where(RunEventModel.task_id == task_id))
            db.execute(delete(StreamTokenModel).where(StreamTokenModel.task_id == task_id))
            db.commit()

    def store_stream_token(
        self,
        token: str,
        task_id: str,
        user_id: str,
        expires_at: float,
    ) -> None:
        with self._session_factory() as db:
            db.execute(
                delete(StreamTokenModel).where(StreamTokenModel.expires_at < time.time())
            )
            db.add(
                StreamTokenModel(
                    token_hash=self._token_hash(token),
                    task_id=task_id,
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )
            db.commit()

    def get_stream_token(self, token: str) -> tuple[str, str, float] | None:
        now = time.time()
        with self._session_factory() as db:
            row = db.get(StreamTokenModel, self._token_hash(token))
            if row is None:
                return None
            if row.expires_at < now:
                db.delete(row)
                db.commit()
                return None
            return row.task_id, row.user_id, row.expires_at

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _to_event(row: RunEventModel) -> RunEvent:
        return RunEvent(
            event_id=row.event_id,
            task_id=row.task_id,
            seq=row.seq,
            correlation_id=row.correlation_id,
            event_type=row.event_type,
            timestamp=row.timestamp,
            summary=row.summary,
            detail=row.detail,
            level=row.level,
        )
