import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CitationDetail, CitationResolution } from "../../api/citations";
import { fetchArticleDetail } from "../../api/knowledge";
import { CitationArticleDrawer } from "./CitationArticleDrawer";

vi.mock("../../api/knowledge", () => ({
  fetchArticleDetail: vi.fn(),
}));

const fetchArticle = vi.mocked(fetchArticleDetail);

function citationWith(resolution: CitationResolution): CitationDetail {
  return {
    citation_id: "cit-1",
    module: "assessment",
    source_id: "CN-LAW-003",
    citation_type: "law_article",
    title: "个人信息保护法",
    article_no: resolution.resolution_type === "exact_article" ? "39" : "9999",
    quote_text: "测试依据",
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
    knowledge_url:
      resolution.resolution_type === "exact_article"
        ? "/knowledge/laws/CN-LAW-003?article=39"
        : "/knowledge/laws/CN-LAW-003",
    anchor: "",
    section_id: "",
    clause_id: "",
    open_mode: "in_app",
    can_jump: resolution.resolution_type === "exact_article",
    resolution,
  };
}

function renderDrawer(citation: CitationDetail) {
  return render(
    <MemoryRouter>
      <CitationArticleDrawer citation={citation} onClose={vi.fn()} />
    </MemoryRouter>,
  );
}

describe("CitationArticleDrawer", () => {
  beforeEach(() => fetchArticle.mockReset());
  afterEach(() => cleanup());

  it("loads article text only for an exact unique resolution", async () => {
    fetchArticle.mockResolvedValue({
      source_id: "CN-LAW-003",
      title: "个人信息保护法",
      article_no: "39",
      article_content: "处理敏感个人信息应当取得个人的单独同意。",
      prev_article_no: "38",
      prev_article_content: "上文",
      next_article_no: "40",
      next_article_content: "下文",
      source_url: "",
      authority_level: "high",
      binding_force: "mandatory",
      jurisdiction: "cn",
      doc_type: "law",
    });

    renderDrawer(
      citationWith({
        resolution_type: "exact_article",
        target_id: "CN-LAW-003:39",
        confidence: 1,
        failure_reason: "",
        available_actions: ["view_article"],
      }),
    );

    expect(await screen.findByText("处理敏感个人信息应当取得个人的单独同意。")).toBeInTheDocument();
    expect(fetchArticle).toHaveBeenCalledWith("CN-LAW-003", "39");
  });

  it("shows source-level status without requesting a nonexistent article", () => {
    renderDrawer(
      citationWith({
        resolution_type: "source_overview",
        target_id: "CN-LAW-003",
        confidence: 0.6,
        failure_reason: "article_not_found",
        available_actions: ["view_source_overview"],
      }),
    );

    expect(screen.getByText("当前为法规来源级定位")).toBeInTheDocument();
    expect(screen.getByText(/引用条号未在本地知识库中找到/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看法规概览" })).toBeInTheDocument();
    expect(fetchArticle).not.toHaveBeenCalled();
  });

  it("shows an unresolved reason and offers no false knowledge jump", () => {
    const citation = citationWith({
      resolution_type: "unresolved",
      target_id: "",
      confidence: 0,
      failure_reason: "source_not_found",
      available_actions: ["manual_review"],
    });
    citation.source_id = "unknown-source";
    citation.knowledge_url = "";

    renderDrawer(citation);

    expect(screen.getByRole("alert")).toHaveTextContent("引用来源未收入本地知识库");
    expect(screen.queryByRole("button", { name: /知识库|法规概览/ })).not.toBeInTheDocument();
    expect(fetchArticle).not.toHaveBeenCalled();
  });
});
