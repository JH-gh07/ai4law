import { useMemo, useState, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { WorkspacePromptModal } from "../components/common/WorkspacePromptModal";
import { useAppStore } from "../lib/app-store";
import type { Jurisdiction, LaunchMode } from "../lib/domain";
import { useLang } from "../lib/language";

import { getRunLifecycleState } from "../lib/run-state";
import {
  buildSuggestedTaskName,
  findTaskTemplate,
  getTaskTemplateInputHint,
  getTaskTemplateOutputHint,
  getTaskTemplateTitle,
  listTaskTemplatesByJurisdiction
} from "../lib/task-templates";

type TaskSpacesPageProps = {
  onStart: () => void;
  onQuickCreate: (config: {
    mode: LaunchMode;
    name: string;
    jurisdiction: Jurisdiction;
    taskTemplateId: string;
  }) => void;
};

export function TaskSpacesPage({ onStart, onQuickCreate }: TaskSpacesPageProps) {
  const { t, lang } = useLang();
  const { state, dispatch } = useAppStore();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [jurisdiction, setJurisdiction] = useState<"ALL" | Jurisdiction>("ALL");
  const [quickCreateDraft, setQuickCreateDraft] = useState<{ taskTemplateId: string; value: string; error: string } | null>(null);
  const [renameDraft, setRenameDraft] = useState<{ taskId: string; value: string } | null>(null);
  const [pendingDeleteTask, setPendingDeleteTask] = useState<{ taskId: string; name: string } | null>(null);

  const jurisdictionShowcase = [
    {
      code: "CN" as const,
      tone: "cn" as const,
      title: lang === "zh" ? "中国任务包" : "China Task Pack",
      description: lang === "zh" ? "点击具体类别后即创建新任务并进入工作区" : "Create and enter a new task directly from category"
    },
    {
      code: "EU" as const,
      tone: "eu" as const,
      title: lang === "zh" ? "欧盟任务包" : "EU Task Pack",
      description: lang === "zh" ? "围绕 SCC / BCR / DPIA / TIA 的合规模块" : "Compliance modules for SCC / BCR / DPIA / TIA"
    },
    {
      code: "US" as const,
      tone: "us" as const,
      title: lang === "zh" ? "美国任务包" : "US Task Pack",
      description: lang === "zh" ? "覆盖 EO 14117 与 CPRA 的任务类别" : "Task categories for EO 14117 and CPRA"
    }
  ];

  const latestRunByTask = useMemo(() => {
    const map = new Map<string, { state: "idle" | "running" | "success" | "failed"; module: string; at: string }>();
    for (const run of state.moduleRuns) {
      const prev = map.get(run.taskSpaceId);
      const at = run.finishedAt ?? run.startedAt;
      if (!prev || at > prev.at) {
        map.set(run.taskSpaceId, { state: getRunLifecycleState(run), module: run.module, at });
      }
    }
    return map;
  }, [state.moduleRuns]);

  const filteredTasks = useMemo(() => {
    const token = query.trim().toLowerCase();
    return [...state.taskSpaces]
      .filter((task) => (jurisdiction === "ALL" ? true : task.jurisdiction === jurisdiction))
      .filter((task) => {
        if (!token) return true;
        const latestModule = latestRunByTask.get(task.id)?.module ?? "";
        const searchable = `${task.name} ${task.jurisdiction} ${task.mode} ${latestModule}`.toLowerCase();
        return searchable.includes(token);
      })
      .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
  }, [jurisdiction, latestRunByTask, query, state.taskSpaces]);

  const recent24hCount = useMemo(() => {
    const now = Date.now();
    return state.taskSpaces.filter((task) => now - new Date(task.updatedAt).getTime() <= 24 * 3600 * 1000).length;
  }, [state.taskSpaces]);

  const renameTask = (taskId: string, currentName: string) => {
    setRenameDraft({ taskId, value: currentName });
  };

  const submitRenameTask = () => {
    if (!renameDraft) return;
    const task = state.taskSpaces.find((item) => item.id === renameDraft.taskId);
    const nextName = renameDraft.value.trim();
    if (!task || !nextName || nextName === task.name) {
      setRenameDraft(null);
      return;
    }
    dispatch({
      type: "rename_task_space",
      payload: {
        id: renameDraft.taskId,
        name: nextName,
        updatedAt: new Date().toISOString()
      }
    });
    setRenameDraft(null);
  };

  const openTask = (taskId: string) => {
    navigate(`/workspace/${taskId}`);
  };

  const deleteTask = (taskId: string) => {
    const task = state.taskSpaces.find((item) => item.id === taskId);
    if (!task) return;
    setPendingDeleteTask({ taskId, name: task.name });
  };

  const submitDeleteTask = () => {
    if (!pendingDeleteTask) return;
    dispatch({ type: "delete_task_space", payload: { id: pendingDeleteTask.taskId } });
    setPendingDeleteTask(null);
  };

  const onTaskCardKeyDown = (event: KeyboardEvent<HTMLElement>, taskId: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openTask(taskId);
    }
  };

  const quickCreateFromTemplate = (taskTemplateId: string) => {
    const taskTemplate = findTaskTemplate(taskTemplateId);
    if (!taskTemplate) return;
    setQuickCreateDraft({
      taskTemplateId: taskTemplate.id,
      value: buildSuggestedTaskName(taskTemplate, lang),
      error: ""
    });
  };

  const submitQuickCreateTask = () => {
    if (!quickCreateDraft) return;
    const taskTemplate = findTaskTemplate(quickCreateDraft.taskTemplateId);
    if (!taskTemplate) {
      setQuickCreateDraft(null);
      return;
    }
    const taskName = quickCreateDraft.value.trim();
    if (!taskName) {
      setQuickCreateDraft((prev) => (prev ? { ...prev, error: t("tasksQuickCreateEmptyError") } : prev));
      return;
    }
    onQuickCreate({
      mode: "rapid",
      name: taskName,
      jurisdiction: taskTemplate.jurisdiction,
      taskTemplateId: taskTemplate.id
    });
    setQuickCreateDraft(null);
  };

  return (
    <section className="page-shell tasks-page">
      <header className="tasks-hero tasks-hub-hero">
        <div>
          <p className="tasks-hub-kicker">TASK HUB</p>
          <h2>{lang === "zh" ? "任务空间" : "Task Space"}</h2>
          <p className="tasks-hero-subtitle">
            {lang === "zh"
              ? "点击法域下的具体类别，先命名再直接创建新任务进入工作区。每个任务空间已绑定后端可执行模块，可直接运行与回溯"
              : "Select a category under each jurisdiction, name your task, and enter workspace directly. Each task space is wired to executable backend modules."}
          </p>
          <div className="tasks-hub-actions">
            <button className="pill-btn-primary" onClick={onStart}>{t("startCta")}</button>
            <Link className="pill-btn" to="/workspace">{t("openWorkspace")}</Link>
          </div>
        </div>
        <div className="tasks-hero-stats">
          <article className="tasks-stat-card">
            <span>{t("tasksStatTotal")}</span>
            <strong>{state.taskSpaces.length}</strong>
          </article>
          <article className="tasks-stat-card">
            <span>{t("tasksStatRecent")}</span>
            <strong>{recent24hCount}</strong>
          </article>
          <article className="tasks-stat-card">
            <span>{t("tasksStatRuns")}</span>
            <strong>{state.moduleRuns.length}</strong>
          </article>
        </div>
      </header>

      <section className="tasks-section tasks-showcase-section">
        <div className="tasks-section-head">
          <h3>{lang === "zh" ? "法域差异化编排" : "Jurisdiction-Oriented Orchestration"}</h3>
          <p>{lang === "zh" ? "点击具体类别后直接创建新任务，不再经过法域中间层" : "Create a task directly from category without an extra jurisdiction step."}</p>
        </div>
        <div className="tasks-showcase-grid">
          {jurisdictionShowcase.map((item) => (
            <article key={item.code} className={`tasks-showcase-card ${item.tone}`}>
              <header className="tasks-showcase-head">
                <span className="tasks-showcase-code">{item.code}</span>
                <h4>{item.title}</h4>
                <p>{item.description}</p>
              </header>
              <ul className="tasks-showcase-list">
                {listTaskTemplatesByJurisdiction(item.code).map((template) => (
                  <li key={template.id}>
                    {(() => {
                      const inputHint = getTaskTemplateInputHint(template, lang).trim();
                      const outputHint = getTaskTemplateOutputHint(template, lang).trim();
                      const mergedHint = inputHint && outputHint
                        ? `${inputHint} · ${outputHint}`
                        : inputHint || outputHint;
                      return (
                    <button
                      type="button"
                      className="tasks-showcase-entry"
                      onClick={() => quickCreateFromTemplate(template.id)}
                    >
                      <strong>{getTaskTemplateTitle(template, lang)}</strong>
                      <span>{mergedHint}</span>
                    </button>
                      );
                    })()}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="tasks-section tasks-recent-section">
        <div className="tasks-section-head">
          <h3>{t("tasksRecentTitle")}</h3>
          <p>{t("tasksRecentSubtitle")}</p>
        </div>

        <div className="tasks-controls tasks-recent-controls">
          <input
            className="resource-search tasks-search"
            placeholder={t("tasksSearchPlaceholder")}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="tasks-filter-tabs">
            <button
              className={`tab-btn ${jurisdiction === "ALL" ? "active" : ""}`}
              onClick={() => setJurisdiction("ALL")}
            >
              {t("tasksFilterAll")}
            </button>
            {(["CN", "EU", "US"] as const).map((item) => (
              <button
                key={item}
                className={`tab-btn ${jurisdiction === item ? "active" : ""}`}
                onClick={() => setJurisdiction(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <div className="tasks-recent-stats">
            <span>{t("tasksStatTotal")}</span>
            <strong>{filteredTasks.length}</strong>
          </div>
          <button className="pill-btn-primary" onClick={onStart}>
            {t("startCta")}
          </button>
        </div>

        <div className="tasks-recent-shell">
          <div className="task-grid tasks-grid">
            {filteredTasks.map((task) => {
              const latestRun = latestRunByTask.get(task.id);
              const taskTemplate = findTaskTemplate(task.taskTemplateId) ?? findTaskTemplate("cn_diagnosis");
              return (
                <article
                  key={task.id}
                  className="task-card tasks-card is-clickable"
                  role="button"
                  tabIndex={0}
                  onClick={() => openTask(task.id)}
                  onKeyDown={(event) => onTaskCardKeyDown(event, task.id)}
                  aria-label={`${t("openWorkspace")} ${task.name}`}
                >
                  <div className="tasks-card-head">
                    <h3>{task.name}</h3>
                    <span className={`tasks-status-pill ${latestRun ? (latestRun.state === "running" ? "running" : latestRun.state === "success" ? "ok" : "fail") : "idle"}`}>
                      {latestRun
                        ? `${latestRun.state === "running" ? "RUNNING" : latestRun.state === "success" ? "OK" : "FAIL"} · ${latestRun.module.toUpperCase()}`
                        : t("tasksCardNoRuns")}
                    </span>
                  </div>

                  <div className="tasks-meta-row">
                    <span>{t("tasksCardJurisdiction")}: {task.jurisdiction}</span>
                    <span>{t("tasksCardMode")}: {task.mode.toUpperCase()}</span>
                    <span>{t("tasksCardTemplate")}: {taskTemplate ? getTaskTemplateTitle(taskTemplate, lang) : "-"}</span>
                    <span>{t("tasksCardModule")}: {task.module.toUpperCase()}</span>
                  </div>

                  <p className="tasks-updated">{t("tasksCardUpdated")}: {new Date(task.updatedAt).toLocaleString()}</p>

                  <div className="tasks-card-actions" onClick={(event) => event.stopPropagation()}>
                    <button
                      className="tasks-save-btn is-danger"
                      onClick={() => deleteTask(task.id)}
                    >
                      {t("tasksDeleteAction")}
                    </button>
                    <button
                      className="tasks-save-btn"
                      onClick={() => renameTask(task.id, task.name)}
                    >
                      {t("tasksRenameAction")}
                    </button>
                  </div>
                </article>
              );
            })}
            {filteredTasks.length === 0 ? <p className="resource-empty">{t("taskSpacesEmpty")}</p> : null}
          </div>
        </div>
      </section>

      <WorkspacePromptModal
        open={!!quickCreateDraft}
        title={t("tasksQuickCreateTitle")}
        description={t("tasksQuickCreateDesc")}
        valueLabel={t("tasksNameField")}
        value={quickCreateDraft?.value ?? ""}
        valuePlaceholder={t("tasksQuickCreatePlaceholder")}
        onValueChange={(value) => setQuickCreateDraft((prev) => (prev ? { ...prev, value, error: "" } : prev))}
        confirmText={t("tasksQuickCreateConfirmAction")}
        cancelText={t("cancelBtn")}
        errorText={quickCreateDraft?.error}
        modalClassName="action-modal-task-create"
        onCancel={() => setQuickCreateDraft(null)}
        onConfirm={submitQuickCreateTask}
      />

      <WorkspacePromptModal
        open={!!renameDraft}
        title={t("tasksRenameTitle")}
        description={t("tasksRenameDesc")}
        valueLabel={t("tasksNameField")}
        value={renameDraft?.value ?? ""}
        valuePlaceholder={t("tasksRenamePrompt")}
        onValueChange={(value) => setRenameDraft((prev) => (prev ? { ...prev, value } : prev))}
        confirmText={t("tasksRenameConfirmAction")}
        cancelText={t("cancelBtn")}
        confirmDisabled={!renameDraft || renameDraft.value.trim().length === 0}
        onCancel={() => setRenameDraft(null)}
        onConfirm={submitRenameTask}
      />

      <WorkspacePromptModal
        open={!!pendingDeleteTask}
        title={t("tasksDeleteTitle")}
        description={`${t("tasksDeleteConfirm")}${pendingDeleteTask ? `\n${pendingDeleteTask.name}` : ""}`}
        confirmText={t("tasksDeleteConfirmAction")}
        cancelText={t("cancelBtn")}
        onCancel={() => setPendingDeleteTask(null)}
        onConfirm={submitDeleteTask}
      />
    </section>
  );
}
