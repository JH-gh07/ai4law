from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.db import Base


class DiagnosisSessionModel(Base):
    __tablename__ = "diagnosis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(32), default="CREATED")
    answers_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
