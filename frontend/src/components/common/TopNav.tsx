import { Link, NavLink, useLocation } from "react-router-dom";
import { useLang } from "../../lib/language";
import { BrandShieldIcon, DocsIcon, GuideIcon, HelpIcon, SettingsIcon } from "./AppIcons";

type TopNavProps = {
  onStart: () => void;
  onReplayGuide: () => void;
};

export function TopNav({ onStart: _onStart, onReplayGuide }: TopNavProps) {
  const { lang, setLang, t } = useLang();
  const location = useLocation();
  const onHome = location.pathname === "/";
  const onWorkspace = location.pathname.startsWith("/workspace");

  const brandTitle = lang === "zh" ? "数规通" : "DATACOMPLY FLOW";
  const brandSub = lang === "zh" ? "DataComply Flow" : "";
  const brandTagline =
    lang === "zh"
      ? "AI驱动的数据跨境合规诊断与文书智能生成平台"
      : "AI-Driven Platform for Cross-Border Data Compliance Diagnosis and Intelligent Document Generation";

  return (
    <header className={`global-nav-wrap ${onHome ? "is-home" : ""} ${onWorkspace ? "is-workspace" : ""}`}>
      <div className={`global-nav ${onHome ? "global-nav-home" : ""}`}>
        <Link to="/" className="global-brand" aria-label={t("navHome")}>
          <span className="global-brand-logo" aria-hidden="true">
            <BrandShieldIcon width="22" height="22" />
          </span>
          <div className="global-brand-copy">
            <div className="global-brand-title">{brandTitle}</div>
            {brandSub ? <div className="global-brand-sub">{brandSub}</div> : null}
            <div className="global-brand-tagline">{brandTagline}</div>
          </div>
        </Link>

        <nav className="global-links" aria-label="global navigation">
          <NavLink to="/" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navHome")}
          </NavLink>
          <NavLink to="/tasks" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navTasks")}
          </NavLink>
          <NavLink to="/workspace" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navWorkspace")}
          </NavLink>
          <NavLink to="/evidence" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navEvidence")}
          </NavLink>
        </nav>

        <div className="global-actions">
          <Link to="/docs" className="global-chip global-chip-with-icon">
            <DocsIcon width="15" height="15" />
            <span>{t("navDocs")}</span>
          </Link>
          <button className="global-chip global-chip-with-icon" onClick={onReplayGuide}>
            <GuideIcon width="15" height="15" />
            <span>{lang === "zh" ? "引导" : "Guide"}</span>
          </button>
          {!onWorkspace ? (
            <button className="global-chip global-chip-optional global-chip-with-icon">
              <HelpIcon width="15" height="15" />
              <span>{t("navHelp")}</span>
            </button>
          ) : null}
          {!onWorkspace ? (
            <Link to="/settings" className="global-chip global-chip-optional global-chip-with-icon">
              <SettingsIcon width="15" height="15" />
              <span>{t("navSettings")}</span>
            </Link>
          ) : null}
          <button
            className="lang-btn lang-toggle-btn active"
            onClick={() => setLang(lang === "zh" ? "en" : "zh")}
            aria-label="toggle-language"
          >
            {lang === "zh" ? "中 / EN" : "EN / 中"}
          </button>
        </div>
      </div>
    </header>
  );
}
