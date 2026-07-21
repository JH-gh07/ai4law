from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app import create_app
from backend.core.settings import Settings
from backend.domains.cn.pipia import router as pipia_router
from backend.domains.cn.security_assessment import router as assessment_router
from backend.domains.eu.bcr_review import router as bcr_router
from backend.domains.eu.dpia import router as dpia_router
from backend.domains.eu.scc_review import router as scc_router
from backend.domains.eu.tia import router as tia_router
from backend.domains.us.cpra import router as cpra_router
from backend.domains.us.eo14117 import router as eo14117_router
from backend.domains.us.eo14117_flow_review import router as flow_router
from backend.schemas.auth import AuthUser
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


@pytest.mark.parametrize(
    ("router_module", "submit_function", "module"),
    [
        (assessment_router, assessment_router.generate_assessment_async, "assessment"),
        (pipia_router, pipia_router.generate_pipia_async, "pipia"),
        (bcr_router, bcr_router.generate_bcr_async, "bcr"),
        (dpia_router, dpia_router.generate_dpia_async, "dpia"),
        (scc_router, scc_router.generate_eu_scc_async, "eu_scc"),
        (tia_router, tia_router.generate_tia_async, "tia"),
        (cpra_router, cpra_router.generate_cpra_async, "cpra"),
        (eo14117_router, eo14117_router.generate_us_14117_async, "us_14117"),
        (flow_router, flow_router.generate_cn_flow_async, "cn_flow"),
    ],
)
def test_all_async_report_routes_persist_task_ownership(
    tmp_path: Path,
    monkeypatch,
    router_module,
    submit_function,
    module: str,
) -> None:
    app = _app(tmp_path)
    from backend.core.db import init_db

    init_db(app.state.container.engine)
    task_id = f"task-{module}"
    monkeypatch.setattr(
        router_module,
        "service",
        SimpleNamespace(submit_async=lambda _payload: SimpleNamespace(task_id=task_id)),
    )
    user = AuthUser(id="route-owner", username="owner", email="owner@test.local")
    session = app.state.container.session_factory()
    try:
        accepted = submit_function(payload=object(), db=session, current_user=user)

        assert accepted.task_id == task_id
        require_task_access(session, task_id=task_id, user_id=user.id)
    finally:
        session.close()


@pytest.mark.parametrize(
    ("router_module", "status_function", "retry_function", "module"),
    [
        (
            assessment_router,
            assessment_router.get_assessment_task,
            assessment_router.retry_assessment_task,
            "assessment",
        ),
        (pipia_router, pipia_router.get_pipia_task, pipia_router.retry_pipia_task, "pipia"),
        (bcr_router, bcr_router.get_bcr_task, bcr_router.retry_bcr_task, "bcr"),
        (dpia_router, dpia_router.get_dpia_task, dpia_router.retry_dpia_task, "dpia"),
        (scc_router, scc_router.get_eu_scc_task, scc_router.retry_eu_scc_task, "eu_scc"),
        (tia_router, tia_router.get_tia_task, tia_router.retry_tia_task, "tia"),
        (cpra_router, cpra_router.get_cpra_task, cpra_router.retry_cpra_task, "cpra"),
        (
            eo14117_router,
            eo14117_router.get_us_14117_task,
            eo14117_router.retry_us_14117_task,
            "us_14117",
        ),
        (flow_router, flow_router.get_cn_flow_task, flow_router.retry_cn_flow_task, "cn_flow"),
    ],
)
def test_all_async_report_task_routes_use_persisted_ownership(
    tmp_path: Path,
    monkeypatch,
    router_module,
    status_function,
    retry_function,
    module: str,
) -> None:
    app = _app(tmp_path)
    from backend.core.db import init_db

    init_db(app.state.container.engine)
    task_id = f"task-status-{module}"
    owner = AuthUser(id="status-owner", username="owner", email="owner@test.local")
    other = AuthUser(id="status-other", username="other", email="other@test.local")
    monkeypatch.setattr(
        router_module,
        "service",
        SimpleNamespace(
            get_async_status=lambda _task_id: SimpleNamespace(result=None),
            retry_async=lambda _task_id: SimpleNamespace(result=None),
        ),
    )
    getattr(router_module, "TASK_OWNERS", {}).clear()
    session = app.state.container.session_factory()
    try:
        claim_task_access(session, task_id=task_id, user_id=owner.id, module=module)

        status_function(
            task_id=task_id,
            db=session,
            current_user=owner,
            container=app.state.container,
        )
        with pytest.raises(HTTPException) as exc_info:
            status_function(
                task_id=task_id,
                db=session,
                current_user=other,
                container=app.state.container,
            )
        with pytest.raises(HTTPException) as retry_exc_info:
            retry_function(task_id=task_id, db=session, current_user=other)
    finally:
        session.close()

    assert exc_info.value.status_code == 404
    assert retry_exc_info.value.status_code == 404


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
