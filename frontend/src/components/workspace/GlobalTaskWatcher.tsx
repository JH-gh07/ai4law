import { useEffect, useRef } from "react";
import { useAppStore } from "../../lib/app-store";
import { AsyncTaskNotFoundError, findModule, fetchModuleTaskStatus } from "../../api/modules";
import {
  isFinalAsyncState,
  isSuccessAsyncState,
  selectRunningModuleRuns,
} from "../../lib/run-state";
/**
 * GlobalTaskWatcher — 全局异步任务心跳轮询器。
 *
 * 职责：
 * 1. 持续性轮询 store 中所有 asyncState = running 的 ModuleRun
 * 2. 发现终态后 dispatch append_run 回填结果
 * 3. 不依赖任何具体页面/组件生命周期
 *
 * 在 App.tsx 根部挂载一次即可。
 */
export function GlobalTaskWatcher() {
  const { state, dispatch } = useAppStore();

  // 用 ref 避免 useEffect 依赖 state 导致频繁重建 interval
  const stateRef = useRef(state);
  stateRef.current = state;

  const inFlightRef = useRef(new Set<string>());

  useEffect(() => {
    const INTERVAL_MS = 5000;

    const poll = async () => {
      const currentState = stateRef.current;
      const runningRuns = selectRunningModuleRuns(currentState.moduleRuns);
      if (runningRuns.length === 0) return;

      const promises = runningRuns.map(async (run) => {
        const taskId = run.asyncTaskId;
        if (!taskId) return;

        // 防止同一 taskId 同一轮并发
        if (inFlightRef.current.has(taskId)) return;

        let moduleDefinition;
        try {
          moduleDefinition = findModule(run.module);
        } catch {
          return;
        }

        if (!moduleDefinition.asyncStatusEndpoint) return;

        inFlightRef.current.add(taskId);
        try {
          const status = await fetchModuleTaskStatus(moduleDefinition, taskId);
          const checkedAt = new Date().toISOString();

          if (isFinalAsyncState(status.state)) {
            dispatch({
              type: "append_run",
              payload: {
                id: run.id,
                taskSpaceId: run.taskSpaceId,
                module: run.module,
                runMode: "async",
                startedAt: run.startedAt,
                finishedAt: checkedAt,
                success: isSuccessAsyncState(status.state),
                request: run.request,
                response: status.result ?? run.response,
                error: status.error ?? "",
                asyncTaskId: taskId,
                asyncState: status.state,
                statusCheckedAt: checkedAt,
              },
            });
          } else {
            // The local run may have been marked failed by a client timeout
            // while the backend continued processing. Restore the authoritative
            // non-terminal state and let the watcher continue polling it.
            dispatch({
              type: "append_run",
              payload: {
                id: run.id,
                taskSpaceId: run.taskSpaceId,
                module: run.module,
                runMode: "async",
                startedAt: run.startedAt,
                finishedAt: "",
                success: false,
                request: run.request,
                response: run.response,
                error: "",
                errorCode: run.errorCode,
                asyncTaskId: taskId,
                asyncState: status.state,
                statusCheckedAt: checkedAt,
              },
            });
          }
        } catch (error) {
          if (error instanceof AsyncTaskNotFoundError) {
            const checkedAt = new Date().toISOString();
            dispatch({
              type: "append_run",
              payload: {
                id: run.id,
                taskSpaceId: run.taskSpaceId,
                module: run.module,
                runMode: "async",
                startedAt: run.startedAt,
                finishedAt: checkedAt,
                success: false,
                request: run.request,
                response: run.response,
                error: error.message,
                errorCode: "async_task_not_found",
                asyncTaskId: taskId,
                asyncState: "failed",
                statusCheckedAt: checkedAt,
              },
            });
          }
        } finally {
          inFlightRef.current.delete(taskId);
        }
      });

      await Promise.allSettled(promises);
    };

    // 挂载时立即检查一次
    void poll();

    const timer = setInterval(() => {
      void poll();
    }, INTERVAL_MS);

    return () => clearInterval(timer);
  }, [dispatch]); // 仅依赖 dispatch（稳定引用）

  return null;
}

// 导出 selectRunningModuleRuns 以复用
export { selectRunningModuleRuns };
