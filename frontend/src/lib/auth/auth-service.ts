import type { AuthUser, LoginPayload, RegisterPayload } from "./types";

type AuthResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
    company_name?: string | null;
  };
};

const TOKEN_KEY = "ai4law_auth_token_v1";

function setToken(token: string, remember: boolean): void {
  if (remember) {
    globalThis.localStorage?.setItem(TOKEN_KEY, token);
    globalThis.sessionStorage?.removeItem(TOKEN_KEY);
  } else {
    globalThis.sessionStorage?.setItem(TOKEN_KEY, token);
    globalThis.localStorage?.removeItem(TOKEN_KEY);
  }
}

function getToken(): string | null {
  return globalThis.sessionStorage?.getItem(TOKEN_KEY) ?? globalThis.localStorage?.getItem(TOKEN_KEY) ?? null;
}

export function getAuthToken(): string | null {
  return getToken();
}

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function clearToken(): void {
  globalThis.localStorage?.removeItem(TOKEN_KEY);
  globalThis.sessionStorage?.removeItem(TOKEN_KEY);
}

function toUser(payload: AuthResponse["user"]): AuthUser {
  return {
    id: payload.id,
    username: payload.username,
    email: payload.email,
    companyName: payload.company_name || undefined,
  };
}

type ValidationDetailItem = {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
};

const FIELD_LABEL_MAP: Record<string, string> = {
  username: "用户名",
  email: "邮箱",
  password: "密码",
  identifier: "用户名或邮箱",
  company_name: "企业名称",
  remember: "记住我",
};

function toReadableField(loc?: Array<string | number>): string {
  if (!Array.isArray(loc) || loc.length === 0) return "字段";
  const last = String(loc[loc.length - 1]);
  return FIELD_LABEL_MAP[last] ?? last;
}

function normalizeDetailMessage(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim().length > 0) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const lines = detail
      .map((item) => {
        const d = item as ValidationDetailItem;
        const field = toReadableField(d.loc);
        const message = typeof d.msg === "string" && d.msg.trim().length > 0 ? d.msg : "输入不合法";
        return `${field}：${message}`;
      })
      .filter((item) => item.trim().length > 0);

    if (lines.length > 0) {
      return lines.join("\n");
    }
  }

  return null;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = normalizeDetailMessage(data?.detail);
    throw new Error(message ?? `请求失败（${response.status}）`);
  }
  return data as T;
}

export const authService = {
  async login(payload: LoginPayload): Promise<AuthUser> {
    const data = await requestJson<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(data.access_token, payload.remember);
    return toUser(data.user);
  },

  async register(payload: RegisterPayload): Promise<AuthUser> {
    const data = await requestJson<AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        username: payload.username,
        email: payload.email,
        password: payload.password,
        company_name: payload.companyName,
      }),
    });
    setToken(data.access_token, true);
    return toUser(data.user);
  },

  async logout(): Promise<void> {
    const token = getToken();
    if (token) {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }).catch(() => undefined);
    }
    clearToken();
  },

  async getCurrentUser(): Promise<AuthUser | null> {
    const token = getToken();
    if (!token) return null;
    try {
      const data = await requestJson<{ user: AuthResponse["user"] }>("/api/v1/auth/me", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return toUser(data.user);
    } catch {
      clearToken();
      return null;
    }
  },
};
