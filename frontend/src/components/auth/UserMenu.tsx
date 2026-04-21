import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth/AuthContext";
import { useLang } from "../../lib/language";

export function UserMenu() {
  const { user, logout } = useAuth();
  const { lang } = useLang();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const initial = useMemo(() => (user?.username?.slice(0, 1) || "U").toUpperCase(), [user?.username]);

  useEffect(() => {
    const onDocClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!rootRef.current?.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  if (!user) return null;

  return (
    <div className="user-menu" ref={rootRef}>
      <button className="user-menu-trigger" onClick={() => setOpen((prev) => !prev)}>
        <span className="user-avatar">{initial}</span>
        <span className="user-name">{user.username}</span>
      </button>
      {open ? (
        <div className="user-menu-dropdown">
          <Link to="/tasks">{lang === "zh" ? "我的任务" : "My Tasks"}</Link>
          <Link to="/reports">{lang === "zh" ? "我的报告" : "My Reports"}</Link>
          <Link to="/workspace">{lang === "zh" ? "工作台" : "Workspace"}</Link>
          <Link to="/profile">{lang === "zh" ? "个人中心" : "Profile"}</Link>
          <button
            type="button"
            onClick={async () => {
              await logout();
              navigate("/");
            }}
          >
            {lang === "zh" ? "退出登录" : "Sign out"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
