from pathlib import Path

from backend.common.llm.client import LLMClient
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
