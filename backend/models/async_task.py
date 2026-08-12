"""Async task persistence model.

The in-memory task manager keeps running-task state in-process, which is lost
on service restart.  This model records the *current* status of every async
task so that ``/me/tasks`` and ``/me/workspace-recovery`` can reconstruct a
task's terminal state after a restart instead of reporting "Task not found".
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class AsyncTaskModel(Base):
    __tablename__ = "async_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Best-effort denormalization.  Authoritative ownership stays in
    # TaskOwnershipModel; this column is filled when known but recovery joins
    # against task_ownerships to authoritatively filter by user.
    user_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    module: Mapped[str] = mapped_column(String(64), index=True, default="")
    status: Mapped[str] = mapped_column(String(32), default="CREATED")
    error: Mapped[str] = mapped_column(Text, default="")
    result_path: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
