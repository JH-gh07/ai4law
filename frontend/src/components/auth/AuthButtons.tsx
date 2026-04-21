import { Link, useLocation } from "react-router-dom";
import { useLang } from "../../lib/language";

export function AuthButtons() {
  const { lang } = useLang();
  const location = useLocation();
  const redirect = `${location.pathname}${location.search}${location.hash}`;
  const target = encodeURIComponent(redirect === "/" ? "/tasks" : redirect);

  return (
    <div className="auth-buttons">
      <Link className="auth-login-link" to={`/login?redirect=${target}`}>
        {lang === "zh" ? "登录" : "Login"}
      </Link>
      <Link className="auth-register-link" to={`/register?redirect=${target}`}>
        {lang === "zh" ? "注册" : "Register"}
      </Link>
    </div>
  );
}
