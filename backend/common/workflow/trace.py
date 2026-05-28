from typing import Any

from pydantic import BaseModel


def dump_model_list(items: list[BaseModel]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in items]
