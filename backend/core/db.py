from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, future=True)


def build_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine) -> None:
    from backend.models import auth, diagnosis, event, report, review, task, workspace  # noqa: F401
    from backend.models import async_task  # noqa: F401
    import backend.common.knowledge.models  # noqa: F401
    import backend.common.citation.audit  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_legacy_columns(engine)


def _ensure_legacy_columns(engine) -> None:
    # Lightweight sqlite-compatible migration for existing local DBs.
    required = {
        "diagnosis_sessions": {"user_id": "TEXT DEFAULT ''"},
        "report_artifacts": {"user_id": "TEXT DEFAULT ''"},
        "review_tasks": {"user_id": "TEXT DEFAULT ''", "request_context_json": "TEXT DEFAULT '{}'"},
        "uploaded_files": {"user_id": "TEXT DEFAULT ''"},
        "run_events": {"correlation_id": "TEXT"},
        "async_tasks": {
            "attempts": "INTEGER DEFAULT 0",
            "max_attempts": "INTEGER DEFAULT 1",
            "result_json": "TEXT DEFAULT ''",
            "provider_snapshot_json": "TEXT DEFAULT ''",
            "manifest_path": "TEXT DEFAULT ''",
        },
    }
    with engine.begin() as conn:
        for table_name, columns in required.items():
            info = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
            existing = {row[1] for row in info}
            for col, ddl in columns.items():
                if col in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col} {ddl}"))
