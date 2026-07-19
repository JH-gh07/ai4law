import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";

describe("apiFetch", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("forwards the request through the shared transport", async () => {
    const response = new Response(JSON.stringify({ ok: true }), { status: 200 });
    const fetchMock = vi.fn().mockResolvedValue(response);
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiFetch("/api/v1/example", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: 1 }),
      timeoutMs: 12000,
    });

    expect(result).toBe(response);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/example",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ value: 1 }),

        signal: expect.any(AbortSignal),
      }),
    );
  });
});
