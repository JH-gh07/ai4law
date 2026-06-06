from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from openai import OpenAI

ROOT = Path("/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law")
FRONTEND_TMP = ROOT / "frontend" / "tmp" / "token-compare-20260606-130425"
RUNTIME_SETTINGS = ROOT / "storage" / "runtime_settings.json"


def load_runtime() -> dict:
    return json.loads(RUNTIME_SETTINGS.read_text(encoding="utf-8"))


def provider_config(provider_id: str, *, override_model: str | None = None) -> dict:
    payload = load_runtime()
    providers = payload["llm"]["providers"]
    for item in providers:
        if item["id"] == provider_id:
            cfg = dict(item)
            if override_model:
                cfg["model"] = override_model
            return cfg
    raise KeyError(provider_id)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def diagnosis_bundle() -> list[dict]:
    base = ROOT / "storage" / "traces" / "diagnosis_sync"
    prompts = []
    for name in ["001_tool_start.json", "003_tool_start.json"]:
        data = read_json(base / name)
        detail = data["payload"]["detail"]
        prompts.append(
            {
                "module": "diagnosis",
                "source": str(base / name),
                "system": detail["system"],
                "user": detail["user"],
                "temperature": detail["temperature"],
                "max_tokens": detail["max_tokens"],
            }
        )
    return prompts


def assessment_bundle() -> list[dict]:
    base = ROOT / "storage" / "traces" / "assessment_sync"
    prompts = []
    for seq in [11, 13, 15, 17, 19, 21, 23, 25]:
        data = read_json(base / f"{seq:03d}_tool_start.json")
        detail = data["payload"]["detail"]
        prompts.append(
            {
                "module": "assessment",
                "source": str(base / f"{seq:03d}_tool_start.json"),
                "system": detail["system"],
                "user": detail["user"],
                "temperature": detail["temperature"],
                "max_tokens": detail["max_tokens"],
            }
        )
    return prompts


def pipia_bundle() -> list[dict]:
    base = ROOT / "storage" / "traces" / "pipia_sync"
    prompts = []
    for seq in [1, 3, 5, 7, 9, 11, 13]:
        data = read_json(base / f"{seq:03d}_llm_chat_request.json")
        payload = data["payload"]
        prompts.append(
            {
                "module": "pipia",
                "source": str(base / f"{seq:03d}_llm_chat_request.json"),
                "system": payload["system"],
                "user": payload["user"],
                "temperature": payload["temperature"],
                "max_tokens": payload["max_tokens"],
            }
        )
    return prompts


def replay_bundle(client: OpenAI, model: str, prompts: list[dict]) -> dict:
    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    rows = []
    for idx, prompt in enumerate(prompts, start=1):
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            temperature=prompt["temperature"],
            max_tokens=prompt["max_tokens"],
        )
        usage = response.usage
        row = {
            "index": idx,
            "source": prompt["source"],
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }
        rows.append(row)
        total_prompt += row["prompt_tokens"]
        total_completion += row["completion_tokens"]
        total_tokens += row["total_tokens"]
    return {
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "llm_calls": len(rows),
        "rows": rows,
    }


def main() -> None:
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("all_proxy", None)
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("ALL_PROXY", None)

    bundles = {
        "diagnosis": diagnosis_bundle(),
        "assessment": assessment_bundle(),
        "pipia": pipia_bundle(),
    }
    providers = [
        ("siliconflow", "deepseek-ai/DeepSeek-V3.2"),
        ("tencent_hunyuan", "hunyuan-lite"),
    ]

    results = []
    for provider_id, model in providers:
        cfg = provider_config(provider_id, override_model=model)
        client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["api_url"],
            timeout=60,
        )
        for module, prompts in bundles.items():
            replay = replay_bundle(client, model, prompts)
            results.append(
                {
                    "module": module,
                    "provider_id": provider_id,
                    "model": model,
                    **replay,
                }
            )

    out_json = FRONTEND_TMP / "replay_results.json"
    out_md = FRONTEND_TMP / "replay_results.md"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 中国三模块 Prompt Bundle 回放 Token 对比",
        "",
        "| 模块 | Provider | Model | Prompt Tokens | Completion Tokens | Total Tokens | LLM Calls |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in results:
        lines.append(
            f"| {row['module']} | {row['provider_id']} | {row['model']} | {row['prompt_tokens']} | {row['completion_tokens']} | {row['total_tokens']} | {row['llm_calls']} |"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_json)
    print(out_md)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    main()
