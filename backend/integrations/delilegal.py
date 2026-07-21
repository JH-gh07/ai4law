from __future__ import annotations

import time
from typing import Any

import httpx

from backend.core.settings import Settings


class DeliLegalService:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.delilegal_base_url.rstrip("/")
        self.app_id = settings.delilegal_app_id
        self.secret = settings.delilegal_secret
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.app_id and self.secret)

    def probe(self) -> dict[str, Any]:
        """Run one minimal law search and return a stable health contract."""
        start = time.perf_counter()
        if not self.enabled:
            return {
                "ok": False,
                "latency_ms": 0,
                "result_count": 0,
                "error_code": "NOT_CONFIGURED",
                "error_category": "configuration",
                "error": "得理 API 未配置 App ID 或 Secret",
            }

        results = self.search_laws("个人信息保护法", size=1)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if self.last_error:
            error_code, error_category, message = _classify_delilegal_error(
                self.last_error
            )
            return {
                "ok": False,
                "latency_ms": latency_ms,
                "result_count": 0,
                "error_code": error_code,
                "error_category": error_category,
                "error": message,
            }
        return {
            "ok": True,
            "latency_ms": latency_ms,
            "result_count": len(results),
            "error_code": "",
            "error_category": "",
            "error": "",
        }

    def search_cases(self, query: str, size: int = 3) -> list[dict[str, Any]]:
        self.last_error = None
        if not self.enabled or not query.strip():
            return []

        # Official DeliLegal shape (queryListCase): condition.keywordArr
        payload = {
            "pageNo": 1,
            "pageSize": size,
            "sortField": "correlation",
            "sortOrder": "desc",
            "condition": {
                "keywordArr": [query],
            },
        }
        headers = {
            "appid": self.app_id,
            "secret": self.secret,
            "Content-Type": "application/json",
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
        except Exception as exc:
            self.last_error = f"queryListCase request failed: {exc}"
            return []

        if not self._is_success(data):
            self.last_error = self._build_api_error("queryListCase", data)
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

    def search_laws(self, query: str, size: int = 5) -> list[dict[str, Any]]:
        self.last_error = None
        if not self.enabled or not query.strip():
            return []

        # Official DeliLegal shape (queryListLaw): condition.keywords + fieldName
        payload = {
            "pageNo": 1,
            "pageSize": size,
            "sortField": "correlation",
            "sortOrder": "desc",
            "condition": {
                "keywords": [query],
                "fieldName": "semantic",
            },
        }
        headers = {
            "appid": self.app_id,
            "secret": self.secret,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.base_url}/api/qa/v3/search/queryListLaw",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            self.last_error = f"queryListLaw request failed: {exc}"
            return []

        if not self._is_success(data):
            self.last_error = self._build_api_error("queryListLaw", data)
            return []

        candidates = self._extract_candidate_list(data)
        normalized: list[dict[str, Any]] = []
        for item in candidates[:size]:
            normalized.append(
                {
                    "title": item.get("title") or item.get("name") or "未命名法规",
                    "source": item.get("source") or item.get("sourceName") or "得理法搜",
                    "summary": item.get("summary") or item.get("snippet") or item.get("content") or "",
                }
            )
        return normalized

    def _is_success(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        if data.get("success") is True:
            return True
        return str(data.get("code")) == "0"

    def _build_api_error(self, endpoint: str, data: Any) -> str:
        if isinstance(data, dict):
            code = data.get("code")
            msg = data.get("msg") or data.get("message") or "unknown error"
            return f"{endpoint} failed: code={code}, msg={msg}"
        return f"{endpoint} failed: invalid response shape"

    def _extract_candidate_list(self, data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []

        # DeliLegal standard: {"body": {"data": [...]}}
        body = data.get("body")
        if isinstance(body, dict):
            body_data = body.get("data")
            if isinstance(body_data, list):
                return [item for item in body_data if isinstance(item, dict)]

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


def _classify_delilegal_error(error: str) -> tuple[str, str, str]:
    text = (error or "").lower()
    patterns = [
        (
            ("余额不足", "额度不足", "quota", "insufficient", "billing"),
            ("INSUFFICIENT_QUOTA", "quota", "得理 API 额度或余额不足"),
        ),
        (
            ("status code 401", "status code 403", "unauthorized", "forbidden", "鉴权", "密钥"),
            ("AUTHENTICATION_FAILED", "authentication", "得理 API 鉴权失败，请检查 App ID、Secret 和访问权限"),
        ),
        (
            ("status code 429", "rate limit", "too many requests", "限流"),
            ("RATE_LIMITED", "rate_limit", "得理 API 请求过于频繁，请稍后重试"),
        ),
        (
            ("timeout", "timed out", "超时"),
            ("TIMEOUT", "network", "得理 API 请求超时，请检查网络和 Base URL"),
        ),
        (
            ("connect", "dns", "ssl", "network"),
            ("NETWORK_ERROR", "network", "无法连接得理 API，请检查 Base URL、DNS、TLS 和网络策略"),
        ),
        (
            ("invalid response shape", "decode", "json"),
            ("INVALID_RESPONSE", "provider", "得理 API 返回了无法解析的响应"),
        ),
    ]
    for needles, classification in patterns:
        if any(needle in text for needle in needles):
            return classification
    return "PROVIDER_ERROR", "provider", "得理 API 最小查询探测失败，请查看后端错误日志"
