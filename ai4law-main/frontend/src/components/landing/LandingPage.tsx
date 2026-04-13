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
          title: "规则分散，判断容易出错",
          desc: "真正难的不是找到规则，而是迅速收敛到正确路径。",
          badge: "规则"
        },
        {
          title: "材料复杂，文书成本高",
          desc: "从清单到报告，链条长、协同重、返工频繁。",
          badge: "文书"
        },
        {
          title: "审查标准不稳定，缺口难定位",
          desc: "很多问题不是没做，而是依据不清、结论不稳。",
          badge: "审查"
        }
      ]
    : [
        {
          title: "Fragmented rules, fragile judgment",
          desc: "The challenge is not finding rules, but converging on the right path fast enough.",
          badge: "Rules"
        },
        {
          title: "Complex materials, expensive drafting",
          desc: "From inventories to reports, long chains and repeated revisions drive the real cost.",
          badge: "Docs"
        },
        {
          title: "Unstable review, hard-to-see gaps",
          desc: "The issue is rarely inaction. More often, the basis is unclear and delivery is not review-ready.",
          badge: "Review"
        }
      ];

  const modules = isZh
    ? [
        {
          title: "合规路径诊断",
          desc: "先完成适用路径判断，再决定是否进入安全评估、标准合同、认证或补充 PIPIA 材料。",
          tag: "Diagnosis"
        },
        {
          title: "报告草案生成",
          desc: "支持生成个人信息出境风险自评估、PIPIA、DPIA、TIA 等文书草案，并保留人工复核入口。",
          tag: "Drafting"
        },
        {
          title: "合同与文件审查",
          desc: "围绕隐私政策、数据处理协议、标准合同、SCC / BCR 等文件输出条款级审查意见与修改依据。",
          tag: "Review"
        },
        {
          title: "风险整改清单",
          desc: "把识别出的高风险缺口转成整改清单、补件要求和后续执行动作，直接进入交付推进。",
          tag: "Action"
        }
      ]
    : [
        {
          title: "Compliance Route Diagnosis",
          desc: "Determine the applicable route first, then decide whether the case moves into security assessment, standard contracts, certification, or supplemental PIPIA preparation.",
          tag: "Diagnosis"
        },
        {
          title: "Draft Generation",
          desc: "Generate draft deliverables such as export risk self-assessments, PIPIA, DPIA, and TIA with clear review checkpoints.",
          tag: "Drafting"
        },
        {
          title: "Contract and File Review",
          desc: "Produce clause-level review comments for privacy policies, DPAs, standard contracts, and SCC / BCR documentation.",
          tag: "Review"
        },
        {
          title: "Remediation Checklist",
          desc: "Convert high-risk findings into remediation items, missing-material requests, and execution-ready next steps.",
          tag: "Action"
        }
      ];

  const jurisdictionCards: JurisdictionCard[] = isZh
    ? [
        {
          code: "CN",
          name: "中国",
          points: ["覆盖安全评估、标准合同、认证等核心路径", "支持数据出境判断、PIPIA 及材料准备", "把中国路径判断收敛得更快、更稳"]
        },
        {
          code: "EU",
          name: "欧盟",
          points: ["覆盖 SCC / BCR / DPIA / TIA 等关键场景", "支持跨境传输义务识别与文书生成", "让欧盟项目更容易形成稳定交付"]
        },
        {
          code: "US",
          name: "美国",
          points: ["覆盖 14117、CPRA 与敏感数据处理场景", "支持第三方共享与风险识别分析", "把美国场景纳入统一执行框架"]
        }
      ]
    : [
        {
          code: "CN",
          name: "China",
          points: ["Covers security assessment, standard contracts, and certification routes", "Supports export diagnosis, PIPIA, and material preparation", "Helps teams converge on a China pathway faster and with more confidence"]
        },
        {
          code: "EU",
          name: "European Union",
          points: ["Supports SCC, BCR, DPIA, and TIA-heavy scenarios", "Connects transfer obligations with draft generation", "Makes EU transfer work easier to deliver with consistency"]
        },
        {
          code: "US",
          name: "United States",
          points: ["Covers EO 14117, CPRA, and sensitive-data handling scenarios", "Supports third-party sharing analysis and risk identification", "Brings US-facing work into the same execution framework"]
        }
      ];

  const flow = isZh
    ? ["输入业务事实与现有材料", "系统收敛合规路径与判断依据", "生成报告、审查结论与风险输出", "沉淀整改动作并继续推进"]
    : [
        "Input business facts and available materials",
        "Converge on the compliance route and supporting basis",
        "Generate reports, review outputs, and risk conclusions",
        "Turn findings into next-step actions"
      ];

  return (
    <section className="landing-blue-page">
      <div className="landing-blue-scroll">
        <div className="landing-blue-shell">
          <section className="landing-blue-hero-screen">
            <div className="landing-blue-hero">
              <div className="landing-blue-hero-left">
                <div className="landing-blue-chip">
                  {isZh ? "跨境合规工作流" : "Cross-Border Compliance Workflow"}
                </div>
                <h1>
                  {isZh ? "把复杂的跨" : "Turn complex data transfer compliance"}
                  <br />
                  {isZh ? "境数据合规，" : "into a clear, executable workflow"}
                  {isZh ? (
                    <>
                      <br />
                      变成清晰、可执行
                      <br />
                      的工作流
                    </>
                  ) : null}
                </h1>
                <p>
                  {isZh
                    ? "从路径判断到文书交付，把高成本的合规准备压缩为可复核、可推进的执行闭环。"
                    : "From route selection to report delivery, AI4Law compresses high-cost compliance work into a workflow that is reviewable and ready to move."}
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
                    <strong>{isZh ? "文书与规则双驱动" : "Rules + Deliverables"}</strong>
                    <span>{isZh ? "不止判断问题，更直接推动交付" : "More than analysis, built to move work forward"}</span>
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
                          "What data types and scenarios are involved?",
                          "Which compliance route should apply?",
                          "What reports and supporting materials are required?"
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
              <span>WHY AI4LAW</span>
              <h2>
                {isZh
                  ? "不是缺少信息，而是缺少一条清楚的合规主线"
                  : "The real gap is not information, but a clear compliance storyline"}
              </h2>
              <p>
                {isZh
                  ? "真正难的不是看见问题，而是把规则、材料和结论收敛成一条可执行、可复核、可交付的路径。"
                  : "The challenge is not seeing the problem. It is turning rules, materials, and conclusions into one path that can be executed, reviewed, and delivered."}
              </p>
            </header>
              <div className="landing-blue-pain-grid landing-blue-why-grid">
                {painPoints.map((item) => (
                  <article key={item.title} className="landing-blue-why-card">
                    <div className="landing-blue-why-card-head">
                      <div
                        className={`landing-blue-icon landing-blue-icon-box ${
                          item.badge === (isZh ? "规则" : "Rules")
                            ? "is-rules"
                            : item.badge === (isZh ? "文书" : "Docs")
                              ? "is-docs"
                              : "is-review"
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
                <h2>
                  {isZh
                    ? "一个层层下滑、逻辑递进的首页结构"
                    : "A layered narrative homepage structure"}
                </h2>
              </div>
              <p>
                {isZh
                  ? "核心价值不在模块堆叠，而在于把路径诊断、PIPIA / DPIA / TIA 草案、SCC / BCR 审查与整改推进连成一条工作流。"
                  : "The value is not in stacking modules, but in connecting route diagnosis, PIPIA / DPIA / TIA drafting, SCC / BCR review, and remediation into one workflow."}
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
                <h2>
                  {isZh
                    ? "不同法域，不同规则，同一套交互入口"
                    : "Different regimes, one interaction framework"}
                </h2>
              </div>
              <p>
                {isZh
                  ? "面向中国、欧盟、美国的核心跨境场景提供结构化入口，让团队在不同法域下都能沿统一方法推进判断与交付。"
                  : "Structured entry points for China, the EU, and the US keep teams on one consistent method across jurisdictions."}
              </p>
            </header>
            <div className="landing-blue-jurisdiction-grid landing-blue-jd-grid">
              {jurisdictionCards.map((card) => (
                <article key={card.code} className="landing-blue-jd-card">
                  <div className="landing-blue-icon landing-blue-jd-icon">●</div>
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
                      : "Explain complex workflow in four clear steps"}
                  </h2>
                </div>
                <p>
                  {isZh
                    ? "首页不必讲完所有细节，但必须让用户迅速明白从哪里开始、如何推进、最后得到什么。"
                    : "A strong landing page does not explain everything. It makes the starting point, path, and outcome clear at a glance."}
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

          <section className="landing-blue-footer landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-center-head">
              <span>NEXT STEP</span>
              <h2>
                {isZh
                  ? "从介绍到执行，直接进入任务空间"
                  : "Move from narrative to execution"}
              </h2>
              <p>
                {isZh
                  ? "当路径、材料和目标开始收敛，真正有价值的下一步，就是把判断推进为结果。"
                  : "Once the path, materials, and goal are aligned, the next valuable move is to turn judgment into results."}
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
