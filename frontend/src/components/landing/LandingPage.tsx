import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { OpenQuestModal } from "../modals/OpenQuestModal";
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

type CopyBlock = {
  painPoints: { title: string; desc: string; badge: string }[];
  modules: { title: string; desc: string; tag: string }[];
  jurisdictions: JurisdictionCard[];
  flow: string[];
  previewQuestions: string[];
};

export function LandingPage({ onStart: _onStart, onQuickCreate: _onQuickCreate }: LandingPageProps) {
  const { lang, t } = useLang();
  const navigate = useNavigate();
  const { state } = useAppStore();
  const isZh = lang === "zh";
  const [openQuestModalOpen, setOpenQuestModalOpen] = useState(false);
  const [openQuestQuery, setOpenQuestQuery] = useState("");

  const heroBrandTitle = isZh ? "数规通" : "DATACOMPLY FLOW";
  const heroBrandSub = isZh ? "DataComply Flow" : "";
  const heroTagline = isZh
    ? "AI驱动的数据跨境合规诊断与文书智能生成平台"
    : "AI-Driven Platform for Cross-Border Data Compliance Diagnosis and Intelligent Document Generation";

  const copy: CopyBlock = isZh
    ? {
        painPoints: [
          {
            title: "规则分散，路径判断成本高",
            desc: "真正难的不是找到法条，而是把规则、场景和材料快速收敛到正确路径。",
            badge: "规则"
          },
          {
            title: "材料繁杂，文书准备链条长",
            desc: "从数据清单到 PIPIA、DPIA、TIA 与 SCC 审查，准备和复核往往最耗时间。",
            badge: "文书"
          },
          {
            title: "审查依据不稳，整改难推进",
            desc: "很多问题不是没发现，而是依据不清、定位不准，难以形成可执行结论。",
            badge: "审查"
          }
        ],
        modules: [
          {
            title: "合规路径诊断",
            desc: "先判断适用路径，再决定是否进入安全评估、标准合同、认证、PIPIA 或豁免处理。",
            tag: "Diagnosis"
          },
          {
            title: "文书草案生成",
            desc: "支持数据出境风险自评、PIPIA、DPIA、TIA 等草案生成，并保留后续复核空间。",
            tag: "Drafting"
          },
          {
            title: "合同与文书审查",
            desc: "围绕隐私政策、DPA、标准合同、SCC/BCR 等文本输出条款级审查意见与修改依据。",
            tag: "Review"
          },
          {
            title: "整改与交付推进",
            desc: "把高风险发现沉淀为整改清单、补件要求与下一步动作，推动团队进入交付状态。",
            tag: "Action"
          }
        ],
        jurisdictions: [
          {
            code: "CN",
            name: "中国",
            points: ["安全评估路径", "标准合同路径", "认证路径", "PIPIA 与申报材料准备"]
          },
          {
            code: "EU",
            name: "欧盟",
            points: ["SCC / BCR 审查", "DPIA 草案生成", "TIA 草案生成", "跨境传输义务分析"]
          },
          {
            code: "US",
            name: "美国",
            points: ["EO 14117 风险识别", "CPRA 合规核查", "敏感数据处理义务", "第三方共享风险分析"]
          }
        ],
        flow: [
          "输入业务事实与现有材料",
          "系统收敛合规路径与判断依据",
          "生成报告、审查结论与风险输出",
          "沉淀整改动作并持续推进"
        ],
        previewQuestions: [
          "企业是否属于受规制主体？",
          "涉及哪些数据类型与跨境场景？",
          "应走哪条合规路径？",
          "还需要哪些报告与补充材料？"
        ]
      }
    : {
        painPoints: [
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
        ],
        modules: [
          {
            title: "Compliance Route Diagnosis",
            desc: "Determine the applicable route before moving into security assessment, SCC or certification, PIPIA supplements, or exemptions.",
            tag: "Diagnosis"
          },
          {
            title: "Draft Generation",
            desc: "Generate export risk self-assessments, PIPIA, DPIA, and TIA drafts with room for review and evidence completion.",
            tag: "Drafting"
          },
          {
            title: "Contract and Document Review",
            desc: "Deliver clause-level review findings for privacy policies, DPAs, standard contracts, and SCC/BCR documentation.",
            tag: "Review"
          },
          {
            title: "Remediation and Delivery",
            desc: "Convert high-risk findings into remediation items, requests for missing inputs, and execution-ready handoff actions.",
            tag: "Action"
          }
        ],
        jurisdictions: [
          {
            code: "CN",
            name: "China",
            points: ["Security Assessment Route", "Standard Contract Route", "Certification Route", "PIPIA and filing-material prep"]
          },
          {
            code: "EU",
            name: "European Union",
            points: ["SCC / BCR Review", "DPIA Drafting", "TIA Drafting", "Transfer Obligation Analysis"]
          },
          {
            code: "US",
            name: "United States",
            points: ["EO 14117 Screening", "CPRA Review", "Sensitive Data Duty Check", "Third-Party Sharing Risk Analysis"]
          }
        ],
        flow: [
          "Input business facts and available materials",
          "Converge on route and supporting basis",
          "Generate reports, review conclusions, and risk outputs",
          "Turn findings into next-step actions"
        ],
        previewQuestions: [
          "Is the company a regulated entity?",
          "What data types and transfer scenarios are involved?",
          "Which compliance route should apply?",
          "What reports and materials are required next?"
        ]
      };

  return (
    <section className="landing-blue-page">
      <div className="landing-blue-scroll">
        <div className="landing-blue-shell">
          <section className="landing-blue-hero-screen">
            <div className="landing-blue-hero">
              <div className="landing-blue-hero-left">
                <h1 className="landing-brand-headline">
                  {heroBrandTitle}
                  {heroBrandSub ? <span>{heroBrandSub}</span> : null}
                </h1>
                <p className="landing-brand-subtitle">{heroTagline}</p>
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
                    <span>
                      {isZh ? "从判断走向文书、报告与修订成果" : "From judgment to reports, drafts, and revision-ready outputs"}
                    </span>
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
                </div>
                <div className="landing-blue-preview">
                  <header>
                    <span>LIVE PREVIEW</span>
                    <strong>{isZh ? "合规路径智能诊断" : "Compliance Route Diagnosis"}</strong>
                  </header>
                  <div className="landing-blue-preview-list">
                    {copy.previewQuestions.map((item, index) => (
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
              <h2>
                {isZh
                  ? "不是缺少信息，而是缺少一条清晰、可执行的合规主线"
                  : "The real gap is not information, but an executable compliance storyline"}
              </h2>
            </header>
            <div className="landing-blue-pain-grid landing-blue-why-grid">
              {copy.painPoints.map((item, index) => {
                const iconClass = index === 0 ? "is-rules" : index === 1 ? "is-docs" : "is-review";
                return (
                <article key={item.title} className="landing-blue-why-card">
                  <div className={`landing-blue-icon landing-blue-icon-box ${iconClass}`}>
                    <span />
                    <span />
                    <span />
                  </div>
                  <h3>{item.title}</h3>
                  <p>{item.desc}</p>
                </article>
                );
              })}
            </div>
          </section>

          <section id="modules" className="landing-blue-section landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-split-head landing-blue-cap-head">
              <div>
                <span>HOW IT WORKS</span>
                <h2>
                  {isZh
                    ? "把诊断、草案、审查与整改串成同一条工作流"
                    : "Connect diagnosis, drafting, review, and remediation into one workflow"}
                </h2>
              </div>
              <p>
                {isZh
                  ? "核心价值不在于模块堆叠，而在于让 PIPIA、DPIA、TIA、SCC/BCR 审查与整改推进在同一框架下协同。"
                  : "The value is not in stacking modules, but in orchestrating PIPIA, DPIA, TIA, SCC/BCR review, and remediation within one framework."}
              </p>
            </header>
            <div className="landing-blue-module-grid landing-blue-cap-grid">
              {copy.modules.map((item) => (
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
                <h2>
                  {isZh
                    ? "中国、欧盟、美国，统一进入同一套工作区方法"
                    : "China, the EU, and the US operate within one execution model"}
                </h2>
              </div>
              <p>
                {isZh
                  ? "不是泛化法律问答，而是围绕具体法域任务，把路径、文书、审查与整改放进同一交付框架。"
                  : "This is not generic legal chat. It brings route selection, drafting, review, and remediation into one delivery framework for specific jurisdictions."}
              </p>
            </header>
            <div className="landing-blue-jurisdiction-grid landing-blue-jd-grid">
              {copy.jurisdictions.map((card) => (
                <article key={card.code} className="landing-blue-jd-card">
                  <div className="landing-blue-icon landing-blue-jd-icon">{card.code}</div>
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
                  <span>WORKFLOW</span>
                  <h2>
                    {isZh
                      ? "最后一层，应当把复杂流程讲成清楚的四步"
                      : "Turn a complex workflow into four clear steps"}
                  </h2>
                </div>
                <p>
                  {isZh
                    ? "首页不必讲完所有细节，但必须让用户迅速知道从哪里开始、如何推进、最终得到什么。"
                    : "The landing page does not need every detail. It should make clear where to start, how to proceed, and what gets delivered."}
                </p>
              </header>
              <div className="landing-blue-flow-grid landing-blue-workflow-right">
                {copy.flow.map((step, index) => (
                  <article key={step} className="landing-blue-workflow-step">
                    <span className="landing-blue-step-id">{String(index + 1).padStart(2, "0")}</span>
                    <p>{step}</p>
                    <em aria-hidden>→</em>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="landing-blue-footer landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-center-head">
              <span>NEXT STEP</span>
              <h2>{isZh ? "从介绍到执行，直接进入任务空间" : "Move from narrative to execution"}</h2>
              <p>
                {isZh
                  ? "当用户已经理解工作流，就不该停在介绍页，而应直接进入可执行任务。"
                  : "Once the workflow is understood, the next action should be to enter an executable task space."}
              </p>
            </header>
            <div className="landing-blue-actions landing-blue-footer-actions">
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
