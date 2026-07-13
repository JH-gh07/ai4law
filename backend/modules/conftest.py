from __future__ import annotations

import pytest

from backend.core.dependencies import get_current_user
from backend.main import app
from backend.schemas.auth import AuthUser


@pytest.fixture
def authenticated_user() -> AuthUser:
    user = AuthUser(
        id="test-user",
        username="test-user",
        email="test-user@example.com",
        company_name="DataComplyFlow Test",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield user
    finally:
        app.dependency_overrides.pop(get_current_user, None)
