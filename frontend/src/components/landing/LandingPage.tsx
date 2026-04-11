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
    { code: "CN" as const, title: "China (CN)" },
    { code: "EU" as const, title: "European Union (EU)" },
    { code: "US" as const, title: "United States (US)" }
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
        </section>

        <section className="landing-reset-middle">
          <header className="landing-reset-block-head">
            <h2>{t("homeResetMiddleTitle")}</h2>
          </header>

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
          </article>

          <article className="landing-reset-stage">
            <div className="landing-reset-stage-title"><span>05</span><h3>{t("homeResetAdvantageTitle")}</h3></div>
            <ul className="landing-reset-advantage-list">
              {advantageItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
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
