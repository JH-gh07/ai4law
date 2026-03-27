from __future__ import annotations

from typing import Any

import httpx

from backend.core.settings import Settings


class DeliLegalService:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.delilegal_base_url.rstrip("/")
        self.app_id = settings.delilegal_app_id
        self.secret = settings.delilegal_secret

    @property
    def enabled(self) -> bool:
        return bool(self.app_id and self.secret)

    def search_cases(self, query: str, size: int = 3) -> list[dict[str, Any]]:
        if not self.enabled or not query.strip():
            return []

        payload = {
            "input": query,
            "pageNum": 1,
            "pageSize": size,
        }
        headers = {
            "appid": self.app_id,
            "secret": self.secret,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.base_url}/api/qa/v3/search/queryListCase",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        candidates = self._extract_candidate_list(data)
        normalized: list[dict[str, Any]] = []
        for item in candidates[:size]:
            normalized.append(
                {
                    "title": item.get("title") or item.get("caseTitle") or item.get("name") or "未命名案例",
                    "source": item.get("source") or item.get("court") or "得理法搜",
                    "summary": item.get("summary") or item.get("snippet") or item.get("content") or "",
                }
            )
        return normalized

    def _extract_candidate_list(self, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []

        for key in ("data", "result", "records", "list", "rows"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                for nested_key in ("list", "records", "rows", "items"):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, list):
                        return [item for item in nested_value if isinstance(item, dict)]
        return []
