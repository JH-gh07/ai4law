from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app import create_app
from backend.core.settings import Settings
from backend.services.task_access import claim_task_access, require_task_access


def _app(tmp_path: Path):
    return create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'task_access.db'}",
            storage_dir=tmp_path / "storage",
        )
    )


def test_claimed_task_access_persists_for_owner(tmp_path: Path) -> None:
    app = _app(tmp_path)
    from backend.core.db import init_db

    init_db(app.state.container.engine)
    session = app.state.container.session_factory()
    try:
        claim_task_access(
            session,
            task_id="task-owned",
            user_id="user-owner",
            module="assessment",
        )

        require_task_access(session, task_id="task-owned", user_id="user-owner")
    finally:
        session.close()


def test_claimed_task_access_hides_task_from_other_user(tmp_path: Path) -> None:
    app = _app(tmp_path)
    from backend.core.db import init_db

    init_db(app.state.container.engine)
    session = app.state.container.session_factory()
    try:
        claim_task_access(
            session,
            task_id="task-private",
            user_id="user-owner",
            module="assessment",
        )

        with pytest.raises(HTTPException) as exc_info:
            require_task_access(session, task_id="task-private", user_id="user-other")
    finally:
        session.close()

    assert exc_info.value.status_code == 404


def test_task_ownership_cannot_be_reassigned_to_another_user(tmp_path: Path) -> None:
    app = _app(tmp_path)
    from backend.core.db import init_db

    init_db(app.state.container.engine)
    session = app.state.container.session_factory()
    try:
        claim_task_access(
            session,
            task_id="task-stable-owner",
            user_id="user-owner",
            module="assessment",
        )

        with pytest.raises(ValueError, match="conflicts"):
            claim_task_access(
                session,
                task_id="task-stable-owner",
                user_id="user-other",
                module="assessment",
            )
    finally:
        session.close()


def test_task_access_fails_closed_when_task_has_no_owner_record(tmp_path: Path) -> None:
    app = _app(tmp_path)
    from backend.core.db import init_db

    init_db(app.state.container.engine)
    session = app.state.container.session_factory()
    try:
        with pytest.raises(HTTPException) as exc_info:
            require_task_access(session, task_id="task-unclaimed", user_id="user-any")
    finally:
        session.close()

    assert exc_info.value.status_code == 404
