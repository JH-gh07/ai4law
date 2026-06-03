from typing import Any

from pydantic import BaseModel


def dump_model_list(items: list[Any]) -> list[dict[str, Any]]:
    return [item.model_dump() if hasattr(item, "model_dump") else item for item in items]
