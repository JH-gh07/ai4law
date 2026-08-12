/**
 * 认证上下文模块
 *
 * 函数：
 * - AuthProvider: 认证上下文提供者组件，接收子组件作为参数，并提供用户认证状态和相关操作函数给子组件使用。
 * - useAuth: 自定义Hook，用于在子组件中访问认证上下文的值，包括当前用户、加载状态、是否已认证以及登录、注册、登出和刷新用户信息的函数。
 *
 * 类型：
 * - AuthContextValue: 认证上下文的值类型，包含当前用户、加载状态、是否已认证以及登录、注册、登出和刷新用户信息的函数。
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { authService } from "../../api/auth";
import type { AuthUser, LoginPayload, RegisterPayload } from "./types";

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  /** Non-empty when /auth/me failed for a transient reason (network/timeout/5xx). */
  authError: string | null;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) return error.message;
  return "Unable to verify session. Please check your connection and retry.";
}

// 用于在子组件中访问认证上下文的值，包括当前用户、加载状态、是否已认证以及登录、注册、登出和刷新用户信息的函数。
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    setAuthError(null);
    try {
      const current = await authService.getCurrentUser();
      setUser(current);
    } catch (error) {
      setAuthError(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const current = await authService.getCurrentUser();
        if (active) {
          setUser(current);
        }
      } catch (error) {
        if (active) {
          setAuthError(errorMessage(error));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const next = await authService.login(payload);
    setAuthError(null);
    setUser(next);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const next = await authService.register(payload);
    setAuthError(null);
    setUser(next);
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setAuthError(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      authError,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, loading, authError, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// 用于在子组件中访问认证上下文的值，包括当前用户、加载状态、是否已认证以及登录、注册、登出和刷新用户信息的函数。
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
