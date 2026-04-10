import { useMemo, useState } from "react";
import { useAppStore } from "../../lib/app-store";
import type { TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";

type ResourcePanelProps = {
  taskSpace: TaskSpace;
};

export function ResourcePanel({ taskSpace }: ResourcePanelProps) {
  const { t } = useLang();
  const { state } = useAppStore();
  const [keyword, setKeyword] = useState("");
  const [failedOnly, setFailedOnly] = useState(false);
  const [highRiskOnly, setHighRiskOnly] = useState(false);
  const [artifactOnly, setArtifactOnly] = useState(false);

  const runs = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.moduleRuns, taskSpace.id]
  );

  const artifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const filteredArtifacts = useMemo(() => {
    if (!keyword.trim()) return artifacts;
    const token = keyword.toLowerCase();
    return artifacts.filter((item) => item.path.toLowerCase().includes(token) || item.module.toLowerCase().includes(token));
  }, [artifacts, keyword]);

  const relatedIssues = useMemo(
    () => state.issues.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.issues, taskSpace.id]
  );

  const latestRunByModule = useMemo(() => {
    const map = new Map<string, { success: boolean; id: string; riskHigh: boolean; hasArtifact: boolean; at: string }>();
    for (const run of runs) {
      const key = run.module;
      const exists = map.get(key);
      const at = run.finishedAt ?? run.startedAt;
      if (!exists || at > exists.at) {
        const riskHigh = relatedIssues.some((issue) => issue.module === run.module && issue.severity === "high");
        const hasArtifact = artifacts.some((artifact) => artifact.module === run.module);
        map.set(key, { success: run.success, id: run.id, riskHigh, hasArtifact, at });
      }
    }
    return map;
  }, [artifacts, relatedIssues, runs]);

  const moduleNodes = useMemo(() => {
    const nodes = [...latestRunByModule.entries()];
    return nodes.filter(([, info]) => {
      if (failedOnly && info.success) return false;
      if (highRiskOnly && !info.riskHigh) return false;
      if (artifactOnly && !info.hasArtifact) return false;
      return true;
    });
  }, [artifactOnly, failedOnly, highRiskOnly, latestRunByModule]);

  return (
    <aside className="pane resource-pane" data-guide="workspace-left">
      <div className="pane-title">{t("leftTitle")}</div>

      <input
        className="resource-search"
        placeholder={t("searchPlaceholder")}
        value={keyword}
        onChange={(event) => setKeyword(event.target.value)}
      />

      <div className="resource-filters">
        <button className={`tab-btn ${failedOnly ? "active" : ""}`} onClick={() => setFailedOnly((v) => !v)}>{t("filterFailedOnly")}</button>
        <button className={`tab-btn ${highRiskOnly ? "active" : ""}`} onClick={() => setHighRiskOnly((v) => !v)}>{t("filterHighOnly")}</button>
        <button className={`tab-btn ${artifactOnly ? "active" : ""}`} onClick={() => setArtifactOnly((v) => !v)}>{t("filterArtifactOnly")}</button>
      </div>

      <section className="resource-section">
        <h4>{t("objectTreeTitle")}</h4>
        <div className="resource-scroll object-tree-scroll">
          <article className="resource-item object-tree-root">
            <strong>{t("treeTaskNode")}: {taskSpace.name}</strong>
          </article>
          {moduleNodes.map(([module, info]) => {
            const moduleRuns = runs.filter((item) => item.module === module).slice(0, 3);
            const moduleArtifacts = filteredArtifacts.filter((item) => item.module === module).slice(0, 3);
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

      <section className="resource-section">
        <h4>{t("recentRuns")}</h4>
        <div className="resource-scroll">
          {runs.slice(0, 10).map((run) => (
            <div key={run.id} className="resource-item">
              <strong>{run.module.toUpperCase()}</strong>
              <span>{run.success ? t("statusSuccess").toUpperCase() : t("statusFailed").toUpperCase()}</span>
            </div>
          ))}
          {runs.length === 0 ? <p className="resource-empty">{t("noRunsYet")}</p> : null}
        </div>
      </section>

      <section className="resource-section">
        <h4>{t("artifactsTitle")}</h4>
        <div className="resource-scroll">
          {filteredArtifacts.slice(0, 20).map((artifact) => (
            <div key={artifact.id} className="resource-item">
              <strong>{artifact.kind}</strong>
              <code>{artifact.path}</code>
            </div>
          ))}
          {filteredArtifacts.length === 0 ? <p className="resource-empty">{t("noArtifacts")}</p> : null}
        </div>
      </section>
    </aside>
  );
}
