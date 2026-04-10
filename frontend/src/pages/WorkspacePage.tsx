import { Navigate, useParams } from "react-router-dom";
import { WorkspaceShell } from "../components/workspace/WorkspaceShell";
import { useAppStore } from "../lib/app-store";

export function WorkspacePage() {
  const { taskId } = useParams();
  const { state } = useAppStore();

  const task = taskId
    ? state.taskSpaces.find((item) => item.id === taskId)
    : state.taskSpaces[0];

  if (!task) {
    return <Navigate to="/tasks" replace />;
  }

  return <WorkspaceShell taskSpace={task} />;
}
