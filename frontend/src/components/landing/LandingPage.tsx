import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../../lib/app-store";
import { useLang } from "../../lib/language";
import type { Jurisdiction, LaunchMode } from "../../lib/domain";

type LandingPageProps = {
  onStart: () => void;
  onQuickCreate: (config: {
    mode: LaunchMode;
    name: string;
    jurisdiction: Jurisdiction;
    taskTemplateId: string;
  }) => void;
};

type JurisdictionCard = {
  code: Jurisdiction;
  name: string;
  points: string[];
};

export function LandingPage({ onStart: _onStart, onQuickCreate: _onQuickCreate }: LandingPageProps) {
  const { lang, t } = useLang();
  const navigate = useNavigate();
  const { state } = useAppStore();
  const isZh = lang === "zh";

  const latestTask = useMemo(
    () => [...state.taskSpaces].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))[0] ?? null,
    [state.taskSpaces]
  );

  const painPoints = isZh
    ? [
        {
          title: "规则分散，判断容易出错",
          desc: "中国、欧盟、美国的跨境数据规则口径不同，企业很难快速判断适用路径与义务边界。",
          badge: "规则"
        },
        {
          title: "材料复杂，文书成本高",
          desc: "从数据清单、实体清单到影响评估与风险自评估，准备过程长、协同成本高、反复修改频繁。",
          badge: "文书"
        },
        {
          title: "审查标准不稳定，缺口难定位",
          desc: "很多问题并不是完全没有做，而是做得不完整、不一致、不足以支撑监管或客户审查。",
          badge: "审查"
        }
      ]
    : [
        {
          title: "Fragmented rules cause unstable judgments",
          desc: "CN, EU, and US cross-border regimes differ and obligation boundaries are hard to identify quickly.",
          badge: "Rules"
        },
        {
          title: "Complex materials and expensive drafting",
          desc: "From inventories to impact assessments, preparation is long and collaboration cost is high.",
          badge: "Docs"
        },
        {
          title: "Review standards drift, gaps are hard to locate",
          desc: "Many cases are not totally missing, but partial and inconsistent for regulatory review.",
          badge: "Review"
        }
      ];

  const modules = isZh
    ? [
        {
          title: "合规路径诊断",
          desc: "基于问答、规则树与事实抽取，判断应走哪条路径、为什么、下一步做什么。",
          tag: "Diagnosis"
        },
        {
          title: "报告草案生成",
          desc: "自动生成风险自评估、PIPIA、DPIA、TIA 等文书草案，保留人工复核接口。",
          tag: "Drafting"
        },
        {
          title: "合同与文件审查",
          desc: "针对隐私政策、数据处理协议、标准合同、SCC/BCR 等文件做条款级检查与修改建议。",
          tag: "Review"
        },
        {
          title: "风险整改清单",
          desc: "把发现的问题转化为可执行任务，按优先级、责任域和整改动作输出。",
          tag: "Action"
        }
      ]
    : [
        {
          title: "Compliance Route Diagnosis",
          desc: "Use Q&A, rule trees, and fact extraction to determine obligation path and next actions.",
          tag: "Diagnosis"
        },
        {
          title: "Draft Generation",
          desc: "Generate risk self-assessment, PIPIA, DPIA, and TIA drafts with human review checkpoints.",
          tag: "Drafting"
        },
        {
          title: "Contract and File Review",
          desc: "Clause-level checks for privacy policies, DPAs, standard contracts, SCC/BCR, and more.",
          tag: "Review"
        },
        {
          title: "Remediation Checklist",
          desc: "Transform findings into executable actions with prioritization and ownership hints.",
          tag: "Action"
        }
      ];

  const jurisdictionCards: JurisdictionCard[] = isZh
    ? [
        {
          code: "CN",
          name: "中国",
          points: ["安全评估路径", "标准合同路径", "个人信息出境认证", "PIPIA 与材料审查"]
        },
        {
          code: "EU",
          name: "欧盟",
          points: ["SCC / BCR 审查", "DPIA 草案生成", "TIA 草案生成", "跨境传输义务分析"]
        },
        {
          code: "US",
          name: "美国",
          points: ["14117 行政令风险识别", "CPRA 合规全景审查", "敏感数据处理义务核查", "第三方共享风险分析"]
        }
      ]
    : [
        {
          code: "CN",
          name: "China",
          points: ["Security Assessment Route", "Standard Contract Route", "PI Export Certification", "PIPIA and Material Review"]
        },
        {
          code: "EU",
          name: "European Union",
          points: ["SCC / BCR Review", "DPIA Drafting", "TIA Drafting", "Transfer Obligation Analysis"]
        },
        {
          code: "US",
          name: "United States",
          points: ["EO 14117 Screening", "CPRA Panorama Review", "Sensitive Data Duty Check", "Third-party Sharing Risk Analysis"]
        }
      ];

  const flow = isZh
    ? ["输入企业事实与业务材料", "系统抽取关键字段并匹配规则", "生成报告、矩阵与风险结论", "输出整改建议与后续动作"]
    : [
        "Input company facts and business materials",
        "Extract key fields and map rules",
        "Generate reports, matrix, and risk conclusions",
        "Output remediation and next actions"
      ];

  return (
    <section className="landing-blue-page">
      <div className="landing-blue-scroll">
        <div className="landing-blue-shell">
        <section className="landing-blue-hero-screen">
          <div className="landing-blue-hero">
          <div className="landing-blue-hero-left">
            <div className="landing-blue-chip">{isZh ? "跨境合规工作流" : "Cross-Border Compliance Workflow"}</div>
            <h1>
              {isZh ? "把复杂的跨境数据合规，" : "Turn complex data transfer compliance"}
              <br />
              {isZh ? "变成清晰、可执行的工作流" : "into a clear, executable workflow"}
            </h1>
            <p>
              {isZh
                ? "从合规路径判断、材料收集、报告草案生成，到文件审查、风险定位与整改清单输出，为企业提供一套可落地的合规辅助入口。"
                : "From route diagnosis and material prep to draft generation, document review, and remediation output, all in one execution flow."}
            </p>
            <div className="landing-blue-actions" data-guide="home-start">
              <button className="pill-btn-primary" onClick={() => navigate("/tasks")}>
                {isZh ? "进入任务空间" : "Open Task Spaces"}
              </button>
              {latestTask ? (
                <button className="pill-btn" onClick={() => navigate(`/workspace/${latestTask.id}`)}>
                  {t("homeIntroContinueAction")}
                </button>
              ) : (
                <button className="pill-btn" disabled>
                  {t("homeIntroContinueAction")}
                </button>
              )}
            </div>
            <div className="landing-blue-facts">
              <article>
                <strong>{isZh ? "3 大法域" : "3 Jurisdictions"}</strong>
                <span>{isZh ? "中国 / 欧盟 / 美国" : "CN / EU / US"}</span>
              </article>
              <article>
                <strong>{isZh ? "4 类核心能力" : "4 Core Capabilities"}</strong>
                <span>{isZh ? "诊断 / 起草 / 审查 / 整改" : "Diagnosis / Drafting / Review / Action"}</span>
              </article>
              <article>
                <strong>{isZh ? "文书与规则双驱动" : "Rules + Drafting"}</strong>
                <span>{isZh ? "不是只做问答或检索" : "More than Q&A or plain search"}</span>
              </article>
            </div>
          </div>
          <div className="landing-blue-hero-right">
            <div className="landing-blue-stats">
              <article>
                <span>{isZh ? "任务总数" : "Tasks"}</span>
                <strong>{state.taskSpaces.length}</strong>
              </article>
              <article>
                <span>{isZh ? "运行总数" : "Runs"}</span>
                <strong>{state.moduleRuns.length}</strong>
              </article>
              <article>
                <span>{isZh ? "法域覆盖" : "Jurisdictions"}</span>
                <strong>3</strong>
              </article>
            </div>
            <div className="landing-blue-preview">
              <header>
                <span>{isZh ? "Live Preview" : "Live Preview"}</span>
                <strong>{isZh ? "合规路径智能诊断" : "Compliance Route Diagnosis"}</strong>
              </header>
              <div className="landing-blue-preview-list">
                {(isZh
                  ? ["企业是否属于受规制主体？", "涉及哪些数据类型与跨境场景？", "应走哪条合规路径？", "需要生成哪些报告与补充材料？"]
                  : [
                      "Is the company a regulated entity?",
                      "What data types and scenarios are involved?",
                      "Which compliance route is applicable?",
                      "What reports and attachments are required?"
                    ]).map((q, i) => (
                  <article key={q}>
                    <small>{isZh ? `问题 ${i + 1}` : `Question ${i + 1}`}</small>
                    <p>{q}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
          </div>
        </section>

        <section id="overview" className="landing-blue-section landing-blue-screen">
          <header className="landing-blue-section-head landing-blue-center-head landing-blue-why-head">
            <span>{isZh ? "WHY AI4LAW" : "WHY AI4LAW"}</span>
            <h2>{isZh ? "不是缺少信息，而是缺少一条清楚的合规主线" : "Not a lack of information, but a missing compliance storyline"}</h2>
            <p>
              {isZh
                ? "首页不只展示功能，而是沿着用户真实思考顺序展开：先看到问题，再理解方法，最后知道如何开始。"
                : "The landing page should follow user cognition: problem first, then method, then action."}
            </p>
          </header>
          <div className="landing-blue-pain-grid landing-blue-why-grid">
            {painPoints.map((item) => (
              <article key={item.title} className="landing-blue-why-card">
                <div className="landing-blue-icon landing-blue-icon-box">{item.badge}</div>
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="modules" className="landing-blue-section landing-blue-screen">
          <header className="landing-blue-section-head landing-blue-split-head landing-blue-cap-head">
            <div>
              <span>{isZh ? "HOW IT WORKS" : "HOW IT WORKS"}</span>
              <h2>{isZh ? "一个层层下滑、逻辑递进的首页结构" : "A layered narrative homepage structure"}</h2>
            </div>
            <p>
              {isZh
                ? "参考你的目标页面，它的核心是叙事连续。这里采用同样结构，但保持 AI4Law 的法学严肃风格。"
                : "This keeps narrative continuity from your reference while adapting to AI4Law's legal tone."}
            </p>
          </header>
          <div className="landing-blue-module-grid landing-blue-cap-grid">
            {modules.map((item) => (
              <article key={item.title} className="landing-blue-cap-card">
                <span>{item.tag}</span>
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="jurisdictions" className="landing-blue-section landing-blue-screen">
          <header className="landing-blue-section-head landing-blue-split-head landing-blue-jd-head">
            <div>
              <span>{isZh ? "JURISDICTIONS" : "JURISDICTIONS"}</span>
              <h2>{isZh ? "不同法域，不同规则，同一套交互入口" : "Different regimes, one interaction framework"}</h2>
            </div>
            <p>
              {isZh
                ? "这个系统不是抽象的法律 AI，而是明确覆盖中国、欧盟、美国三类跨境数据核心场景。"
                : "This is not generic legal AI. It explicitly covers CN/EU/US transfer scenarios."}
            </p>
          </header>
          <div className="landing-blue-jurisdiction-grid landing-blue-jd-grid">
            {jurisdictionCards.map((card) => (
              <article key={card.code} className="landing-blue-jd-card">
                <div className="landing-blue-icon landing-blue-jd-icon">◎</div>
                <h3>{card.name}</h3>
                <ul>
                  {card.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>

        <section id="flow" className="landing-blue-flow landing-blue-screen">
          <div className="landing-blue-workflow-layout">
            <header className="landing-blue-section-head landing-blue-workflow-left">
              <div className="landing-blue-workflow-title">
                <span>{isZh ? "WORKFLOW" : "WORKFLOW"}</span>
                <h2>{isZh ? "最后一层，应当把复杂流程讲成清楚的四步" : "Explain complex workflow in four clear steps"}</h2>
              </div>
              <p>
                {isZh
                  ? "企业级官网不宜把流程讲得过碎。更合适的方式，是将完整工作流压缩为几个稳定、可记忆、可理解的核心阶段。"
                  : "Enterprise landing pages should compress complexity into memorable core stages."}
              </p>
            </header>
            <div className="landing-blue-flow-grid landing-blue-workflow-right">
              {flow.map((step, index) => (
                <article key={step} className="landing-blue-workflow-step">
                  <span className="landing-blue-step-id">{String(index + 1).padStart(2, "0")}</span>
                  <p>{step}</p>
                  <em aria-hidden>›</em>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-blue-footer landing-blue-screen">
          <header className="landing-blue-section-head landing-blue-center-head">
            <span>{isZh ? "NEXT STEP" : "NEXT STEP"}</span>
            <h2>{isZh ? "从介绍到执行，直接进入任务空间" : "Move from narrative to execution"}</h2>
            <p>
              {isZh
                ? "当前版本已完成结构与视觉基线，下一步可继续细化文案、图示、动画节奏与法域入口策略。"
                : "Structure and visual baseline are ready; next iteration can refine copy, visuals, and transitions."}
            </p>
          </header>
          <div className="landing-blue-actions landing-blue-footer-actions">
            <button className="pill-btn-primary" onClick={() => navigate("/tasks")}>{isZh ? "进入任务空间" : "Open Task Spaces"}</button>
            {latestTask ? (
              <button className="pill-btn" onClick={() => navigate(`/workspace/${latestTask.id}`)}>
                {t("homeIntroContinueAction")}
              </button>
            ) : (
              <button className="pill-btn" disabled>
                {t("homeIntroContinueAction")}
              </button>
            )}
          </div>
        </section>
        </div>
      </div>
    </section>
  );
}
