import type { ModuleKey, ModuleRun, TaskSpace } from "../../lib/domain";
import { ModuleRunPanel, type RunOutput } from "./ModuleRunPanel";
import { useLang } from "../../lib/language";

type StageSplitViewProps = {
  taskSpace: TaskSpace;
  onRunDone: (output: RunOutput) => void;
  latestRun: ModuleRun | null;
  onTaskCreated?: (taskId: string, module: ModuleKey) => void;
};

export function StageSplitView({ taskSpace, onRunDone, latestRun, onTaskCreated }: StageSplitViewProps) {
  const { lang } = useLang();

  return (
    <section className="stage-split stage-split-single" data-guide="workspace-center">
      <div className="stage-shell stage-shell-single">
        <section className="stage-pane stage-pane-run-only">
          <div className="stage-pane-head stage-pane-head-redesign">
            <div>
              <span>{lang === "zh" ? "运行面板" : "Run Panel"}</span>
              <strong>{lang === "zh" ? "执行当前模块并生成可预览结果" : "Run the active module and generate previewable results"}</strong>
            </div>
            {latestRun ? (
              <small className={`stage-run-status ${latestRun.success ? "is-success" : "is-fail"}`}>
                {latestRun.success ? (lang === "zh" ? "最近一次运行成功" : "Latest run succeeded") : (lang === "zh" ? "最近一次运行失败" : "Latest run failed")}
              </small>
            ) : null}
          </div>
          <section className="plugin-view plugin-view-run plugin-view-run-full">
            <ModuleRunPanel onRunDone={onRunDone} taskSpace={taskSpace} onTaskCreated={onTaskCreated} />
          </section>
        </section>
      </div>
    </section>
  );
}
