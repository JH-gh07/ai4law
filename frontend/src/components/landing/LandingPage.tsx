import { Link } from "react-router-dom";
import { useLang } from "../../lib/language";

type LandingPageProps = {
  onStart: () => void;
};

export function LandingPage({ onStart }: LandingPageProps) {
  const { t } = useLang();
  const scenes = [
    { tag: t("storyScene1Tag"), title: t("storyScene1Title"), desc: t("storyScene1Desc"), metric: "Route Gate" },
    { tag: t("storyScene2Tag"), title: t("storyScene2Title"), desc: t("storyScene2Desc"), metric: "Evidence Bind" },
    { tag: t("storyScene3Tag"), title: t("storyScene3Title"), desc: t("storyScene3Desc"), metric: "Cross-Jurisdiction" }
  ];

  return (
    <section className="landing-hero" role="region" aria-label="landing hero">
      <div className="landing-inner">
        <div className="landing-content">
          <div className="landing-copy">
            <div className="landing-kicker reveal reveal-1">{t("heroEyebrow")}</div>
            <h2 className="landing-title reveal reveal-2">{t("heroTitle")}</h2>
            <h3 className="landing-accent reveal reveal-3">{t("heroTitleAccent")}</h3>
            <p className="landing-desc reveal reveal-4">{t("heroDesc")}</p>

            <div className="landing-actions reveal reveal-5" data-guide="home-start">
              <button className="pill-btn-primary" onClick={onStart}>{t("startCta")}</button>
              <Link className="pill-btn" to="/tasks">{t("secondaryCta")}</Link>
            </div>
          </div>

          <div className="landing-visual" aria-hidden="true">
            <div className="visual-glow" />
            <div className="visual-card">
              <div className="visual-card-kicker">LIVE COMPLIANCE SIGNAL</div>
              <div className="visual-line" />
              <div className="visual-metrics">
                <div><span>11</span><small>Modules</small></div>
                <div><span>3</span><small>Jurisdictions</small></div>
                <div><span>RAG</span><small>Evidence</small></div>
                <div><span>24/7</span><small>Copilot</small></div>
              </div>
              <div className="visual-orbit">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        </div>

        <section className="capability-section">
          <div className="capability-head">
            <h3>{t("capabilityTitle")}</h3>
            <p>{t("capabilityFlow")}</p>
          </div>
          <div className="capability-grid">
            <article className="capability-card">
              <h4>Route Intelligence</h4>
              <p>Diagnosis + threshold checks route each case to proper module path.</p>
            </article>
            <article className="capability-card wide">
              <h4>Draft Delivery Engine</h4>
              <p>Template-driven generation with report packages and structured outputs.</p>
            </article>
            <article className="capability-card">
              <h4>Evidence Chain</h4>
              <p>RAG citations and consistency issues flow into review and report center.</p>
            </article>
          </div>
        </section>

        <footer className="landing-footer">
          <span>路径判定</span>
          <span>证据引用</span>
          <span>草案生成</span>
          <span>质量复核</span>
        </footer>
      </div>

      <section className="story-deck" aria-label={t("storyTitle")}>
        {scenes.map((scene, index) => (
          <article key={scene.title} className="story-scene">
            <div className="story-inner">
              <div className="story-copy">
                <div className="story-tag">{scene.tag}</div>
                <h3>{scene.title}</h3>
                <p>{scene.desc}</p>
              </div>
              <div className="story-visual">
                <div className="story-meter">{scene.metric}</div>
                <div className="story-track">
                  <div className="story-dot" />
                  <div className="story-line" style={{ width: `${(index + 1) * 32}%` }} />
                </div>
              </div>
            </div>
          </article>
        ))}
      </section>
    </section>
  );
}
