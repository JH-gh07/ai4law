import { useEffect, useMemo, type KeyboardEvent as ReactKeyboardEvent } from "react";
import type { ModuleRun, TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { findTaskTemplate, getTaskTemplateTitle } from "../../lib/task-templates";

type OpenQuestModalProps = {
  tasks: TaskSpace[];
  runs: ModuleRun[];
  query: string;
  onQueryChange: (value: string) => void;
  onClose: () => void;
  onOpenTask: (taskId: string) => void;
};

const toModeLabel = (mode: TaskSpace["mode"]) => {
  if (mode === "rapid") return "Rapid";
  if (mode === "draft") return "Draft";
  return "Matrix";
};

export function OpenQuestModal({
  tasks,
  runs,
  query,
  onQueryChange,
  onClose,
  onOpenTask
}: OpenQuestModalProps) {
  const { t, lang } = useLang();

  useEffect(() => {
    const onEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onClose();
    };
    globalThis.addEventListener("keydown", onEscape);
    return () => globalThis.removeEventListener("keydown", onEscape);
  }, [onClose]);

  const latestRunByTask = useMemo(() => {
    const map = new Map<string, ModuleRun>();
    for (const run of runs) {
      const prev = map.get(run.taskSpaceId);
      const at = run.finishedAt ?? run.startedAt;
      const prevAt = prev ? prev.finishedAt ?? prev.startedAt : "";
      if (!prev || at > prevAt) {
        map.set(run.taskSpaceId, run);
      }
    }
    return map;
  }, [runs]);

  const filtered = useMemo(() => {
    const token = query.trim().toLowerCase();
    const sorted = [...tasks].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
    if (!token) return sorted;
    return sorted.filter((task) => {
      const latest = latestRunByTask.get(task.id);
      const template = findTaskTemplate(task.taskTemplateId);
      const text = `${task.name} ${task.id} ${task.mode} ${task.jurisdiction} ${task.module} ${task.taskTemplateId} ${task.workspaceStyle} ${latest?.module ?? ""} ${template?.title.zh ?? ""} ${template?.title.en ?? ""}`.toLowerCase();
      return text.includes(token);
    });
  }, [latestRunByTask, query, tasks]);

  const latestUpdate = tasks.length
    ? [...tasks].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))[0]?.updatedAt
    : undefined;

  return (
    <div className="modal-backdrop quest-modal-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="quest-modal" onClick={(event) => event.stopPropagation()}>
        <header className="quest-modal-head">
          <div>
            <h3>{t("openQuestTitle")}</h3>
            <p>{t("openQuestDesc")}</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="close quest modal">×</button>
        </header>

        <div className="quest-modal-body">
          <aside className="quest-modal-left">
            <div className="quest-left-title">{t("openQuestTitle")}</div>
            <input
              className="quest-search"
              placeholder={t("openQuestSearchPlaceholder")}
              value={query}
              autoFocus
              onChange={(event) => onQueryChange(event.target.value)}
            />
            <div className="quest-left-pills">
              <span>{t("openQuestLocalCount")}: {tasks.length}</span>
              <span>
                {t("openQuestRecent")}:
                {" "}
                {latestUpdate ? new Date(latestUpdate).toLocaleString(lang === "zh" ? "zh-CN" : "en-US") : "-"}
              </span>
            </div>
          </aside>

          <section className="quest-modal-right">
            {filtered.length === 0 ? (
              <p className="resource-empty">{t("openQuestEmpty")}</p>
            ) : (
              filtered.map((task, index) => {
                const latest = latestRunByTask.get(task.id);
                const template = findTaskTemplate(task.taskTemplateId);
                const onCardKeyDown = (event: ReactKeyboardEvent<HTMLElement>) => {
                  if (event.key !== "Enter" && event.key !== " ") return;
                  event.preventDefault();
                  onOpenTask(task.id);
                };
                return (
                  <article
                    key={task.id}
                    className="quest-item-card"
                    role="button"
                    tabIndex={0}
                    onClick={() => onOpenTask(task.id)}
                    onKeyDown={onCardKeyDown}
                    aria-label={`${t("openQuestOpenAction")} ${task.name}`}
                  >
                    <div className="quest-item-row">
                      <strong>{task.name}</strong>
                      <small>
                        {t("openQuestUpdatedAt")}
                        {" "}
                        {new Date(task.updatedAt).toLocaleString(lang === "zh" ? "zh-CN" : "en-US")}
                      </small>
                    </div>

                    <p>
                      {latest
                        ? `Latest ${latest.module.toUpperCase()} · ${latest.success ? t("statusSuccess") : t("statusFailed")}`
                        : t("tasksCardNoRuns")}
                    </p>

                    <div className="quest-item-pills">
                      <span>{String(index + 1).padStart(3, "0")}</span>
                      <span>{toModeLabel(task.mode)}</span>
                      <span>{task.jurisdiction}</span>
                      <span>{task.module.toUpperCase()}</span>
                      {template ? <span>{getTaskTemplateTitle(template, lang)}</span> : null}
                    </div>

                    <button
                      className="pill-btn"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenTask(task.id);
                      }}
                    >
                      {t("openQuestOpenAction")}
                    </button>
                  </article>
                );
              })
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
