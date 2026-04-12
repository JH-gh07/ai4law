from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.dependencies import get_container
from backend.schemas.copilot import CopilotChatRequest, CopilotChatResponse

router = APIRouter()

_UNAVAILABLE_MARKER = "LLM服务暂时不可用"


def _action_hint(action: str | None) -> str:
    if not action:
        return "用户直接发起自由问答。"
    if action == "due_diligence":
        return "用户希望生成尽调提纲。"
    if action == "memo":
        return "用户希望生成合规备忘录。"
    if action == "remediation":
        return "用户希望生成整改清单。"
    return f"用户动作：{action}。"


def _format_history(messages) -> str:
    if not messages:
        return "（无）"
    rows: list[str] = []
    for item in messages[-8:]:
        role_name = "用户" if item.role == "user" else "助手"
        text = item.content.strip()
        if text:
            rows.append(f"- {role_name}: {text}")
    return "\n".join(rows) if rows else "（无）"


@router.post("/chat", response_model=CopilotChatResponse)
def chat_with_copilot(
    body: CopilotChatRequest,
    container=Depends(get_container),
) -> CopilotChatResponse:
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    system = (
        "你是 AI4Law 的通用服务 Copilot。"
        "你要基于当前任务上下文提供可执行、可复核的法律合规建议。"
        "输出要求：结论先行、条目清晰、避免空泛。"
        "如信息不足，明确指出缺失项并给出补充清单。"
    )

    context = body.context
    task_space = body.task_space
    user_prompt = (
        f"【任务空间】\n"
        f"- ID: {task_space.id}\n"
        f"- 名称: {task_space.name}\n"
        f"- 法域: {task_space.jurisdiction}\n"
        f"- 模块: {task_space.module}\n"
        f"- 模式: {task_space.mode or '-'}\n"
        f"- 工作区样式: {task_space.workspace_style or '-'}\n\n"
        f"【执行上下文】\n"
        f"- 当前阶段: {context.current_step or '-'}\n"
        f"- 阻塞原因: {context.blocker or '-'}\n"
        f"- 运行次数: {context.runs_count}\n"
        f"- 告警数量: {context.issues_count}\n"
        f"- 证据数量: {context.evidence_count}\n"
        f"- 产物数量: {context.artifact_count}\n"
        f"- 重点告警: {', '.join(context.top_issues[:5]) if context.top_issues else '-'}\n"
        f"- 近期产物: {', '.join(context.latest_artifacts[:5]) if context.latest_artifacts else '-'}\n\n"
        f"【会话历史】\n{_format_history(body.messages)}\n\n"
        f"【动作意图】\n{_action_hint(body.action)}\n\n"
        f"【本轮用户请求】\n{prompt}"
    )

    reply = container.llm_client.chat(
        system=system,
        user=user_prompt,
        temperature=0.2,
        max_tokens=2048,
    ).strip()

    if not reply:
        reply = "当前未返回有效内容，请重试。"

    fallback = (not container.llm_client.enabled) or (_UNAVAILABLE_MARKER in reply)
    return CopilotChatResponse(
        reply=reply,
        model=container.settings.llm_model,
        enabled=container.llm_client.enabled,
        fallback=fallback,
    )
