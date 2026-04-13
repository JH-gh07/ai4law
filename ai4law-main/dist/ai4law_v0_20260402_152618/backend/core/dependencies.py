from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.core.container import AppContainer


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_db(container: AppContainer = Depends(get_container)) -> Generator[Session, None, None]:
    db = container.session_factory()
    try:
        yield db
    finally:
        db.close()
