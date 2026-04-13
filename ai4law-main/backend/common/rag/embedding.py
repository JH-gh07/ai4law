from __future__ import annotations

import math
import re
from collections import Counter


def normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    lowered = lowered.replace("\u3000", " ")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def tokenize_text(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    alpha_numeric = re.findall(r"[a-z0-9_+-]+", normalized)
    chinese_chars = [char for char in normalized if "\u4e00" <= char <= "\u9fff"]

    tokens: list[str] = []
    tokens.extend(alpha_numeric)
    tokens.extend(chinese_chars)

    if len(chinese_chars) >= 2:
        tokens.extend("".join(chinese_chars[idx : idx + 2]) for idx in range(len(chinese_chars) - 1))
    if len(chinese_chars) >= 3:
        tokens.extend("".join(chinese_chars[idx : idx + 3]) for idx in range(len(chinese_chars) - 2))

    return tokens


class HashingEmbedder:
    """Deterministic local embedder for offline vector retrieval."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = max(64, dimension)

    def embed(self, text: str) -> dict[int, float]:
        tokens = tokenize_text(text)
        if not tokens:
            return {}

        counts = Counter(tokens)
        vector: dict[int, float] = {}
        for token, count in counts.items():
            index = hash(token) % self.dimension
            vector[index] = vector.get(index, 0.0) + float(count)
        return self._l2_normalize(vector)

    @staticmethod
    def similarity(left: dict[int, float], right: dict[int, float]) -> float:
        if not left or not right:
            return 0.0
        shared = set(left) & set(right)
        return sum(left[idx] * right[idx] for idx in shared)

    @staticmethod
    def _l2_normalize(vector: dict[int, float]) -> dict[int, float]:
        norm = math.sqrt(sum(value * value for value in vector.values()))
        if norm <= 0:
            return {}
        return {index: value / norm for index, value in vector.items()}
