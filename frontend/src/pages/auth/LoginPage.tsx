import { FormEvent, useMemo, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth/AuthContext";
import { useLang } from "../../lib/language";

function useRedirectPath(): string {
  const { search } = useLocation();
  return useMemo(() => {
    const params = new URLSearchParams(search);
    const redirect = params.get("redirect") || "/tasks";
    return redirect.startsWith("/") ? redirect : "/tasks";
  }, [search]);
}

export function LoginPage() {
  const { lang } = useLang();
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const redirect = useRedirectPath();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={redirect} replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ identifier, password, remember });
      navigate(redirect, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : lang === "zh" ? "登录失败，请重试" : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="auth-page-shell">
      <article className="auth-card">
        <h1>{lang === "zh" ? "登录数规通" : "Sign in to DataComply Flow"}</h1>
        <p>{lang === "zh" ? "继续进入任务空间与报告中心。" : "Continue to workspace and reports."}</p>

        <form className="auth-form" onSubmit={onSubmit}>
          <label>
            <span>{lang === "zh" ? "用户名或邮箱" : "Username or email"}</span>
            <input name="username" autoComplete="username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required autoFocus />
          </label>

          <label>
            <span>{lang === "zh" ? "密码" : "Password"}</span>
            <input name="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>

          <div className="auth-form-row">
            <label className="auth-check">
              <input name="remember" type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              <span>{lang === "zh" ? "记住我" : "Remember me"}</span>
            </label>
            <button type="button" className="auth-text-link">
              {lang === "zh" ? "忘记密码" : "Forgot password"}
            </button>
          </div>

          {error ? <div className="auth-error">{error}</div> : null}

          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? (lang === "zh" ? "登录中..." : "Signing in...") : lang === "zh" ? "登录" : "Sign in"}
          </button>
        </form>

        <div className="auth-footer-links">
          <Link to={`/register?redirect=${encodeURIComponent(redirect)}`}>
            {lang === "zh" ? "没有账号？去注册" : "No account? Register"}
          </Link>
          <Link to="/">{lang === "zh" ? "返回首页" : "Back to home"}</Link>
        </div>
      </article>
    </section>
  );
}
