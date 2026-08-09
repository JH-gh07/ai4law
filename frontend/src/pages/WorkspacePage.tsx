import { Navigate, useParams } from "react-router-dom";
import { useAppStore } from "../lib/app-store";
import { WorkspaceShell } from "../components/workspace/WorkspaceShell";

/**
 * 工作区页面组件
 * 根据任务ID显示相应的工作区，如果没有指定任务ID则显示最近更新的任务
 */
export function WorkspacePage() {
  const { taskId } = useParams();
  const { state } = useAppStore();

  const latestTask = [...state.taskSpaces].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))[0];

  if (!taskId && latestTask) {
    return <Navigate to={`/workspace/${latestTask.id}`} replace />;//replace /语法是指在导航时替换当前的历史记录条目，而不是添加一个新的条目。这意味着用户在浏览器中点击“后退”按钮时，不会返回到之前的页面，而是直接返回到更早的页面。
  }

  const task = taskId ? state.taskSpaces.find((item) => item.id === taskId) : null;

  if (!task) {
    if (latestTask) {
      return <Navigate to={`/workspace/${latestTask.id}`} replace />;
    }
    return <Navigate to="/tasks" replace />;
  }

  return <WorkspaceShell taskSpace={task} />;
}
