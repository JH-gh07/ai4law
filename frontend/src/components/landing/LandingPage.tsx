import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { OpenQuestModal } from "../modals/OpenQuestModal";
import { useAppStore } from "../../lib/app-store";
import { useLang } from "../../lib/language";
import type { Jurisdiction, LaunchMode } from "../../lib/domain";
import { FlagCN, FlagEU, FlagUS } from "../common/AppIcons";

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

const flagMap = {
  CN: FlagCN,
  EU: FlagEU,
  US: FlagUS
} as const;

export function LandingPage({ onStart: _onStart, onQuickCreate: _onQuickCreate }: LandingPageProps) {
  const { lang, t } = useLang();
  const navigate = useNavigate();
  const { state } = useAppStore();
  const isZh = lang === "zh";
  const [openQuestModalOpen, setOpenQuestModalOpen] = useState(false);
  const [openQuestQuery, setOpenQuestQuery] = useState("");

  const painPoints = isZh
    ? [
        {
          title: "规则多源分散，路径判断成本高",
          desc: "难点不在于能否查到法规，而在于能否迅速把规则、场景和材料收敛到正确路径。",
          badge: "规则"
        },
        {
          title: "文书准备链条长，交付反复返工",
          desc: "从清单、附件到 PIPIA、DPIA、TIA、SCC 审查报告，真正消耗的是准备与复核成本。",
          badge: "文书"
        },
        {
          title: "审查依据不稳，问题难以说服团队",
          desc: "很多问题不是没有发现，而是依据不清、定位不准、修改意见难以进入执行闭环。",
          badge: "审查"
        }
      ]
    : [
        {
          title: "Fragmented rules make route decisions expensive",
          desc: "The real challenge is converging rules, business facts, and materials into the right route quickly.",
          badge: "Rules"
        },
        {
          title: "Document preparation is long and revision-heavy",
          desc: "Across PIPIA, DPIA, TIA, SCC review, and supporting materials, preparation and review drive the cost.",
          badge: "Docs"
        },
        {
          title: "Review basis is unstable and hard to align on",
          desc: "Issues are often found, but unclear basis and weak positioning prevent execution-ready remediation.",
          badge: "Review"
        }
      ];

  const modules = isZh
    ? [
        {
          title: "合规路径诊断",
          desc: "先完成适用路径判断，再决定是否进入安全评估、标准合同/认证、PIPIA 补充或豁免处理。",
          tag: "Diagnosis"
        },
        {
          title: "文书草案生成",
          desc: "支持数据出境风险自评估报告、PIPIA、DPIA、TIA 等草案生成，保留后续复核与补件空间。",
          tag: "Drafting"
        },
        {
          title: "合同与制度审查",
          desc: "围绕隐私政策、DPA、标准合同、SCC/BCR 等文本输出条款级审查意见与修改依据。",
          tag: "Review"
        },
        {
          title: "整改与交付推进",
          desc: "把高风险发现转成整改清单、补件要求和执行动作，推动团队真正进入交付状态。",
          tag: "Action"
        }
      ]
    : [
        {
          title: "Compliance Route Diagnosis",
          desc: "Determine the applicable route before moving into security assessment, SCC/certification, PIPIA supplements, or exemptions.",
          tag: "Diagnosis"
        },
        {
          title: "Draft Generation",
          desc: "Generate export risk self-assessments, PIPIA, DPIA, and TIA drafts with room for review and evidence completion.",
          tag: "Drafting"
        },
        {
          title: "Contract and Governance Review",
          desc: "Deliver clause-level review findings for privacy policies, DPAs, standard contracts, and SCC/BCR documentation.",
          tag: "Review"
        },
        {
          title: "Remediation and Delivery",
          desc: "Convert high-risk findings into remediation items, requests for missing inputs, and execution-ready handoff actions.",
          tag: "Action"
        }
      ];

  const jurisdictionCards: JurisdictionCard[] = isZh
    ? [
        {
          code: "CN",
          name: "中国",
          points: ["覆盖安全评估、标准合同、认证等核心路径", "支持路径诊断、PIPIA 及申报材料准备", "更快形成中国法域下的稳定交付口径"]
        },
        {
          code: "EU",
          name: "欧盟",
          points: ["覆盖 SCC、BCR、DPIA、TIA 等关键专题", "把跨境传输义务与文书生成、审查连接起来", "让欧盟任务更容易形成一致交付"]
        },
        {
          code: "US",
          name: "美国",
          points: ["覆盖 EO 14117、CPRA 与敏感数据流动场景", "支持接收方、共享链路与限制性风险识别", "把美国专题纳入统一工作区与交付框架"]
        }
      ]
    : [
        {
          code: "CN",
          name: "China",
          points: ["Covers security assessment, SCC filing, and certification routes", "Supports diagnosis, PIPIA, and filing-material preparation", "Improves delivery consistency for China-focused work"]
        },
        {
          code: "EU",
          name: "European Union",
          points: ["Covers SCC, BCR, DPIA, and TIA topics", "Connects transfer obligations with drafting and review", "Makes EU transfer work easier to deliver consistently"]
        },
        {
          code: "US",
          name: "United States",
          points: ["Covers EO 14117, CPRA, and sensitive-data transfer topics", "Supports recipient, sharing-chain, and restricted-risk analysis", "Brings US-facing work into the same execution framework"]
        }
      ];

  const flow = isZh
    ? ["输入业务事实与现有材料", "系统收敛合规路径与判断依据", "生成报告、审查结论与风险输出", "沉淀整改动作并持续推进"]
    : [
        "Input business facts and available materials",
        "Converge on route and supporting basis",
        "Generate reports, review conclusions, and risk outputs",
        "Turn findings into next-step actions"
      ];

  return (
    <section className="landing-blue-page">
      <div className="landing-blue-scroll">
        <div className="landing-blue-shell">
          <section className="landing-blue-hero-screen">
            <div className="landing-blue-hero">
              <div className="landing-blue-hero-left">
                <div className="landing-blue-chip">{isZh ? "跨境数据合规工作流" : "Cross-Border Data Compliance Workflow"}</div>
                <h1 className="landing-brand-headline">
                  数规通
                  <span>DataComply Flow</span>
                </h1>
                <p className="landing-brand-subtitle">
                  AI驱动的数据跨境合规诊断与文书智能生成平台
                </p>
                <p>
                  {isZh
                    ? "把路径判断、材料准备、文书草案、合同审查和整改推进收敛到同一条可复核、可执行、可交付的工作流。"
                    : "Bring route decisions, material preparation, legal drafting, document review, and remediation into one reviewable workflow."}
                </p>
                <div className="landing-blue-actions" data-guide="home-start">
                  <button className="pill-btn-primary" onClick={() => navigate("/tasks")}>
                    {isZh ? "进入任务空间" : "Open Task Spaces"}
                  </button>
                  <button
                    className="pill-btn quest-open-btn"
                    onClick={() => {
                      setOpenQuestQuery("");
                      setOpenQuestModalOpen(true);
                    }}
                  >
                    {t("homeIntroContinueAction")}
                  </button>
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
                    <strong>{isZh ? "结果导向交付" : "Delivery-Oriented"}</strong>
                    <span>{isZh ? "从判断走向文书、报告与修订成果" : "From judgment to reports, drafts, and revision-ready outputs"}</span>
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
                    <span>LIVE PREVIEW</span>
                    <strong>{isZh ? "合规路径智能诊断" : "Compliance Route Diagnosis"}</strong>
                  </header>
                  <div className="landing-blue-preview-list">
                    {(isZh
                      ? [
                          "企业是否属于受规制主体？",
                          "涉及哪些数据类型与跨境场景？",
                          "应走哪条合规路径？",
                          "需要生成哪些报告与补充材料？"
                        ]
                      : [
                          "Is the company a regulated entity?",
                          "What data types and transfer scenarios are involved?",
                          "Which compliance route should apply?",
                          "What reports and materials are required next?"
                        ]).map((item, index) => (
                      <article key={item}>
                        <small>{isZh ? `问题 ${index + 1}` : `Question ${index + 1}`}</small>
                        <p>{item}</p>
                      </article>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section id="overview" className="landing-blue-section landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-center-head landing-blue-why-head">
              <span>WHY DATACOMPLY FLOW</span>
              <h2>{isZh ? "不是缺少信息，而是缺少一条清晰、可执行的合规主线" : "The real gap is not information, but an executable compliance storyline"}</h2>
              <p>
                {isZh
                  ? "企业真正难的不是找到规则，而是把规则、材料和判断依据收敛成一条能被团队持续推进的路径。"
                  : "The difficult part is not finding the rules. It is aligning materials, reasoning, and delivery into one path teams can actually execute."}
              </p>
            </header>
            <div className="landing-blue-pain-grid landing-blue-why-grid">
              {painPoints.map((item) => (
                <article key={item.title} className="landing-blue-why-card">
                  <div className="landing-blue-why-card-head">
                    <div
                      className={`landing-blue-icon landing-blue-icon-box ${
                        item.badge === (isZh ? "规则" : "Rules") ? "is-rules" : item.badge === (isZh ? "文书" : "Docs") ? "is-docs" : "is-review"
                      }`}
                      aria-hidden="true"
                    >
                      <span />
                      <span />
                      <span />
                    </div>
                    <h3>{item.title}</h3>
                  </div>
                  <p>{item.desc}</p>
                </article>
              ))}
            </div>
          </section>

          <section id="modules" className="landing-blue-section landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-split-head landing-blue-cap-head">
              <div>
                <span>HOW IT WORKS</span>
                <h2>{isZh ? "把判断、草案、审查与整改串成同一条工作流" : "Connect diagnosis, drafting, review, and remediation into one workflow"}</h2>
              </div>
              <p>
                {isZh
                  ? "核心价值不在于堆叠模块，而在于让 PIPIA、DPIA、TIA、SCC/BCR 审查和整改推进在同一框架下协同。"
                  : "The value is not in stacking modules, but in orchestrating PIPIA, DPIA, TIA, SCC/BCR review, and remediation within one framework."}
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
                <span>JURISDICTIONS</span>
                <h2>{isZh ? "中国、欧盟、美国，统一进入同一套工作区方法" : "China, EU, and US work within one execution model"}</h2>
              </div>
              <p>
                {isZh
                  ? "不同法域下的专题任务可以保持统一的进入方式、运行方式和交付方式。"
                  : "Different legal regimes still share one interaction, execution, and delivery framework."}
              </p>
            </header>
            <div className="landing-blue-jurisdiction-grid landing-blue-jd-grid">
              {jurisdictionCards.map((card) => {
                const Flag = flagMap[card.code];
                return (
                  <article key={card.code} className="landing-blue-jd-card">
                    <div className="landing-blue-jd-flag">
                      <Flag width="54" height="36" />
                    </div>
                    <h3>{card.name}</h3>
                    <ul>
                      {card.points.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  </article>
                );
              })}
            </div>
          </section>

          <section id="flow" className="landing-blue-flow landing-blue-screen">
            <div className="landing-blue-workflow-layout">
              <header className="landing-blue-section-head landing-blue-workflow-left">
                <div className="landing-blue-workflow-title">
                  <span>WORKFLOW</span>
                  <h2>{isZh ? "让复杂流程在首页就能被理解成四个清晰动作" : "Turn a complex flow into four clear actions"}</h2>
                </div>
                <p>
                  {isZh
                    ? "首页不必讲完所有细节，但必须让用户立刻知道从哪里开始、如何推进、最终得到什么。"
                    : "A strong landing page does not explain everything. It makes the starting point, path, and outcome immediately clear."}
                </p>
              </header>
              <div className="landing-blue-flow-grid landing-blue-workflow-right">
                {flow.map((step, index) => (
                  <article key={step} className="landing-blue-workflow-step">
                    <span className="landing-blue-step-id">{String(index + 1).padStart(2, "0")}</span>
                    <p>{step}</p>
                    <em aria-hidden>→</em>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>

      {openQuestModalOpen ? (
        <OpenQuestModal
          tasks={state.taskSpaces}
          runs={state.moduleRuns}
          query={openQuestQuery}
          onQueryChange={setOpenQuestQuery}
          onClose={() => setOpenQuestModalOpen(false)}
          onOpenTask={(taskId) => {
            setOpenQuestModalOpen(false);
            navigate(`/workspace/${taskId}`);
          }}
        />
      ) : null}
    </section>
  );
}
