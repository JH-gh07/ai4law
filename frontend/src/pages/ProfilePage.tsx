import { useAuth } from "../lib/auth/AuthContext";
import { useLang } from "../lib/language";

export function ProfilePage() {
  const { user } = useAuth();
  const { lang } = useLang();

  return (
    <section className="home-shell auth-page-shell">
      <article className="auth-card">
        <h1>{lang === "zh" ? "个人中心" : "Profile"}</h1>
        <p>{lang === "zh" ? "当前登录账号信息。" : "Current signed-in account."}</p>
        <div className="auth-profile-grid">
          <div>
            <strong>{lang === "zh" ? "用户名" : "Username"}</strong>
            <span>{user?.username || "-"}</span>
          </div>
          <div>
            <strong>{lang === "zh" ? "邮箱" : "Email"}</strong>
            <span>{user?.email || "-"}</span>
          </div>
          <div>
            <strong>{lang === "zh" ? "企业" : "Company"}</strong>
            <span>{user?.companyName || "-"}</span>
          </div>
        </div>
      </article>
    </section>
  );
}
