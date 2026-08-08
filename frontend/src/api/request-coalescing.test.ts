import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import { fetchCitationMap } from "./citations";
import { fetchKnowledgeCitation } from "./knowledge";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("./auth", () => ({
  getAuthHeaders: vi.fn(() => ({ Authorization: "Bearer test-token" })),
}));

const mockedApiFetch = vi.mocked(apiFetch);

describe("read request coalescing", () => {
  beforeEach(() => {
    mockedApiFetch.mockReset();
  });

  it("shares one in-flight citation-map request across report renderers", async () => {
    mockedApiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ task_id: "coalesce-task", module: "assessment", footnote_map: {}, citation_count: 0 }),
    } as Response);

    const first = fetchCitationMap("coalesce-task", "assessment");
    const second = fetchCitationMap("coalesce-task", "assessment");

    await Promise.all([first, second]);
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);
    expect(mockedApiFetch).toHaveBeenCalledWith(
      "/api/v1/citations/reports/coalesce-task?module=assessment",
      { headers: { Authorization: "Bearer test-token" } },
    );
  });

  it("shares one in-flight knowledge citation request for the same normalized query", async () => {
    mockedApiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ query: "个人信息保护法第39条", matched: null, preview: "" }),
    } as Response);

    const first = fetchKnowledgeCitation("  个人信息保护法第39条  ");
    const second = fetchKnowledgeCitation("个人信息保护法第39条");

    await Promise.all([first, second]);
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);
  });
});
