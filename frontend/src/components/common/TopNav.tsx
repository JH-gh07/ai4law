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

  return (
    <header className={`global-nav-wrap ${onHome ? "is-home" : ""}`}>
      <div className={`global-nav ${onHome ? "global-nav-home" : ""}`}>
        <div className="global-brand">
          <span className="global-brand-logo">§</span>
          <div>
            <div className="global-brand-title">{t("appBrand")}</div>
            <div className="global-brand-sub">Compliance OS</div>
          </div>
        </div>

        <nav className="global-links" aria-label="global navigation">
          <NavLink to="/" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navHome")}
          </NavLink>
          <NavLink to="/jurisdictions/cn" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navCN")}
          </NavLink>
          <NavLink to="/jurisdictions/eu" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navEU")}
          </NavLink>
          <NavLink to="/jurisdictions/us" className={({ isActive }) => `global-link ${isActive ? "active" : ""}`}>
            {t("navUS")}
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
          <button className="global-chip">{t("navHelp")}</button>
          <Link to="/docs" className="global-chip">{t("navSettings")}</Link>
          <button className={`lang-btn ${lang === "zh" ? "active" : ""}`} onClick={() => setLang("zh")}>中</button>
          <button className={`lang-btn ${lang === "en" ? "active" : ""}`} onClick={() => setLang("en")}>EN</button>
          <button className="pill-btn-primary" onClick={onStart}>{t("navStart")}</button>
        </div>
      </div>
    </header>
  );
}
