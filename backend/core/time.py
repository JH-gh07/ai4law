from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return an explicit timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    """Return UTC without tzinfo for existing naive SQLAlchemy columns."""
    return utc_now().replace(tzinfo=None)


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp suitable for JSON traces."""
    return utc_now().isoformat()
