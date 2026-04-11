import { Navigate, useParams } from "react-router-dom";
import { useAppStore } from "../lib/app-store";
import { SuperDesign002Page } from "./SuperDesign002Page";

export function WorkspacePage() {
  const { taskId } = useParams();
  const { state } = useAppStore();

  const latestTask = [...state.taskSpaces].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))[0];

  if (!taskId && latestTask) {
    return <Navigate to={`/workspace/${latestTask.id}`} replace />;
  }

  const task = taskId ? state.taskSpaces.find((item) => item.id === taskId) : null;

  if (!task) {
    if (latestTask) {
      return <Navigate to={`/workspace/${latestTask.id}`} replace />;
    }
    return <Navigate to="/tasks" replace />;
  }

  return <SuperDesign002Page taskSpace={task} />;
}
