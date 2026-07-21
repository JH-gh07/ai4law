from backend.core.settings import Settings
from backend.integrations.delilegal import DeliLegalService


def _configured_service() -> DeliLegalService:
    return DeliLegalService(
        Settings(
            delilegal_app_id="test-app",
            delilegal_secret="test-secret",
            _env_file=None,
        )
    )


def test_delilegal_probe_distinguishes_actionable_failure_categories() -> None:
    service = _configured_service()
    current_error = {"message": ""}

    def failed_search(_query: str, size: int = 1):
        assert size == 1
        service.last_error = current_error["message"]
        return []

    service.search_laws = failed_search  # type: ignore[method-assign]
    cases = {
        "request failed: status code 401": ("AUTHENTICATION_FAILED", "authentication"),
        "code=402, msg=余额不足": ("INSUFFICIENT_QUOTA", "quota"),
        "request failed: status code 429": ("RATE_LIMITED", "rate_limit"),
        "request timed out": ("TIMEOUT", "network"),
        "connection refused": ("NETWORK_ERROR", "network"),
        "invalid response shape": ("INVALID_RESPONSE", "provider"),
        "unknown provider rejection": ("PROVIDER_ERROR", "provider"),
    }

    for error, expected in cases.items():
        current_error["message"] = error
        result = service.probe()
        assert (result["error_code"], result["error_category"]) == expected


def test_delilegal_probe_treats_a_successful_empty_search_as_healthy() -> None:
    service = _configured_service()

    def empty_search(_query: str, size: int = 1):
        service.last_error = None
        return []

    service.search_laws = empty_search  # type: ignore[method-assign]

    result = service.probe()

    assert result["ok"] is True
    assert result["result_count"] == 0
    assert result["error_code"] == ""
