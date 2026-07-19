from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend.common.events.manager import get_ssemanager
from backend.common.trace.context import current_trace
from backend.common.trace.recorder import TraceRecorder
from backend.core.dependencies import get_container
from backend.schemas.copilot import CopilotChatRequest, CopilotChatResponse

router = APIRouter()


def _action_hint(action: str | None) -> str:
    if not action:
        return "自由对话"
    if action == "due_diligence":
        return "尽调支持"
    if action == "memo":
        return "备忘录支持"
    if action == "remediation":
        return "整改建议"
    return action


def _format_history(messages: list) -> str:
    if not messages:
        return "（无）"

    rows: list[str] = []
    for item in messages[-12:]:
        role_name = "用户" if item.role == "user" else "助手"
        text = item.content.strip()
        if text:
            rows.append(f"{role_name}: {text}")
    return "\n".join(rows) if rows else "（无）"


def _is_small_talk(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {
        "hi",
        "hello",
        "hey",
        "你好",
        "你好啊",
        "在吗",
        "你在吗",
        "嗨",
        "哈喽",
    }


def _build_local_reply(body: CopilotChatRequest) -> str:
    prompt = body.prompt.strip()
    context = body.context
    task_space = body.task_space

    if _is_small_talk(prompt):
        if context.blocker:
            return (
                f"我在。现在这个任务卡在“{context.blocker}”。"
                "你可以直接问我要做什么，或者把现有材料发给我，我帮你一起判断下一步。"
            )
        return "我在。你可以直接问我当前任务怎么推进，我会结合上下文跟你一起分析。"

    if any(keyword in prompt.lower() for keyword in ("下一步", "怎么做", "怎么办", "建议", "next")):
        if context.blocker:
            return (
                f"先处理当前阻塞项：{context.blocker}。"
                "把这一步补齐后，再重新运行当前模块，我就能继续帮你判断结果和风险。"
            )
        return "可以先把你的目标、材料现状和卡点发我，我来帮你拆下一步。"

    if any(keyword in prompt for keyword in ("总结", "概述", "现在什么情况")):
        return (
            f"当前任务是“{task_space.name}”，模块为 {task_space.module}，模式为 {task_space.mode or '-'}。"
            f"目前运行 {context.runs_count} 次，告警 {context.issues_count} 条，证据 {context.evidence_count} 条，产物 {context.artifact_count} 个。"
            f"{'当前卡点是：' + context.blocker + '。' if context.blocker else ''}"
            "如果你愿意，我可以继续帮你把下一步动作直接列出来。"
        )

    return (
        "我可以正常和你一起聊这个任务。"
        f"当前我知道的上下文是：任务“{task_space.name}”，模块 {task_space.module}，"
        f"{'当前卡在“' + context.blocker + '”。' if context.blocker else '暂时没有明确阻塞。'}"
        "你可以直接问我要不要补材料、先做哪一步、某个风险怎么判断，或者让我帮你整理结论。"
    )


@router.post("/chat", response_model=CopilotChatResponse)
def chat_with_copilot(
    body: CopilotChatRequest,
    container=Depends(get_container),
) -> CopilotChatResponse:
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    context = body.context
    task_space = body.task_space

    system = (
        "你是 AI4Law 工作台里的 Copilot，需要像一个正常、自然、简洁的中文助手与用户对话。"
        "优先直接回应用户当下这句话，而不是机械复述整个任务状态。"
        "只有在确实有帮助时，才引用任务上下文、阻塞项、告警或产物。"
        "如果用户只是打招呼、试探、追问、确认，先像正常聊天一样回答，不要输出报告体、清单体或大段模板。"
        "默认回答控制在 2 到 6 句，除非用户明确要求详细展开。"
        "不要总用“结论/现状说明/缺失信息”这种固定结构。"
        "如果信息不足，先用一句话说明还缺什么，再顺着用户的问题继续聊。"
        "你的语气要像搭档，不要像审计报告生成器。"
    )

    user_prompt = (
        "下面是辅助上下文，供你参考，不要求你逐项复述。\n\n"
        f"任务名称：{task_space.name}\n"
        f"法域：{task_space.jurisdiction}\n"
        f"模块：{task_space.module}\n"
        f"模式：{task_space.mode or '-'}\n"
        f"工作区样式：{task_space.workspace_style or '-'}\n"
        f"当前阶段：{context.current_step or '-'}\n"
        f"当前阻塞：{context.blocker or '-'}\n"
        f"运行次数：{context.runs_count}\n"
        f"告警数量：{context.issues_count}\n"
        f"证据数量：{context.evidence_count}\n"
        f"产物数量：{context.artifact_count}\n"
        f"重点问题：{', '.join(context.top_issues[:5]) if context.top_issues else '-'}\n"
        f"近期产物：{', '.join(context.latest_artifacts[:5]) if context.latest_artifacts else '-'}\n"
        f"当前执行摘要：{context.trace_summary or '-'}\n"
        f"当前执行阶段：{context.trace_stage or '-'}\n"
        f"当前执行状态：{context.trace_status or '-'}\n"
        f"关键执行节点：{'; '.join(context.trace_highlights[:6]) if context.trace_highlights else '-'}\n"
        f"用户意图：{_action_hint(body.action)}\n\n"
        f"最近对话：\n{_format_history(body.messages)}\n\n"
        f"用户刚刚说：{prompt}\n\n"
        "请像正常聊天一样直接回复用户。除非用户明确要结构化输出，否则不要自发写成长报告。"
    )

    fallback = not container.llm_client.enabled
    reply = ""
    usage_payload = {"usage_source": "unavailable"}

    trace = None
    trace_token = None
    if body.task_id:
        trace = TraceRecorder(Path("storage/traces") / f"copilot_{body.task_id}", task_id=body.task_id)
        trace.subscribe(get_ssemanager().on_event)
        trace_token = current_trace.set(trace)
        trace.record(
            "tool_start",
            {
                "summary": "Copilot 对话请求",
                "detail": {
                    "tool": "copilot_chat",
                    "task": body.task_space.name,
                    "module": body.task_space.module,
                    "prompt": prompt[:800],
                    "history_count": len(body.messages),
                    "raw_name": "copilot_chat_request",
                },
            },
        )

    try:
        if not fallback:
            llm_result = container.llm_client.chat_with_metadata(
                system=system,
                user=user_prompt,
                temperature=0.6,
                max_tokens=800,
                channel="copilot",
            )
            reply = str(llm_result.get("content") or "").strip()
            usage_raw = llm_result.get("usage")
            if isinstance(usage_raw, dict):
                usage_payload = usage_raw
            fallback = not bool(reply)

        if fallback:
            reply = _build_local_reply(body)

        if trace is not None:
            trace.record(
                "tool_result",
                {
                    "summary": "Copilot 对话返回",
                    "detail": {
                        "tool": "copilot_chat",
                        "model": container.llm_client._model if container.llm_client.enabled else "local-copilot-fallback",
                        "fallback": fallback,
                        "content": reply[:1200],
                        "raw_name": "copilot_chat_response",
                    },
                },
            )

        return CopilotChatResponse(
            reply=reply,
            model=container.llm_client._model if container.llm_client.enabled else "local-copilot-fallback",
            enabled=container.llm_client.enabled,
            fallback=fallback,
            usage=usage_payload,
        )
    finally:
        if trace is not None:
            try:
                trace.write_manifest()
            except Exception:
                pass
        if trace_token is not None:
            current_trace.reset(trace_token)
