from pathlib import Path

from backend.common.llm.client import LLMClient
from backend.common.llm.context import current_llm_client
from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder
from backend.core.settings import Settings


def test_llm_client_trace_includes_provider_metadata(tmp_path: Path) -> None:
    settings = Settings(_env_file=None)
    settings._runtime_llm_providers = [
        {
            "id": "deepseek-demo",
            "name": "DeepSeek Demo",
            "provider_type": "openai_compatible",
            "api_key": "",
            "api_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "enabled": True,
            "timeout": 30,
        }
    ]
    settings._runtime_llm_active_provider_id = "deepseek-demo"
    client = LLMClient(settings)

    trace_dir = Path(tmp_path) / "trace"
    recorder = TraceRecorder(trace_dir, task_id="trace-task")
    token = current_trace.set(recorder)
    try:
        client.chat_with_metadata(system="s", user="u")
    finally:
        current_trace.reset(token)

    content = (trace_dir / "001_tool_start.json").read_text(encoding="utf-8")
    assert '"provider_id": "deepseek-demo"' in content
    assert '"provider_name": "DeepSeek Demo"' in content
    assert '"provider_type": "openai_compatible"' in content
    assert '"base_url": "https://api.deepseek.com/v1"' in content


def test_provider_snapshot_is_immutable_and_never_exposes_api_key() -> None:
    settings = Settings(_env_file=None)
    settings._runtime_llm_providers = [
        {
            "id": "snapshot-provider",
            "name": "Snapshot Provider",
            "provider_type": "openai_compatible",
            "api_key": "never-write-this-secret",
            "api_url": "https://example.com/v1",
            "model": "snapshot-model",
            "enabled": True,
            "timeout": 45,
        }
    ]
    settings._runtime_llm_active_provider_id = "snapshot-provider"

    snapshot = LLMClient(settings).provider_snapshot()
    public = snapshot.sanitized()

    assert public["provider_id"] == "snapshot-provider"
    assert public["model"] == "snapshot-model"
    assert public["api_key_configured"] is True
    assert len(public["fingerprint"]) == 64
    assert "api_key" not in public
    assert "never-write-this-secret" not in repr(snapshot)


def test_live_client_delegates_to_task_scoped_frozen_client(monkeypatch) -> None:
    live = LLMClient(Settings(_env_file=None))
    frozen = live.clone()
    calls: list[str] = []

    def frozen_chat(**_kwargs):
        calls.append("frozen")
        return {"content": "snapshot-result", "usage": {}, "fallback": False}

    monkeypatch.setattr(frozen, "chat_with_metadata", frozen_chat)
    token = current_llm_client.set(frozen)
    try:
        result = live.chat_with_metadata(system="s", user="u")
    finally:
        current_llm_client.reset(token)

    assert result["content"] == "snapshot-result"
    assert calls == ["frozen"]
