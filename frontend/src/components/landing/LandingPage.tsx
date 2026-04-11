import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../../lib/app-store";
import { useLang } from "../../lib/language";
import type { Jurisdiction, LaunchMode } from "../../lib/domain";
import {
  buildSuggestedTaskName,
  findTaskTemplate,
  getTaskTemplateInputHint,
  getTaskTemplateOutputHint,
  getTaskTemplateTitle,
  listTaskTemplatesByJurisdiction
} from "../../lib/task-templates";

type LandingPageProps = {
  onStart: () => void;
  onQuickCreate: (config: {
    mode: LaunchMode;
    name: string;
    jurisdiction: Jurisdiction;
    taskTemplateId: string;
  }) => void;
};

export function LandingPage({ onStart, onQuickCreate }: LandingPageProps) {
  const { t, lang } = useLang();
  const navigate = useNavigate();
  const { state } = useAppStore();
  const isZh = lang === "zh";

  const recentTasks = useMemo(
    () => [...state.taskSpaces].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1)),
    [state.taskSpaces]
  );

  const latestTask = recentTasks[0] ?? null;
  const featureTags = [
    t("homeResetFeatureTag1"),
    t("homeResetFeatureTag2"),
    t("homeResetFeatureTag3"),
    t("homeResetFeatureTag4"),
    t("homeResetFeatureTag5"),
    t("homeResetFeatureTag6")
  ];
  const advantageItems = [
    t("homeResetAdvantageItem1"),
    t("homeResetAdvantageItem2"),
    t("homeResetAdvantageItem3"),
    t("homeResetAdvantageItem4"),
    t("homeResetAdvantageItem5")
  ];
  const trustItems = [
    t("homeResetTrustItem1"),
    t("homeResetTrustItem2"),
    t("homeResetTrustItem3"),
    t("homeResetTrustItem4")
  ];
  const caseItems = [
    t("homeResetCaseItem1"),
    t("homeResetCaseItem2"),
    t("homeResetCaseItem3"),
    t("homeResetCaseItem4")
  ];
  const jurisdictionColumns = [
    { code: "CN" as const, title: isZh ? "中国（CN）" : "China (CN)" },
    { code: "EU" as const, title: isZh ? "欧盟（EU）" : "European Union (EU)" },
    { code: "US" as const, title: isZh ? "美国（US）" : "United States (US)" }
  ];
  const previewQuestions = isZh
    ? [
        "企业是否属于受规制主体？",
        "涉及哪些数据类型与跨境场景？",
        "应走哪条合规路径？",
        "需要生成哪些报告与补充材料？"
      ]
    : [
        "Is the company a regulated entity?",
        "What data types and transfer scenarios are involved?",
        "Which compliance path should be selected?",
        "What reports and supporting materials are required?"
      ];
  const painPoints = isZh
    ? [
        {
          title: "规则分散，判断容易出错",
          desc: "中国、欧盟、美国跨境规则口径差异大，路径判断容易偏差。"
        },
        {
          title: "材料复杂，文书成本高",
          desc: "从清单到评估报告，准备链路长、协同成本高、反复修改频繁。"
        },
        {
          title: "审查标准不稳定，缺口难定位",
          desc: "很多问题并非完全缺失，而是不完整、不一致、不可审计。"
        }
      ]
    : [
        {
          title: "Fragmented rules, unstable judgments",
          desc: "CN, EU, and US rules differ significantly and route decisions often drift."
        },
        {
          title: "Heavy documentation cost",
          desc: "From inventories to assessment drafts, preparation and collaboration are expensive."
        },
        {
          title: "Unstable review standards",
          desc: "Many issues are partial, inconsistent, and hard to audit."
        }
      ];
  const moduleCards = isZh
    ? [
        { title: "合规路径诊断", desc: "问答 + 规则树判断义务路径与下一步动作。" },
        { title: "报告草案生成", desc: "生成安全评估、PIPIA、DPIA、TIA 等文书草案。" },
        { title: "合同与文件审查", desc: "对隐私政策、SCC/BCR、处理协议进行条款级检查。" },
        { title: "风险整改清单", desc: "把问题转为可执行整改任务并给出优先级。" }
      ]
    : [
        { title: "Route Diagnosis", desc: "Q&A + rule tree to choose obligations and next actions." },
        { title: "Draft Generation", desc: "Generate safety assessment, PIPIA, DPIA, and TIA drafts." },
        { title: "Contract Review", desc: "Clause-level checks for privacy policy, SCC/BCR, and DPAs." },
        { title: "Remediation List", desc: "Convert findings into prioritized, executable actions." }
      ];
  const flowSteps = isZh
    ? ["输入企业与业务事实", "抽取关键字段并做规则匹配", "形成报告与风险结论", "输出整改建议与后续动作"]
    : [
        "Input business facts",
        "Extract key fields and match rules",
        "Generate reports and risk conclusions",
        "Output remediation actions"
      ];

  const quickCreateFromTemplate = (taskTemplateId: string) => {
    const taskTemplate = findTaskTemplate(taskTemplateId);
    if (!taskTemplate) return;
    const suggestedName = buildSuggestedTaskName(taskTemplate, lang);
    const taskName = globalThis.prompt(t("homePrdQuickCreatePrompt"), suggestedName)?.trim();
    if (!taskName) return;
    onQuickCreate({
      mode: "rapid",
      name: taskName,
      jurisdiction: taskTemplate.jurisdiction,
      taskTemplateId: taskTemplate.id
    });
  };

  return (
    <section className="landing-reset-page">
      <div className="landing-reset-shell">
        <section className="landing-reset-hero">
          <div className="landing-reset-hero-copy">
            <span className="landing-reset-kicker">{t("heroEyebrow")}</span>
            <h1>{t("homeResetHeroPosition")}</h1>
            <p>{t("homeResetHeroValue")}</p>
            <div className="landing-reset-actions" data-guide="home-start">
              <button className="pill-btn-primary" onClick={onStart}>{t("startCta")}</button>
              <button className="pill-btn" onClick={() => navigate("/tasks")}>{t("homeIntroTaskAction")}</button>
              {latestTask ? (
                <button className="pill-btn" onClick={() => navigate(`/workspace/${latestTask.id}`)}>
                  {t("homeIntroContinueAction")}
                </button>
              ) : null}
            </div>
          </div>
          <div className="landing-reset-hero-side">
            <div className="landing-reset-hero-metrics">
              <article>
                <span>{t("tasksStatTotal")}</span>
                <strong>{state.taskSpaces.length}</strong>
              </article>
              <article>
                <span>{t("tasksStatRuns")}</span>
                <strong>{state.moduleRuns.length}</strong>
              </article>
              <article>
                <span>{t("homeResetMetricJurisdictions")}</span>
                <strong>3</strong>
              </article>
            </div>
            <article className="landing-reset-preview-card">
              <header>
                <p>{isZh ? "实时预览" : "Live Preview"}</p>
                <strong>{isZh ? "合规路径智能诊断" : "Compliance Path Diagnosis"}</strong>
              </header>
              <div className="landing-reset-preview-list">
                {previewQuestions.map((question) => (
                  <div key={question}>
                    <span>{question}</span>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>

        <section className="landing-reset-middle">
          <header className="landing-reset-block-head">
            <h2>{t("homeResetMiddleTitle")}</h2>
          </header>
          <div className="landing-reset-steps-rail">
            <article className="landing-reset-stage">
              <div className="landing-reset-stage-title"><span>01</span><h3>{t("homeResetProblemTitle")}</h3></div>
              <p>{t("homeResetProblemDesc")}</p>
            </article>
            <article className="landing-reset-stage">
              <div className="landing-reset-stage-title"><span>02</span><h3>{t("homeResetSolutionTitle")}</h3></div>
              <p>{t("homeResetSolutionDesc")}</p>
            </article>
            <article className="landing-reset-stage">
              <div className="landing-reset-stage-title"><span>03</span><h3>{t("homeResetFeatureTitle")}</h3></div>
              <div className="landing-reset-tags">
                {featureTags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </article>
            <article className="landing-reset-stage">
              <div className="landing-reset-stage-title"><span>04</span><h3>{t("homeResetSceneTitle")}</h3></div>
              <p>{isZh ? "按法域分组展示可执行模板，点击即可创建任务。" : "Templates are grouped by jurisdiction and executable directly."}</p>
            </article>
            <article className="landing-reset-stage">
              <div className="landing-reset-stage-title"><span>05</span><h3>{t("homeResetAdvantageTitle")}</h3></div>
              <ul className="landing-reset-advantage-list">
                {advantageItems.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        <section className="landing-reset-overview">
          <header className="landing-reset-block-head">
            <h2>{isZh ? "问题与价值" : "Why This Matters"}</h2>
          </header>
          <div className="landing-reset-overview-grid">
            {painPoints.map((item) => (
              <article key={item.title} className="landing-reset-overview-card">
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-reset-modules">
          <header className="landing-reset-block-head">
            <h2>{isZh ? "功能模块" : "Core Modules"}</h2>
          </header>
          <div className="landing-reset-modules-grid">
            {moduleCards.map((item) => (
              <article key={item.title} className="landing-reset-module-card">
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-reset-scenes">
          <header className="landing-reset-block-head">
            <h2>{isZh ? "法域场景入口" : "Jurisdiction Entries"}</h2>
          </header>
          <div className="landing-reset-scene-grid">
            {jurisdictionColumns.map((column) => (
              <section key={column.code} className="landing-reset-scene-col">
                <header>
                  <strong>{column.title}</strong>
                </header>
                <div className="landing-reset-template-list">
                  {listTaskTemplatesByJurisdiction(column.code).map((template) => (
                    <button
                      key={template.id}
                      type="button"
                      className="landing-reset-template-card"
                      onClick={() => quickCreateFromTemplate(template.id)}
                    >
                      <h4>{getTaskTemplateTitle(template, lang)}</h4>
                      <p>{template.subtitle[lang]}</p>
                      <span>{getTaskTemplateInputHint(template, lang)}</span>
                      <span>{getTaskTemplateOutputHint(template, lang)}</span>
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </section>

        <section className="landing-reset-flow">
          <header className="landing-reset-block-head">
            <h2>{isZh ? "工作流程" : "Workflow"}</h2>
          </header>
          <div className="landing-reset-flow-grid">
            {flowSteps.map((step, index) => (
              <article key={step}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{step}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-reset-footer">
          <header className="landing-reset-block-head">
            <h2>{t("homeResetFooterTitle")}</h2>
          </header>
          <div className="landing-reset-footer-grid">
            <article>
              <h3>{t("homeResetCaseTitle")}</h3>
              <ul>
                {caseItems.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
            <article>
              <h3>{t("homeResetTrustTitle")}</h3>
              <ul>
                {trustItems.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
            <article>
              <h3>{t("homeResetConsultTitle")}</h3>
              <p>{t("homeResetConsultDesc")}</p>
              <div className="landing-reset-actions landing-reset-footer-actions">
                <button className="pill-btn" onClick={() => navigate("/tasks")}>{t("homeResetConsultCta")}</button>
                <button className="pill-btn-primary" onClick={onStart}>{t("homeResetTrialCta")}</button>
              </div>
            </article>
          </div>
        </section>
      </div>
    </section>
  );
}
