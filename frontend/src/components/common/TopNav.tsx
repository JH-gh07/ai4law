import { Link, NavLink, useLocation } from "react-router-dom";
import { useLang } from "../../lib/language";

type TopNavProps = {
  onStart: () => void;
  onReplayGuide: () => void;
};

export function TopNav({ onStart, onReplayGuide }: TopNavProps) {
  const { lang, setLang, t } = useLang();
  const location = useLocation();
  const onHome = location.pathname === "/";
  const onWorkspace = location.pathname.startsWith("/workspace");

  return (
    <header className={`global-nav-wrap ${onHome ? "is-home" : ""} ${onWorkspace ? "is-workspace" : ""}`}>
      <div className={`global-nav ${onHome ? "global-nav-home" : ""}`}>
        <Link to="/" className="global-brand" aria-label={t("navHome")}>
          <span className="global-brand-logo">§</span>
          <div>
            <div className="global-brand-title">{t("appBrand")}</div>
            <div className="global-brand-sub">Compliance OS</div>
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
          <NavLink to="/reports" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navReports")}
          </NavLink>
          <NavLink to="/evidence" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navEvidence")}
          </NavLink>
        </nav>

        <div className="global-actions">
          <Link to="/docs" className="global-chip">{t("navDocs")}</Link>
          <button className="global-chip" onClick={onReplayGuide}>{t("onboardingReplay")}</button>
          {!onWorkspace ? <button className="global-chip global-chip-optional">{t("navHelp")}</button> : null}
          {!onWorkspace ? <Link to="/docs" className="global-chip global-chip-optional">{t("navSettings")}</Link> : null}
          <button className={`lang-btn ${lang === "zh" ? "active" : ""}`} onClick={() => setLang("zh")}>中</button>
          <button className={`lang-btn ${lang === "en" ? "active" : ""}`} onClick={() => setLang("en")}>EN</button>
          <button className="pill-btn-primary" onClick={onStart}>{t("navStart")}</button>
        </div>
      </div>
    </header>
  );
}
