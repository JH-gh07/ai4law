import os

import requests

BASE_URL = os.getenv("AI4LAW_API_BASE", "http://127.0.0.1:8000/api/v1")


def post_json(path: str, payload: dict) -> dict:
    response = requests.post(f"{BASE_URL}{path}", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()
