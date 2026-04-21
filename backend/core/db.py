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
    from backend.models import auth, diagnosis, report, review, workspace  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_legacy_columns(engine)


def _ensure_legacy_columns(engine) -> None:
    # Lightweight sqlite-compatible migration for existing local DBs.
    required = {
        "diagnosis_sessions": {"user_id": "TEXT DEFAULT ''"},
        "report_artifacts": {"user_id": "TEXT DEFAULT ''"},
        "review_tasks": {"user_id": "TEXT DEFAULT ''"},
        "uploaded_files": {"user_id": "TEXT DEFAULT ''"},
    }
    with engine.begin() as conn:
        for table_name, columns in required.items():
            info = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
            existing = {row[1] for row in info}
            for col, ddl in columns.items():
                if col in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col} {ddl}"))
