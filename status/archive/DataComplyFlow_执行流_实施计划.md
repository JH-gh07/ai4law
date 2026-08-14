# 执行流成熟架构 — 三阶段实施计划

## Phase 1 (P0): 打通事件通道 → 实时可见

| # | 文件 | 改动 |
|---|------|------|
| 1 | `frontend/src/api/events.ts` | `fetchTaskEvents` 加 `getAuthHeaders()` |
| 2 | `backend/common/events/manager.py` | SSEManager 加 `stream_token` 生成/验证 |
| 3 | `backend/api/v1/endpoints/events.py` | 新增 `POST /token/{id}` 签发; SSE stream 支持 `?token=` 参数 |
| 4 | `frontend/src/lib/useTaskEvents.ts` | SSE 连接前先请求 stream token, URL 拼入 `?token=` |
| 5 | `frontend/src/components/workspace/WorkspaceShell.tsx` | 修复 activeTaskId 条件(已完成任务也设置) |

## Phase 2 (P1): 事件持久化 + 历史回放

| # | 文件 | 改动 |
|---|------|------|
| 6 | `backend/models/event_log.py` | 新建 EventLog SQLAlchemy 模型 |
| 7 | `backend/common/trace/recorder.py` | `record()` 双写: 审计 JSON + EventLog (SQLite) |
| 8 | `backend/api/v1/endpoints/events.py` | 新增 `GET /task/{id}/full` 从 EventLog 读取全量 |

## Phase 3 (P2): 取消机制 + 细粒度 LLM token

| # | 文件 | 改动 |
|---|------|------|
| 9 | `backend/common/tasks/manager.py` | cancel 加 threading.Event 信号量 |
| 10 | `backend/common/llm/client.py` | LLM 调用中检查 cancel event, 支持提前中止 |

先执行 Phase 1。
