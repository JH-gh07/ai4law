import type { ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../lib/auth/AuthContext";

type ProtectedRouteProps = {
  children: ReactElement;
};

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, loading, authError } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="auth-page-shell">Loading...</div>;
  }

  if (authError) {
    // A transient failure (network/timeout/server error) must not bounce the
    // user back to login and must not clear their still-valid local token.
    return (
      <div className="auth-page-shell">
        <p className="auth-error-message">{authError}</p>
        <button className="kc-btn primary" type="button" onClick={() => globalThis.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  if (!isAuthenticated) {
    const redirect = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/login?redirect=${encodeURIComponent(redirect)}`} replace />;
  }

  return children;
}
