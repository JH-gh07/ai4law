import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchCitationMap, type CitationDetail } from "../../api/citations";
import { CitationMarkdownRenderer } from "./CitationMarkdownRenderer";

const popoverClick = vi.hoisted(() => vi.fn());

vi.mock("../../api/citations", async () => {
  const actual = await vi.importActual<typeof import("../../api/citations")>("../../api/citations");
  return { ...actual, fetchCitationMap: vi.fn() };
});

vi.mock("./CitationArticleDrawer", () => ({
  CitationArticleDrawer: ({ citation }: { citation: CitationDetail }) => (
    <div data-testid="citation-drawer">{citation.title}</div>
  ),
}));

vi.mock("./CitationPopover", () => ({
  CitationPopover: ({
    citation,
    onClickSource,
  }: {
    citation: CitationDetail;
    onClickSource?: (citation: CitationDetail) => void;
  }) => (
    <button
      type="button"
      onClick={() => {
        popoverClick();
        onClickSource?.(citation);
      }}
    >
      打开引用
    </button>
  ),
}));

const fetchMap = vi.mocked(fetchCitationMap);

const exactCitation: CitationDetail = {
  citation_id: "cit-1",
  module: "assessment",
  source_id: "CN-LAW-003",
  citation_type: "law_article",
  title: "个人信息保护法",
  article_no: "39",
  quote_text: "处理敏感个人信息应当取得单独同意。",
  authority_level: "high",
  binding_force: "mandatory",
  related_issue_ids: [],
  related_fact_ids: [],
  related_evidence_ids: [],
  confidence_score: 1,
  footnote_number: 1,
  source_kind: "law_article",
  source_url: "",
  allowed_usage: [],
  can_enter_external_report: true,
  external_report_allowed: true,
  confidence_threshold: 0.2,
  knowledge_url: "/knowledge/laws/CN-LAW-003?article=39",
  anchor: "",
  section_id: "",
  clause_id: "",
  open_mode: "in_app",
  can_jump: true,
  resolution: {
    resolution_type: "exact_article",
    target_id: "CN-LAW-003:39",
    confidence: 1,
    failure_reason: "",
    available_actions: ["view_article"],
  },
};

describe("CitationMarkdownRenderer", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    popoverClick.mockReset();
    fetchMap.mockReset();
    fetchMap.mockResolvedValue({
      task_id: "task-1",
      module: "assessment",
      footnote_map: { "1": exactCitation },
      citation_count: 1,
    });
  });

  it("opens the controlled in-app drawer without creating a new tab", async () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    render(
      <CitationMarkdownRenderer
        markdown="审查结论[1]"
        taskId="task-1"
        moduleKey="assessment"
      />,
    );

    const openButton = await screen.findByRole("button", { name: "打开引用" });
    await act(async () => openButton.click());

    expect(popoverClick).toHaveBeenCalledOnce();
    expect(await screen.findByTestId("citation-drawer")).toHaveTextContent("个人信息保护法");
    expect(openSpy).not.toHaveBeenCalled();
  });

  it("renders missing-evidence notices as warnings, never as citation controls", async () => {
    render(
      <CitationMarkdownRenderer
        markdown="企业应当完成评估。 【待核验：缺少法规依据】"
        taskId="task-1"
        moduleKey="assessment"
      />,
    );

    const notice = await screen.findByText("企业应当完成评估。 【待核验：缺少法规依据】");
    expect(notice.closest("p")).toHaveClass("workspace-legal-callout-pending");
    expect(screen.queryByRole("button", { name: "打开引用" })).not.toBeInTheDocument();
  });
});
