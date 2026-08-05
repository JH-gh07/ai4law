from sqlalchemy import Float, JSON, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class RunEventModel(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        UniqueConstraint("task_id", "seq", name="uq_run_events_task_seq"),
        Index("ix_run_events_task_seq", "task_id", "seq"),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="audit")


class StreamTokenModel(Base):
    __tablename__ = "event_stream_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    expires_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
