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

  const jurisdictionCards = [
    {
      code: "CN",
      title: "中国数据出境",
      desc: "围绕三路径要求进行路径判断、材料准备与报告交付。",
      tags: ["路径诊断", "安全评估", "PIPIA", "文档审查"],
      to: "/jurisdictions/cn"
    },
    {
      code: "EU",
      title: "欧盟数据跨境传输",
      desc: "围绕 SCC / BCR 与 DPIA / TIA 提供传输工具与风险评估支持。",
      tags: ["SCC", "BCR", "DPIA", "TIA"],
      to: "/jurisdictions/eu"
    },
    {
      code: "US",
      title: "美国（加州）数据出境",
      desc: "覆盖 14117 风险结论与 CPRA 治理检查双线合规场景。",
      tags: ["14117", "CPRA", "风险矩阵", "治理检查"],
      to: "/jurisdictions/us"
    }
  ] as const;

  const serviceCards = [
    {
      title: "从中国大陆向境外传输数据",
      audience: "适用于需判断三路径义务并准备申报/备案材料的企业",
      services: 5,
      outputs: ["路径诊断报告", "风险自评估报告", "PIPIA 报告", "文档审查结论"],
      to: "/jurisdictions/cn"
    },
    {
      title: "从欧盟向境外传输数据",
      audience: "适用于 GDPR 第五章下跨境传输工具与评估场景",
      services: 4,
      outputs: ["SCC 合规审查报告", "BCR 审核报告", "DPIA 草案", "TIA 草案"],
      to: "/jurisdictions/eu"
    },
    {
      title: "从美国向境外传输数据",
      audience: "适用于 14117 国家安全限制与 CPRA 消费者隐私治理场景",
      services: 2,
      outputs: ["14117 红黄绿灯结论", "高风险实体清单", "CPRA 合规全景报告"],
      to: "/jurisdictions/us"
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
      .filter((task) => (token ? task.name.toLowerCase().includes(token) : true))
      .sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
  }, [jurisdiction, query, state.taskSpaces]);

  const recent24hCount = useMemo(() => {
    const now = Date.now();
    return state.taskSpaces.filter((task) => now - new Date(task.updatedAt).getTime() <= 24 * 3600 * 1000).length;
  }, [state.taskSpaces]);

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
          <h3>法域科普与入口</h3>
          <p>先判断属于哪个法域，再进入该法域工作台选择具体任务。</p>
        </div>
        <div className="tasks-jurisdiction-grid">
          {jurisdictionCards.map((card) => (
            <article key={card.code} className="tasks-jurisdiction-card">
              <div className="tasks-jurisdiction-head">
                <strong>{card.title}</strong>
                <span>{card.code}</span>
              </div>
              <p>{card.desc}</p>
              <div className="tasks-tag-list">
                {card.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <Link className="pill-btn" to={card.to}>查看详情</Link>
            </article>
          ))}
        </div>
      </section>

      <section className="tasks-section">
        <div className="tasks-section-head">
          <h3>专项服务入口</h3>
          <p>按业务场景分流，直接看到“适用对象、可用服务数量、典型输出物”。</p>
        </div>
        <div className="tasks-service-grid">
          {serviceCards.map((card) => (
            <article key={card.title} className="tasks-service-card">
              <h4>{card.title}</h4>
              <p>{card.audience}</p>
              <div className="tasks-service-meta">可用服务：{card.services}</div>
              <ul>
                {card.outputs.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <Link className="pill-btn-primary" to={card.to}>进入法域工作台</Link>
            </article>
          ))}
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
          <h3>继续处理已有任务</h3>
          <p>下方保留你原来的任务列表能力，用于回到历史任务继续执行。</p>
        </div>

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
    </section>
  );
}
