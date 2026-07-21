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

export function RegisterPage() {
  const { lang } = useLang();
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const redirect = useRedirectPath();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={redirect} replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError(lang === "zh" ? "两次输入的密码不一致" : "Passwords do not match");
      return;
    }

    setSubmitting(true);
    try {
      await register({ username, email, password, companyName });
      navigate(redirect, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : lang === "zh" ? "注册失败，请重试" : "Register failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="auth-page-shell">
      <article className="auth-card">
        <h1>{lang === "zh" ? "创建账号" : "Create your account"}</h1>
        <p>{lang === "zh" ? "注册后即可进入合规任务空间。" : "Register to enter the compliance workspace."}</p>

        <form className="auth-form" onSubmit={onSubmit}>
          <label>
            <span>{lang === "zh" ? "用户名" : "Username"}</span>
            <input name="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
          </label>

          <label>
            <span>{lang === "zh" ? "邮箱" : "Email"}</span>
            <input name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>

          <label>
            <span>{lang === "zh" ? "企业名称（可选）" : "Company (optional)"}</span>
            <input name="organization" autoComplete="organization" value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
          </label>

          <label>
            <span>{lang === "zh" ? "密码" : "Password"}</span>
            <input name="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>

          <label>
            <span>{lang === "zh" ? "确认密码" : "Confirm password"}</span>
            <input name="confirmPassword" type="password" autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
          </label>

          {error ? <div className="auth-error">{error}</div> : null}

          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? (lang === "zh" ? "注册中..." : "Registering...") : lang === "zh" ? "注册" : "Register"}
          </button>
        </form>

        <div className="auth-footer-links">
          <Link to={`/login?redirect=${encodeURIComponent(redirect)}`}>
            {lang === "zh" ? "已有账号？去登录" : "Have an account? Sign in"}
          </Link>
          <Link to="/">{lang === "zh" ? "返回首页" : "Back to home"}</Link>
        </div>
      </article>
    </section>
  );
}
