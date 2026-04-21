import { Link, NavLink, useLocation } from "react-router-dom";
import { UserMenu } from "../auth/UserMenu";
import { useAuth } from "../../lib/auth/AuthContext";
import { useLang } from "../../lib/language";
import { DocsIcon, GlobeIcon, GuideIcon, SettingsIcon } from "./AppIcons";

type TopNavProps = {
  onStart: () => void;
  onReplayGuide: () => void;
};

export function TopNav({ onStart: _onStart, onReplayGuide }: TopNavProps) {
  const { lang, setLang, t } = useLang();
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const onHome = location.pathname === "/";
  const onWorkspace = location.pathname.startsWith("/workspace");
  const redirect = `${location.pathname}${location.search}${location.hash}`;
  const loginTarget = encodeURIComponent(redirect === "/" ? "/tasks" : redirect);

  const brandTitle = "DataComply Flow";
  const brandSub = lang === "zh" ? "数规通" : "ShuGuiTong";

  return (
    <header className={`global-nav-wrap ${onHome ? "is-home" : ""} ${onWorkspace ? "is-workspace" : ""}`}>
      <div className={`global-nav ${onHome ? "global-nav-home" : ""}`}>
        <Link to="/" className="global-brand" aria-label={t("navHome")}>
          <span className="global-brand-logo" aria-hidden="true">
            <img src="/brand-shield.svg" alt="" />
          </span>
          <div className="global-brand-copy">
            <div className="global-brand-name-row">
              <div className="global-brand-sub">{brandSub}</div>
              <div className="global-brand-title">{brandTitle}</div>
            </div>
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
            <span>{t("navHelp")}</span>
          </button>
          {!onWorkspace ? (
            <Link to="/settings" className="global-icon-action" aria-label={t("navSettings")} title={t("navSettings")}>
              <SettingsIcon width="17" height="17" />
            </Link>
          ) : null}
          <button
            className="global-icon-action global-lang-action"
            onClick={() => setLang(lang === "zh" ? "en" : "zh")}
            aria-label={lang === "zh" ? "switch-to-english" : "switch-to-chinese"}
            title={lang === "zh" ? "EN" : "中"}
          >
            <GlobeIcon width="17" height="17" />
          </button>
          {isAuthenticated ? (
            <UserMenu />
          ) : (
            <Link className="global-auth-lite" to={`/login?redirect=${loginTarget}`}>
              <span className="global-auth-lite-avatar" aria-hidden="true" />
              <span>{lang === "zh" ? "登录" : "Sign in"}</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
