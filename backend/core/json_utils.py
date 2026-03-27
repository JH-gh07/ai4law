import json
from typing import Any


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def loads(raw: str | None, default: Any):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default
