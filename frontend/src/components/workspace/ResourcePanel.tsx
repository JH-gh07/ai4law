import { useMemo } from "react";
import { useAppStore } from "../../lib/app-store";
import type { TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";

type ResourcePanelProps = {
  taskSpace: TaskSpace;
  tabs: Array<{ id: string; label: string; closable: boolean }>;
  openTabs: string[];
  activeTab: string;
  tabQuery: string;
  onTabQueryChange: (value: string) => void;
  onTabQuerySubmit: () => void;
  onActivateTab: (tabId: string) => void;
  onOpenTab: (tabId: string) => void;
  onCloseTab: (tabId: string) => void;
};

export function ResourcePanel({
  taskSpace,
  tabs,
  openTabs,
  activeTab,
  tabQuery,
  onTabQueryChange,
  onTabQuerySubmit,
  onActivateTab,
  onOpenTab,
  onCloseTab
}: ResourcePanelProps) {
  const { t } = useLang();
  const { state } = useAppStore();

  const runs = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.moduleRuns, taskSpace.id]
  );

  const artifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const latestRunByModule = useMemo(() => {
    const map = new Map<string, { success: boolean; id: string; at: string }>();
    for (const run of runs) {
      const key = run.module;
      const exists = map.get(key);
      const at = run.finishedAt ?? run.startedAt;
      if (!exists || at > exists.at) {
        map.set(key, { success: run.success, id: run.id, at });
      }
    }
    return map;
  }, [runs]);

  const moduleNodes = useMemo(
    () => [...latestRunByModule.entries()].sort((a, b) => (a[1].at < b[1].at ? 1 : -1)),
    [latestRunByModule]
  );
  const closedTabCount = tabs.length - openTabs.length;

  const onTabQueryKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      onTabQuerySubmit();
    }
  };

  return (
    <aside className="pane resource-pane" data-guide="workspace-left">
      <div className="pane-title">{t("leftTitle")}</div>
      <div className="resource-pane-body">
        <section className="resource-section resource-tab-shell">
          <h4>{t("workspaceTabSearchAction")} Tab</h4>
          <div className="resource-tab-search">
            <input
              value={tabQuery}
              onChange={(event) => onTabQueryChange(event.target.value)}
              onKeyDown={onTabQueryKeyDown}
              placeholder={t("workspaceTabSearchPlaceholder")}
            />
            <button className="pill-btn" onClick={onTabQuerySubmit}>
              {t("workspaceTabSearchAction")}
            </button>
          </div>
          <div className="resource-tab-list">
            {tabs.map((tab) => {
              const isOpen = openTabs.includes(tab.id);
              const isActive = activeTab === tab.id;
              return (
                <article key={tab.id} className={`resource-tab-item ${isActive ? "active" : ""}`}>
                  <button
                    className={`resource-tab-main ${isOpen ? "opened" : "closed"}`}
                    onClick={() => (isOpen ? onActivateTab(tab.id) : onOpenTab(tab.id))}
                  >
                    <span>{tab.label}</span>
                    <small>{isOpen ? "OPEN" : "CLOSED"}</small>
                  </button>
                  {isOpen && tab.closable ? (
                    <button
                      className="resource-tab-close"
                      aria-label={`close-${tab.id}`}
                      onClick={() => onCloseTab(tab.id)}
                    >
                      ×
                    </button>
                  ) : null}
                </article>
              );
            })}
          </div>
          <p className="resource-tab-meta">
            {t("workspaceTabSearchAction")} Tabs · {openTabs.length}/{tabs.length}
            {closedTabCount > 0 ? ` · +${closedTabCount}` : ""}
          </p>
        </section>

        <section className="resource-section resource-tree-shell">
          <h4>{t("objectTreeTitle")}</h4>
          <div className="resource-scroll object-tree-scroll">
            <article className="resource-item object-tree-root">
              <strong>{t("treeTaskNode")}: {taskSpace.name}</strong>
            </article>
            {moduleNodes.map(([module, info]) => {
              const moduleRuns = runs.filter((item) => item.module === module).slice(0, 3);
              const moduleArtifacts = artifacts.filter((item) => item.module === module).slice(0, 3);
              return (
                <article key={module} className="resource-item object-tree-module">
                  <strong>{t("treeModuleNode")}: {module.toUpperCase()}</strong>
                  <span>{info.success ? t("statusSuccess") : t("statusFailed")}</span>
                  <div className="object-tree-children">
                    {moduleRuns.map((run) => (
                      <code key={run.id}>{t("treeRunNode")}: {run.id.slice(0, 12)}</code>
                    ))}
                    {moduleArtifacts.map((artifact) => (
                      <code key={artifact.id}>{t("treeArtifactNode")}: {artifact.kind}</code>
                    ))}
                  </div>
                </article>
              );
            })}
            {moduleNodes.length === 0 ? <p className="resource-empty">{t("noRunsYet")}</p> : null}
          </div>
        </section>
      </div>
    </aside>
  );
}
