import { RunTranscript } from "./RunTranscript";

type Props = {
  taskId: string | null;
  moduleLabel?: string;
};

export function ExecutionTimeline({ taskId, moduleLabel = "" }: Props) {
  return <RunTranscript taskId={taskId} moduleLabel={moduleLabel} />;
}
