import { afterEach, describe, expect, it, vi } from "vitest";

import { authService, getAuthToken } from "./auth";
import { HttpStatusError, HttpTimeoutError } from "./client";

const TOKEN_KEY = "ai4law_auth_token_v1";

function seedToken() {
  globalThis.localStorage.setItem(TOKEN_KEY, "test-token");
}

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("authService.getCurrentUser", () => {
  afterEach(() => {
    globalThis.localStorage.clear();
    globalThis.sessionStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns null without making a request when no token is stored", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const result = await authService.getCurrentUser();

    expect(result).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("clears token and returns null on 401", async () => {
    seedToken();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "invalid" }, 401)));

    const result = await authService.getCurrentUser();

    expect(result).toBeNull();
    expect(getAuthToken()).toBeNull();
  });

  it("clears token and returns null on 403", async () => {
    seedToken();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "forbidden" }, 403)));

    const result = await authService.getCurrentUser();

    expect(result).toBeNull();
    expect(getAuthToken()).toBeNull();
  });

  it("re-throws on server error (5xx) and preserves the token", async () => {
    seedToken();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 500)));

    await expect(authService.getCurrentUser()).rejects.toBeInstanceOf(HttpStatusError);
    expect(getAuthToken()).toBe("test-token");
  });

  it("re-throws on network failure and preserves the token", async () => {
    seedToken();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    await expect(authService.getCurrentUser()).rejects.toBeInstanceOf(TypeError);
    expect(getAuthToken()).toBe("test-token");
  });

  it("re-throws on timeout and preserves the token", async () => {
    seedToken();
    // Abort the fetch with a timeout reason like apiFetch would.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() => {
        const controller = new AbortController();
        controller.abort(new HttpTimeoutError());
        return Promise.reject(controller.signal.reason);
      }),
    );

    await expect(authService.getCurrentUser()).rejects.toThrow();
    expect(getAuthToken()).toBe("test-token");
  });

  it("returns the user on success", async () => {
    seedToken();
    const user = { id: "u1", username: "alice", email: "a@example.com" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ user }, 200)));

    const result = await authService.getCurrentUser();

    expect(result).toEqual({ id: "u1", username: "alice", email: "a@example.com", companyName: undefined });
  });
});
