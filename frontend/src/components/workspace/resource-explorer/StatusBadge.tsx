import type { ExplorerStatus } from "./types";
import { useLang } from "../../../lib/language";

type StatusBadgeProps = {
  status: ExplorerStatus;
};

const STATUS_META: Record<ExplorerStatus, { label: { zh: string; en: string }; tone: string }> = {
  missing: { label: { zh: "缺失", en: "Missing" }, tone: "danger" },
  uploaded: { label: { zh: "已上传", en: "Uploaded" }, tone: "success" },
  parsed: { label: { zh: "已解析", en: "Parsed" }, tone: "info" },
  optional: { label: { zh: "可选", en: "Optional" }, tone: "neutral" },
  in_progress: { label: { zh: "进行中", en: "In Progress" }, tone: "active" },
  pending: { label: { zh: "待处理", en: "Pending" }, tone: "pending" },
  pending_generation: { label: { zh: "待生成", en: "Pending" }, tone: "pending" },
  blocked: { label: { zh: "阻塞", en: "Blocked" }, tone: "danger" },
  opened: { label: { zh: "打开中", en: "Opened" }, tone: "active" },
  collapsed: { label: { zh: "收起", en: "Collapsed" }, tone: "neutral" },
  failed: { label: { zh: "失败", en: "Failed" }, tone: "danger" },
  completed: { label: { zh: "完成", en: "Completed" }, tone: "success" },
  editing: { label: { zh: "编辑中", en: "Editing" }, tone: "active" }
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { lang } = useLang();
  const meta = STATUS_META[status];
  return <span className={`rx-badge rx-badge-${meta.tone}`}>{meta.label[lang]}</span>;
}
