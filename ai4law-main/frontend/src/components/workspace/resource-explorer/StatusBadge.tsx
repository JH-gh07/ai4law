import type { ExplorerStatus } from "./types";

type StatusBadgeProps = {
  status: ExplorerStatus;
};

const STATUS_META: Record<ExplorerStatus, { label: string; tone: string }> = {
  missing: { label: "缺失", tone: "danger" },
  uploaded: { label: "已上传", tone: "success" },
  parsed: { label: "已解析", tone: "info" },
  optional: { label: "可选", tone: "neutral" },
  in_progress: { label: "进行中", tone: "active" },
  pending: { label: "待处理", tone: "pending" },
  pending_generation: { label: "待生成", tone: "pending" },
  blocked: { label: "阻塞", tone: "danger" },
  opened: { label: "打开中", tone: "active" },
  collapsed: { label: "收起", tone: "neutral" },
  failed: { label: "失败", tone: "danger" },
  completed: { label: "完成", tone: "success" },
  editing: { label: "编辑中", tone: "active" }
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const meta = STATUS_META[status];
  return <span className={`rx-badge rx-badge-${meta.tone}`}>{meta.label}</span>;
}
