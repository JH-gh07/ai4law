import { useMemo } from "react";
import { useAppStore } from "../../lib/app-store";
import type { TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";

type ResourcePanelProps = {
  taskSpace: TaskSpace;
};

export function ResourcePanel({ taskSpace }: ResourcePanelProps) {
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

  return (
    <aside className="pane resource-pane" data-guide="workspace-left">
      <div className="pane-title">{t("leftTitle")}</div>

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
    </aside>
  );
}
