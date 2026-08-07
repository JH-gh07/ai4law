from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 单一数据源：Citation ID 格式与 {{CIT-xxx}} 标记语法（共性下沉原则）。
#
# 所有需要解析标记或验证 ID 的模块从此处导入，禁止在其他模块中重复定义。
# ---------------------------------------------------------------------------

# 匹配 id_generator.generate_citation_id() 生成的合法 citation ID。
#
# 格式：CIT-{jurisdiction}-{abbr}-{ART<n>|GEN}-P{nn}
#
# abbr 段允许：
#   - 下划线（新格式，id_generator 已对连字符做 sanitize）
#   - 连字符（旧格式，向后兼容存量数据）
#
# ART 段允许 ASCII 字母、数字、下划线，及中文汉字（normalize_article_no 可能返回汉字）。
CITATION_ID_RE = re.compile(
    r"CIT-[A-Z]{2}-[A-Z0-9_-]+-(?:ART[A-Za-z0-9_一-鿿]+|GEN)-P\d+"
)

# 匹配 LLM 输出中的 {{CIT-xxx}} 标记。
CIT_MARKER_RE = re.compile(r"\{\{(" + CITATION_ID_RE.pattern + r")\}\}")


def is_valid_citation_id(cid: str) -> bool:
    """当且仅当 cid 符合规范的 citation ID 格式时返回 True。"""
    return bool(CITATION_ID_RE.fullmatch(cid))
