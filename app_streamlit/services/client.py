import os

import requests

BASE_URL = os.getenv("AI4LAW_API_BASE", "http://127.0.0.1:8000/api/v1")


def _format_http_error(response: requests.Response) -> str:
    status = response.status_code
    url = response.url
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if status == 422 and isinstance(payload, dict):
        details = payload.get("detail")
        if isinstance(details, list):
            messages: list[str] = []
            for item in details:
                if not isinstance(item, dict):
                    continue
                loc = item.get("loc", [])
                field = ".".join(str(x) for x in loc[1:]) if isinstance(loc, list) and len(loc) > 1 else str(loc)
                msg = item.get("msg", "invalid value")
                messages.append(f"{field}: {msg}")
            if messages:
                return f"HTTP 422 {url}\n" + "\n".join(messages)

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail:
            return f"HTTP {status} {url}\n{detail}"

    text = (response.text or "").strip()
    return f"HTTP {status} {url}\n{text[:300]}"


def post_json(path: str, payload: dict) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        response = requests.post(url, json=payload, timeout=60)
    except requests.RequestException as exc:
        raise RuntimeError(f"Request failed: {url}\n{exc}") from exc
    if not response.ok:
        raise RuntimeError(_format_http_error(response))
    return response.json()


def get_json(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, timeout=60)
    except requests.RequestException as exc:
        raise RuntimeError(f"Request failed: {url}\n{exc}") from exc
    if not response.ok:
        raise RuntimeError(_format_http_error(response))
    return response.json()
