import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchCitationMap, type CitationDetail } from "../../api/citations";
import { CitationMarkdownRenderer } from "./CitationMarkdownRenderer";

const popoverClick = vi.hoisted(() => vi.fn());
const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock("../../api/citations", async () => {
  const actual = await vi.importActual<typeof import("../../api/citations")>("../../api/citations");
  return { ...actual, fetchCitationMap: vi.fn() };
});

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

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
  knowledge_url: "/evidence?source=CN-LAW-003&article=39",
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
    mockNavigate.mockReset();
    fetchMap.mockReset();
    fetchMap.mockResolvedValue({
      task_id: "task-1",
      module: "assessment",
      footnote_map: { "1": exactCitation },
      citation_count: 1,
    });
  });

  it("navigates to evidence page on citation click", async () => {
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
    expect(mockNavigate).toHaveBeenCalledWith("/evidence?source=CN-LAW-003&article=39");
  });

  it("navigates to the canonical knowledge article route", async () => {
    fetchMap.mockResolvedValue({
      task_id: "task-1",
      module: "dpia",
      footnote_map: {
        "1": {
          ...exactCitation,
          module: "dpia",
          source_id: "EU-LAW-001",
          article_no: "36",
          knowledge_url: "/knowledge/laws/EU-LAW-001?article=36",
        },
      },
      citation_count: 1,
    });

    render(
      <CitationMarkdownRenderer
        markdown="事先咨询结论[1]"
        taskId="task-1"
        moduleKey="dpia"
      />,
    );

    const openButton = await screen.findByRole("button", { name: "打开引用" });
    await act(async () => openButton.click());

    expect(mockNavigate).toHaveBeenCalledWith("/knowledge/laws/EU-LAW-001?article=36");
  });

  it("does not navigate to an external or unsupported citation URL", async () => {
    fetchMap.mockResolvedValue({
      task_id: "task-1",
      module: "dpia",
      footnote_map: {
        "1": {
          ...exactCitation,
          knowledge_url: "https://example.invalid/redirect",
        },
      },
      citation_count: 1,
    });

    render(
      <CitationMarkdownRenderer markdown="结论[1]" taskId="task-1" moduleKey="dpia" />,
    );

    const openButton = await screen.findByRole("button", { name: "打开引用" });
    await act(async () => openButton.click());

    expect(mockNavigate).not.toHaveBeenCalled();
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
