"""稳定 JSON canonicalization 与 hash。

约束（task082 §5.3）：
- 统一 UTF-8、排序 key、固定分隔符、无多余空白；
- hash 输入明确排除运行时 audit 字段（由调用方在传入前剥离）；
- 禁止使用文件修改时间作为版本真相，禁止只 hash 文件路径。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """把任意可 JSON 序列化对象规范化为稳定字符串。

    ``sort_keys=True`` + ``separators=(",", ":")`` 保证 key 顺序变化不影响结果。
    ``ensure_ascii=False`` 保留中文字面（UTF-8），hash 前统一 UTF-8 编码。
    ``allow_nan=False`` 拒绝 NaN/Infinity，避免不可复现的 JSON 表示。
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def stable_hash(value: Any, *, prefix: str = "") -> str:
    """计算稳定 SHA-256。

    ``value`` 若为字符串则直接使用（调用方须已 canonicalize），否则先
    :func:`canonical_json`。``prefix`` 用于区分 hash 域（如 "template:",
    "plan:", "input:"），避免不同对象偶然碰撞。
    """
    text = value if isinstance(value, str) else canonical_json(value)
    payload = f"{prefix}{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonicalize_payload(payload: Any) -> Any:
    """把 Python 对象做一次深度规范化（用于输入 hash 与模板 hash 输入）。

    返回新的、纯 JSON 类型（dict/list/str/int/float/bool/None）的对象，
    不保留 pydantic 模型或 tuple 等自定义类型。
    """
    return json.loads(canonical_json(payload))


__all__ = ["canonical_json", "canonicalize_payload", "stable_hash"]
