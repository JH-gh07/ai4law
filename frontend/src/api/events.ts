import { apiFetch } from "./client";

export type TaskEventsResponse<TEvent> = {
  events?: TEvent[];
  latest_seq?: number;
};

export function getTaskEventStreamUrl(taskId: string): string {
  return `/api/v1/events/task/${encodeURIComponent(taskId)}/stream`;
}

export async function fetchTaskEvents<TEvent>(
  taskId: string,
  since: number,
): Promise<TaskEventsResponse<TEvent>> {
  const response = await apiFetch(
    `/api/v1/events/task/${encodeURIComponent(taskId)}/events?since=${since}`,
  );
  return (await response.json()) as TaskEventsResponse<TEvent>;
}
