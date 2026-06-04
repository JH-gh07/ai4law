import { useEffect, useRef } from "react";
import { useAppStore } from "../../lib/app-store";
import { useTaskEvents } from "../../lib/useTaskEvents";

type Props = {
  taskId: string | null;
  taskSpaceId: string;
  moduleLabel?: string;
};

function extractStageName(summary: string): string {
  const trimmed = summary.replace(/^(CPRA |SCC |DPIA |BCR |TIA |EU |US )/, "");
  if (trimmed.length <= 12) return trimmed;
  return trimmed.slice(0, 12) + "…";
}

export function TaskEventBridge({ taskId, taskSpaceId, moduleLabel }: Props) {
  const events = useTaskEvents(taskId);
  const { dispatch } = useAppStore();
  const sessionIdRef = useRef<string | null>(null);
  const pendingStagesRef = useRef<string[]>([]);
  const seenSeqs = useRef(new Set<number>());

  useEffect(() => {
    if (!taskId || events.length === 0) return;

    const newEvents = events.filter((event) => !seenSeqs.current.has(event.seq));
    if (newEvents.length === 0) return;

    for (const event of newEvents) {
      seenSeqs.current.add(event.seq);

      switch (event.event_type) {
        case "status": {
          if (sessionIdRef.current) break;
          const sessionId = `run-${taskId}`;
          sessionIdRef.current = sessionId;
          dispatch({
            type: "begin_run_session",
            payload: {
              id: sessionId,
              taskSpaceId,
              taskId,
              module: moduleLabel ?? "",
              startedAt: event.timestamp,
              stages: [],
              isComplete: false,
              collapsed: false,
            },
          });
          break;
        }
        case "tool_start": {
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          const stageId = `stage-${taskId}-${event.seq}`;
          pendingStagesRef.current.push(stageId);
          const agentName = event.detail?.agent
            ? String(event.detail.agent)
            : event.detail?.tool
              ? String(event.detail.tool)
              : extractStageName(event.summary);
          const command = event.detail?.tool
            ? String(event.detail.tool)
            : event.detail?.agent
              ? String(event.detail.agent)
              : undefined;

          dispatch({
            type: "begin_run_session",
            payload: {
              id: sessionId,
              taskSpaceId,
              taskId,
              module: moduleLabel ?? "",
              startedAt: event.timestamp,
              stages: [{
                id: stageId,
                name: agentName,
                status: "running",
                startedAt: event.timestamp,
                command,
                icon: "🔧",
              }],
              isComplete: false,
              collapsed: false,
            },
          });
          break;
        }
        case "tool_result": {
          const stageId = pendingStagesRef.current.pop();
          const sessionId = sessionIdRef.current;
          if (!stageId || !sessionId) break;
          dispatch({
            type: "stage_done",
            payload: {
              sessionId,
              stageId,
              summary: event.summary,
              detail: event.detail ?? null,
              completedAt: event.timestamp,
            },
          });
          break;
        }
        case "thought": {
          const sessionId = sessionIdRef.current;
          const runningStageId = pendingStagesRef.current[pendingStagesRef.current.length - 1];
          if (!sessionId || !runningStageId) break;
          dispatch({
            type: "stage_done",
            payload: {
              sessionId,
              stageId: runningStageId,
              summary: event.summary,
              completedAt: event.timestamp,
            },
          });
          break;
        }
        case "warning": {
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          const stageId = `stage-${taskId}-${event.seq}`;
          dispatch({
            type: "begin_run_session",
            payload: {
              id: sessionId,
              taskSpaceId,
              taskId,
              module: moduleLabel ?? "",
              startedAt: event.timestamp,
              stages: [{
                id: stageId,
                name: event.summary,
                status: "done",
                startedAt: event.timestamp,
                completedAt: event.timestamp,
                summary: event.summary,
                icon: "⚠️",
              }],
              isComplete: false,
              collapsed: false,
            },
          });
          break;
        }
        case "intermediate": {
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          const stageId = `stage-${taskId}-${event.seq}`;
          dispatch({
            type: "begin_run_session",
            payload: {
              id: sessionId,
              taskSpaceId,
              taskId,
              module: moduleLabel ?? "",
              startedAt: event.timestamp,
              stages: [{
                id: stageId,
                name: extractStageName(event.summary),
                status: "done",
                startedAt: event.timestamp,
                completedAt: event.timestamp,
                summary: event.summary,
                icon: "📊",
              }],
              isComplete: false,
              collapsed: false,
            },
          });
          break;
        }
        case "final": {
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          dispatch({
            type: "finish_run_session",
            payload: {
              sessionId,
              completedAt: event.timestamp,
              totalDurationMs: event.detail?.total_duration_ms
                ? Number(event.detail.total_duration_ms)
                : undefined,
            },
          });
          break;
        }
        case "final_brief":
          break;
      }
    }
  }, [dispatch, events, moduleLabel, taskId, taskSpaceId]);

  useEffect(() => {
    return () => {
      sessionIdRef.current = null;
      pendingStagesRef.current = [];
      seenSeqs.current.clear();
    };
  }, [taskId]);

  return null;
}
