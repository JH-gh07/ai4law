import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { OpenQuestModal } from "../modals/OpenQuestModal";
import { useAppStore } from "../../lib/app-store";
import { useAuth } from "../../lib/auth/AuthContext";
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
};

function JurisdictionFlag({ code }: { code: Jurisdiction }) {
  if (code === "CN") {
    return (
      <svg viewBox="0 0 36 24" aria-hidden="true">
        <rect width="36" height="24" rx="3" fill="#de2910" />
        <path d="M7.2 3.1l0.79 2.41h2.53l-2.05 1.49 0.78 2.41-2.05-1.49-2.05 1.49 0.78-2.41-2.05-1.49h2.53z" fill="#ffde00" />
        <path d="M12.7 2.84l0.31 0.96h1.01l-0.82 0.59 0.32 0.96-0.82-0.6-0.82 0.6 0.31-0.96-0.82-0.59h1.01z" fill="#ffde00" transform="rotate(22 12.7 4.2)" />
        <path d="M15.14 5.26l0.31 0.96h1.01l-0.82 0.59 0.31 0.96-0.81-0.6-0.82 0.6 0.31-0.96-0.82-0.59h1.01z" fill="#ffde00" transform="rotate(45 15.14 6.62)" />
        <path d="M15.05 9.22l0.31 0.96h1.01l-0.82 0.59 0.31 0.96-0.81-0.6-0.82 0.6 0.31-0.96-0.82-0.59h1.01z" fill="#ffde00" transform="rotate(8 15.05 10.58)" />
        <path d="M12.43 11.86l0.31 0.96h1.01l-0.82 0.6 0.31 0.95-0.81-0.59-0.82 0.59 0.31-0.95-0.82-0.6h1.01z" fill="#ffde00" transform="rotate(28 12.43 13.22)" />
      </svg>
    );
  }

  if (code === "EU") {
    return (
      <svg viewBox="0 0 36 24" aria-hidden="true">
        <rect width="36" height="24" rx="3" fill="#003399" />
        <g fill="#ffcc00">
          <circle cx="18" cy="5" r="1.1" />
          <circle cx="21.8" cy="6" r="1.1" />
          <circle cx="24.5" cy="9" r="1.1" />
          <circle cx="25" cy="12" r="1.1" />
          <circle cx="24.5" cy="15" r="1.1" />
          <circle cx="21.8" cy="18" r="1.1" />
          <circle cx="18" cy="19" r="1.1" />
          <circle cx="14.2" cy="18" r="1.1" />
          <circle cx="11.5" cy="15" r="1.1" />
          <circle cx="11" cy="12" r="1.1" />
          <circle cx="11.5" cy="9" r="1.1" />
          <circle cx="14.2" cy="6" r="1.1" />
        </g>
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 36 24" aria-hidden="true">
      <rect width="36" height="24" rx="3" fill="#b22234" />
      <rect y="2" width="36" height="2" fill="#ffffff" />
      <rect y="6" width="36" height="2" fill="#ffffff" />
      <rect y="10" width="36" height="2" fill="#ffffff" />
      <rect y="14" width="36" height="2" fill="#ffffff" />
      <rect y="18" width="36" height="2" fill="#ffffff" />
      <rect y="22" width="36" height="2" fill="#ffffff" />
      <rect width="15.2" height="12.5" rx="2" fill="#3c3b6e" />
      <g fill="#ffffff">
        <circle cx="3" cy="2.5" r="0.55" />
        <circle cx="6" cy="2.5" r="0.55" />
        <circle cx="9" cy="2.5" r="0.55" />
        <circle cx="12" cy="2.5" r="0.55" />
        <circle cx="4.5" cy="4.5" r="0.55" />
        <circle cx="7.5" cy="4.5" r="0.55" />
        <circle cx="10.5" cy="4.5" r="0.55" />
        <circle cx="3" cy="6.5" r="0.55" />
        <circle cx="6" cy="6.5" r="0.55" />
        <circle cx="9" cy="6.5" r="0.55" />
        <circle cx="12" cy="6.5" r="0.55" />
        <circle cx="4.5" cy="8.5" r="0.55" />
        <circle cx="7.5" cy="8.5" r="0.55" />
        <circle cx="10.5" cy="8.5" r="0.55" />
        <circle cx="3" cy="10.5" r="0.55" />
        <circle cx="6" cy="10.5" r="0.55" />
        <circle cx="9" cy="10.5" r="0.55" />
        <circle cx="12" cy="10.5" r="0.55" />
      </g>
    </svg>
  );
}

export function LandingPage({ onStart: _onStart, onQuickCreate: _onQuickCreate }: LandingPageProps) {
  const { lang, t } = useLang();
  const { isAuthenticated } = useAuth();
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
            desc: "真正难的不是找到法条，而是把规则、场景和材料快速收敛到正确路径",
            badge: "规则"
          },
          {
            title: "材料繁杂，文书准备链条长",
            desc: "从数据清单到 PIPIA、DPIA、TIA 与 SCC 审查，准备和复核往往最耗时间",
            badge: "文书"
          },
          {
            title: "审查依据不稳，整改难推进",
            desc: "很多问题不是没发现，而是依据不清、定位不准，难以形成可执行结论",
            badge: "审查"
          }
        ],
        modules: [
          {
            title: "合规路径诊断",
            desc: "先判断适用路径，再决定是否进入安全评估、标准合同、认证、PIPIA 或豁免处理",
            tag: "Diagnosis"
          },
          {
            title: "文书草案生成",
            desc: "支持数据出境风险自评、PIPIA、DPIA、TIA 等草案生成，并保留后续复核空间",
            tag: "Drafting"
          },
          {
            title: "合同与文书审查",
            desc: "围绕隐私政策、DPA、标准合同、SCC/BCR 等文本输出条款级审查意见与修改依据",
            tag: "Review"
          },
          {
            title: "整改与交付推进",
            desc: "把高风险发现沉淀为整改清单、补件要求与下一步动作，推动团队进入交付状态",
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
        ]
      }
    : {
        painPoints: [
          {
            title: "Fragmented rules make route decisions expensive",
            desc: "The real challenge is converging rules, business facts, and materials into the right route quickly",
            badge: "Rules"
          },
          {
            title: "Document preparation is long and revision-heavy",
            desc: "Across PIPIA, DPIA, TIA, SCC review, and supporting materials, preparation and review drive the cost",
            badge: "Docs"
          },
          {
            title: "Review basis is unstable and hard to align on",
            desc: "Issues are often found, but unclear basis and weak positioning prevent execution-ready remediation",
            badge: "Review"
          }
        ],
        modules: [
          {
            title: "Compliance Route Diagnosis",
            desc: "Determine the applicable route before moving into security assessment, SCC or certification, PIPIA supplements, or exemptions",
            tag: "Diagnosis"
          },
          {
            title: "Draft Generation",
            desc: "Generate export risk self-assessments, PIPIA, DPIA, and TIA drafts with room for review and evidence completion",
            tag: "Drafting"
          },
          {
            title: "Contract and Document Review",
            desc: "Deliver clause-level review findings for privacy policies, DPAs, standard contracts, and SCC/BCR documentation",
            tag: "Review"
          },
          {
            title: "Remediation and Delivery",
            desc: "Convert high-risk findings into remediation items, requests for missing inputs, and execution-ready handoff actions",
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
        ]
      };

  const navigateWithAuth = (targetPath: string) => {
    if (isAuthenticated) {
      navigate(targetPath);
      return;
    }
    navigate(`/login?redirect=${encodeURIComponent(targetPath)}`);
  };

  return (
    <section className="landing-blue-page">
      <div className="landing-blue-scroll">
        <div className="landing-blue-shell">
          <section className="landing-blue-hero-screen">
            <div className="landing-blue-hero landing-blue-hero-video-mode">
              <video
                className="landing-blue-hero-video-bg"
                src="/media/homepage.mp4"
                autoPlay
                muted
                loop
                playsInline
                preload="metadata"
              />
              <div className="landing-blue-hero-layer landing-blue-hero-layer-brand" />
              <div className="landing-blue-hero-content">
                <div className="landing-blue-hero-left">
                  <h1 className="landing-brand-headline">
                    {heroBrandTitle}
                    {heroBrandSub ? <span>{heroBrandSub}</span> : null}
                  </h1>
                  <p className="landing-brand-subtitle">{heroTagline}</p>
                  <div className="landing-blue-actions" data-guide="home-start">
                    <button className="pill-btn-primary" onClick={() => navigateWithAuth("/tasks")}>
                      {isZh ? "进入任务空间" : "Open Task Spaces"}
                    </button>
                    <button
                      className="pill-btn quest-open-btn"
                      onClick={() => {
                        if (!isAuthenticated) {
                          navigateWithAuth("/tasks");
                          return;
                        }
                        setOpenQuestQuery("");
                        setOpenQuestModalOpen(true);
                      }}
                    >
                      {t("homeIntroContinueAction")}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section id="overview" className="landing-blue-section landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-center-head landing-blue-why-head">
              <span>WHY DATACOMPLY FLOW</span>
              <h2 className={`landing-blue-why-copy ${isZh ? "is-zh" : "is-en"}`}>
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
            </header>
            <div className="landing-blue-timeline">
              <div className="landing-blue-timeline-axis" />
              {copy.modules.map((item, index) => (
                <div key={item.title} className={`landing-blue-timeline-step step-${index + 1}`}>
                  <div className="landing-blue-timeline-card">
                    <span className="landing-blue-timeline-seq">{String(index + 1).padStart(2, "0")}</span>
                    <span className="landing-blue-timeline-tag">{item.tag}</span>
                    <h3>{item.title}</h3>
                    <p>{item.desc}</p>
                  </div>
                  <div className="landing-blue-timeline-node">
                    <span className="landing-blue-timeline-dot" />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section id="jurisdictions" className="landing-blue-section landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-center-head landing-blue-jd-head">
              <div>
                <span>JURISDICTIONS</span>
                <h2>
                  {isZh
                    ? "中国、欧盟、美国，统一进入同一套工作区方法"
                    : "China, the EU, and the US operate within one execution model"}
                </h2>
              </div>
            </header>
            <div className="landing-blue-jurisdiction-grid landing-blue-jd-grid">
              {copy.jurisdictions.map((card) => (
                <article key={card.code} className="landing-blue-jd-card">
                  <div className="landing-blue-icon landing-blue-jd-icon">
                    <JurisdictionFlag code={card.code} />
                  </div>
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

          <section className="landing-blue-footer landing-blue-screen">
            <header className="landing-blue-section-head landing-blue-center-head">
              <span>NEXT STEP</span>
              <h2>{isZh ? "从介绍到执行，直接进入任务空间" : "Move from narrative to execution"}</h2>
            </header>
            <div className="landing-blue-actions landing-blue-footer-actions">
              <button className="pill-btn-primary" onClick={() => navigateWithAuth("/tasks")}>
                {isZh ? "进入任务空间" : "Open Task Spaces"}
              </button>
              <button
                className="pill-btn quest-open-btn"
                onClick={() => {
                  if (!isAuthenticated) {
                    navigateWithAuth("/tasks");
                    return;
                  }
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
