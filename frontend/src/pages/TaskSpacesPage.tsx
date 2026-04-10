import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAppStore } from "../lib/app-store";
import type { Jurisdiction } from "../lib/domain";
import { useLang } from "../lib/language";

type TaskSpacesPageProps = {
  onStart: () => void;
};

const SAVED_TASK_IDS_KEY = "ai4law_saved_task_spaces_v1";

const readSavedTaskIds = (): string[] => {
  try {
    const raw = globalThis.localStorage?.getItem(SAVED_TASK_IDS_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
};

export function TaskSpacesPage({ onStart }: TaskSpacesPageProps) {
  const { t } = useLang();
  const { state } = useAppStore();
  const [query, setQuery] = useState("");
  const [jurisdiction, setJurisdiction] = useState<"ALL" | Jurisdiction>("ALL");
  const [savedTaskIds, setSavedTaskIds] = useState<string[]>(readSavedTaskIds);

  const cnTasks = [
    {
      title: "合规路径诊断",
      scenario: "适合首次判断义务",
      io: "输入：问答 · 输出：诊断报告",
      cta: "开始诊断"
    },
    {
      title: "安全评估路径",
      scenario: "适合需申报安全评估的企业",
      io: "输入：表单+材料 · 输出：风险自评估报告",
      cta: "开始填写材料"
    },
    {
      title: "认证 / 标准合同路径",
      scenario: "适用于认证与标准合同备案场景",
      io: "输入：处理活动信息 · 输出：PIPIA 报告",
      cta: "开始准备材料"
    },
    {
      title: "文档专项智能审查",
      scenario: "审查隐私政策、标准合同、DPA、云协议",
      io: "输入：文档上传 · 输出：问题与修改建议",
      cta: "上传文件审查"
    },
    {
      title: "通用服务",
      scenario: "覆盖尽调报告、合规备忘录、整改建议",
      io: "输入：业务背景材料 · 输出：清单化交付",
      cta: "查看可用服务"
    }
  ] as const;

  const euTransmissionTools = [
    {
      title: "SCC 审查",
      io: "输入：SCC 文本 · 输出：《SCC 合规审查报告》"
    },
    {
      title: "BCR 审核",
      io: "输入：BCR+集团范围 · 输出：BCR 审核报告"
    }
  ] as const;

  const euRiskTools = [
    {
      title: "DPIA 草案生成",
      io: "输入：处理活动描述 · 输出：DPIA 草案"
    },
    {
      title: "TIA 草案生成",
      io: "输入：国家+接收方+补充措施 · 输出：TIA 草案"
    }
  ] as const;

  const usPanels = [
    {
      title: "14117 行政令合规",
      theme: "risk",
      bullets: [
        "检测是否涉及关注国/被覆盖的人",
        "分析是否触发禁止或限制性交易",
        "输出红黄绿灯结论报告"
      ]
    },
    {
      title: "CPRA 合规",
      theme: "governance",
      bullets: [
        "数据映射与敏感信息识别",
        "告知/合同/权利机制检查",
        "输出合规全景报告"
      ]
    }
  ] as const;

  const capabilityItems = [
    "智能路径诊断",
    "风险评估报告生成",
    "法律文件智能审查",
    "风险与整改建议",
    "多法域知识支持"
  ] as const;

  const deliverableSamples = [
    {
      title: "《合规路径诊断报告》",
      desc: "输出适用路径、法规依据与下一步行动清单。"
    },
    {
      title: "《数据出境风险自评估报告》",
      desc: "按监管结构生成章节化草案，支持后续补证与复核。"
    },
    {
      title: "《个人信息保护影响评估报告》",
      desc: "覆盖认证/标准合同场景，形成 PIPIA 交付底稿。"
    },
    {
      title: "《SCC 合规审查报告》",
      desc: "条款级定位问题、风险解释与修改建议可追溯。"
    }
  ] as const;

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

  const savedTasks = useMemo(() => {
    const saved = new Set(savedTaskIds);
    return filteredTasks.filter((task) => saved.has(task.id));
  }, [filteredTasks, savedTaskIds]);

  useEffect(() => {
    try {
      globalThis.localStorage?.setItem(SAVED_TASK_IDS_KEY, JSON.stringify(savedTaskIds));
    } catch {
      // Ignore persistence failures in private mode or blocked storage.
    }
  }, [savedTaskIds]);

  useEffect(() => {
    const validIds = new Set(state.taskSpaces.map((task) => task.id));
    setSavedTaskIds((prev) => {
      const next = prev.filter((id) => validIds.has(id));
      if (next.length === prev.length && next.every((id, idx) => id === prev[idx])) {
        return prev;
      }
      return next;
    });
  }, [state.taskSpaces]);

  const toggleSaveTask = (taskId: string) => {
    setSavedTaskIds((prev) => {
      if (prev.includes(taskId)) return prev.filter((id) => id !== taskId);
      return [taskId, ...prev].slice(0, 40);
    });
  };

  return (
    <section className="page-shell tasks-page">
      <header className="tasks-hero tasks-hub-hero">
        <div>
          <p className="tasks-hub-kicker">TASK HUB</p>
          <h2>任务空间（总分流）</h2>
          <p className="tasks-hero-subtitle">
            先选法域，再选任务，再进入执行页。任务空间用于呈现“场景、输入、输出、交付物”的全链路入口。
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

      <section className="tasks-ia-strip">
        <span>首页门户</span>
        <span>法域工作台</span>
        <span>具体任务页面</span>
        <span>报告结果页</span>
      </section>

      <section className="tasks-section">
        <div className="tasks-section-head">
          <h3>法域差异化编排</h3>
          <p>以该区块作为唯一法域分流入口，直接进入对应工作区。</p>
        </div>
        <div className="tasks-diff-grid">
          <article className="tasks-diff-panel tasks-diff-cn">
            <header>
              <h4>中国：5个任务入口</h4>
              <p>诊断 / 安全评估 / 认证标准合同 / 文档审查 / 通用服务</p>
            </header>
            <div className="tasks-diff-cn-grid">
              {cnTasks.map((task) => (
                <article key={task.title} className="tasks-diff-cn-card">
                  <strong>{task.title}</strong>
                  <p>{task.scenario}</p>
                  <span>{task.io}</span>
                  <Link className="pill-btn" to="/jurisdictions/cn">{task.cta}</Link>
                </article>
              ))}
            </div>
          </article>

          <article className="tasks-diff-panel tasks-diff-eu">
            <header>
              <h4>欧盟：2组任务</h4>
              <p>传输工具（SCC + BCR）与风险评估（DPIA + TIA）分组展示</p>
            </header>
            <div className="tasks-diff-eu-groups">
              <section>
                <h5>传输工具类</h5>
                <div className="tasks-diff-eu-grid">
                  {euTransmissionTools.map((item) => (
                    <article key={item.title} className="tasks-diff-eu-card">
                      <strong>{item.title}</strong>
                      <p>{item.io}</p>
                    </article>
                  ))}
                </div>
              </section>
              <section>
                <h5>风险评估类</h5>
                <div className="tasks-diff-eu-grid">
                  {euRiskTools.map((item) => (
                    <article key={item.title} className="tasks-diff-eu-card">
                      <strong>{item.title}</strong>
                      <p>{item.io}</p>
                    </article>
                  ))}
                </div>
              </section>
            </div>
            <Link className="pill-btn-primary" to="/jurisdictions/eu">进入欧盟工作台</Link>
          </article>

          <article className="tasks-diff-panel tasks-diff-us">
            <header>
              <h4>美国：2栏结构</h4>
              <p>14117 风险预警 与 CPRA 治理检查，视觉语义明确区分</p>
            </header>
            <div className="tasks-diff-us-cols">
              {usPanels.map((panel) => (
                <section key={panel.title} className={`tasks-diff-us-card ${panel.theme}`}>
                  <strong>{panel.title}</strong>
                  <ul>
                    {panel.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
            <Link className="pill-btn-primary" to="/jurisdictions/us">进入美国工作台</Link>
          </article>
        </div>
      </section>

      <section className="tasks-section tasks-capability-section">
        <div className="tasks-section-head">
          <h3>平台能力</h3>
          <p>强调“合规工作台”属性，而非单点问答工具。</p>
        </div>
        <div className="tasks-capability-strip">
          {capabilityItems.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </section>

      <section className="tasks-section">
        <div className="tasks-section-head">
          <h3>案例 / 结果展示</h3>
          <p>先可视化交付物，再进入下载与复核流程。</p>
        </div>
        <div className="tasks-deliverable-grid">
          {deliverableSamples.map((sample) => (
            <article key={sample.title} className="tasks-deliverable-card">
              <div className="tasks-doc-thumb" />
              <strong>{sample.title}</strong>
              <p>{sample.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="tasks-section">
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
            <span>{t("tasksSavedCount")}</span>
            <strong>{savedTasks.length}</strong>
          </div>
          <button className="pill-btn-primary" onClick={onStart}>
            {t("startCta")}
          </button>
        </div>

        <div className="tasks-recent-shell">
          <aside className="tasks-saved-pane">
            <h4>{t("tasksSavedListTitle")}</h4>
            {savedTasks.length > 0 ? (
              <div className="tasks-saved-list">
                {savedTasks.map((task) => (
                  <article key={task.id} className="tasks-saved-item">
                    <div>
                      <strong>{task.name}</strong>
                      <p>{task.jurisdiction} · {task.mode.toUpperCase()}</p>
                    </div>
                    <Link to={`/workspace/${task.id}`} className="pill-btn">
                      {t("openWorkspace")}
                    </Link>
                  </article>
                ))}
              </div>
            ) : (
              <p className="resource-empty">{t("tasksSavedEmpty")}</p>
            )}
          </aside>

          <div className="task-grid tasks-grid">
            {filteredTasks.map((task) => {
              const latestRun = latestRunByTask.get(task.id);
              const saved = savedTaskIds.includes(task.id);
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
                    <button
                      className={`tasks-save-btn ${saved ? "is-saved" : ""}`}
                      onClick={() => toggleSaveTask(task.id)}
                    >
                      {saved ? t("tasksSavedProject") : t("tasksSaveProject")}
                    </button>
                    <Link to={`/workspace/${task.id}`} className="pill-btn">
                      {t("openWorkspace")}
                    </Link>
                  </div>
                </article>
              );
            })}
            {filteredTasks.length === 0 ? <p className="resource-empty">{t("taskSpacesEmpty")}</p> : null}
          </div>
        </div>
      </section>
    </section>
  );
}
