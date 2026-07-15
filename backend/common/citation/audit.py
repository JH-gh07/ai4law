"""Citation audit log — tracks every citation lifecycle event for traceability."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session

from backend.core.db import Base
from backend.core.time import utc_now_naive

logger = logging.getLogger(__name__)


class CitationAction(str, Enum):
    created = "created"
    linked = "linked"
    updated = "updated"
    published = "published"
    deprecated = "deprecated"


class CitationAuditLog(Base):
    __tablename__ = "citation_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    citation_id: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(32), default="created")
    report_id: Mapped[str] = mapped_column(String(128), default="")
    task_id: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


def log_citation_event(
    citation_id: str,
    action: CitationAction,
    *,
    task_id: str = "",
    report_id: str = "",
    detail: str = "",
    db: Optional[Session] = None,
) -> None:
    """Record a citation lifecycle event.

    If db is not provided, tries to create a session from settings.
    Fails silently on DB errors (fire-and-forget for audit trails).
    """
    entry = CitationAuditLog(
        citation_id=citation_id,
        action=action.value if isinstance(action, CitationAction) else action,
        task_id=task_id,
        report_id=report_id,
        detail=detail,
    )
    if db is not None:
        try:
            db.add(entry)
            db.flush()
        except Exception:
            logger.warning("Failed to write citation audit log", exc_info=True)
        return

    try:
        from backend.core.db import build_engine, build_session_factory
        from backend.core.settings import get_settings

        settings = get_settings()
        engine = build_engine(settings.database_url)
        factory = build_session_factory(engine)
        session = factory()
        try:
            session.add(entry)
            session.commit()
        except Exception:
            session.rollback()
            logger.warning("Failed to write citation audit log", exc_info=True)
        finally:
            session.close()
    except Exception:
        logger.warning("Failed to create DB session for citation audit", exc_info=True)


def log_citations_created(
    citation_ids: list[str],
    task_id: str = "",
    report_id: str = "",
    db: Optional[Session] = None,
) -> None:
    """Bulk-log that citations were created."""
    for cid in citation_ids:
        log_citation_event(
            cid, CitationAction.created, task_id=task_id, report_id=report_id, db=db
        )


def get_citation_audit_log(
    citation_id: str,
    db: Session,
    limit: int = 20,
) -> list[CitationAuditLog]:
    """Retrieve audit log entries for a citation."""
    return (
        db.query(CitationAuditLog)
        .filter(CitationAuditLog.citation_id == citation_id)
        .order_by(CitationAuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_task_audit_log(
    task_id: str,
    db: Session,
    limit: int = 50,
) -> list[CitationAuditLog]:
    """Retrieve all citation audit entries for a task."""
    return (
        db.query(CitationAuditLog)
        .filter(CitationAuditLog.task_id == task_id)
        .order_by(CitationAuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
