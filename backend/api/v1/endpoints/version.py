from fastapi import APIRouter

from backend.core.release_info import load_public_release_info


router = APIRouter()


@router.get("/version")
def get_version() -> dict[str, object]:
    return load_public_release_info()
