import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAppStore } from "../lib/app-store";
import type { Jurisdiction } from "../lib/domain";
import { useLang } from "../lib/language";

type TaskSpacesPageProps = {
  onStart: () => void;
};

export function TaskSpacesPage({ onStart }: TaskSpacesPageProps) {
  const { t } = useLang();
  const { state } = useAppStore();
  const [query, setQuery] = useState("");
  const [jurisdiction, setJurisdiction] = useState<"ALL" | Jurisdiction>("ALL");

  const latestRunByTask = useMemo(() => {
    const map = new Map<string, { success: boolean; module: string; at: string }>();
    for (const run of state.moduleRuns) {
      const prev = map.get(run.taskSpaceId);
      const at = run.finishedAt ?? run.startedAt;
      if (!prev || at > prev.at) {
        map.set(run.taskSpaceId, { success: run.success, module: run.module, at });
      }
    }
    return map;
  }, [state.moduleRuns]);

  const filteredTasks = useMemo(() => {
    const token = query.trim().toLowerCase();
    return [...state.taskSpaces]
      .filter((task) => (jurisdiction === "ALL" ? true : task.jurisdiction === jurisdiction))
      .filter((task) => (token ? task.name.toLowerCase().includes(token) : true))
      .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
  }, [jurisdiction, query, state.taskSpaces]);

  const recent24hCount = useMemo(() => {
    const now = Date.now();
    return state.taskSpaces.filter((task) => now - new Date(task.updatedAt).getTime() <= 24 * 3600 * 1000).length;
  }, [state.taskSpaces]);

  return (
    <section className="page-shell tasks-page">
      <header className="tasks-hero">
        <div>
          <h2>{t("taskSpacesTitle")}</h2>
          <p className="tasks-hero-subtitle">{t("taskSpacesSubtitle")}</p>
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

      <div className="tasks-controls">
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
        <button className="pill-btn-primary" onClick={onStart}>{t("startCta")}</button>
      </div>

      <div className="task-grid tasks-grid">
        {filteredTasks.map((task) => {
          const latestRun = latestRunByTask.get(task.id);
          return (
            <article key={task.id} className="task-card tasks-card">
              <div className="tasks-card-head">
                <h3>{task.name}</h3>
                <span className={`tasks-status-pill ${latestRun ? (latestRun.success ? "ok" : "fail") : "idle"}`}>
                  {latestRun
                    ? `${latestRun.success ? "OK" : "FAIL"} · ${latestRun.module.toUpperCase()}`
                    : t("tasksCardNoRuns")}
                </span>
              </div>

              <div className="tasks-meta-row">
                <span>{t("tasksCardJurisdiction")}: {task.jurisdiction}</span>
                <span>{t("tasksCardMode")}: {task.mode.toUpperCase()}</span>
              </div>

              <p className="tasks-updated">{t("tasksCardUpdated")}: {new Date(task.updatedAt).toLocaleString()}</p>

              <div className="tasks-card-actions">
                <Link to={`/workspace/${task.id}`} className="pill-btn">{t("openWorkspace")}</Link>
              </div>
            </article>
          );
        })}
        {filteredTasks.length === 0 ? <p className="resource-empty">{t("taskSpacesEmpty")}</p> : null}
      </div>
    </section>
  );
}
