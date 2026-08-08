import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CitationDetail } from "../../api/citations";
import { CitationPopover } from "./CitationPopover";

const citation = {
  citation_id: "cit-1",
  title: "个人信息保护法",
  article_no: "39",
  quote_text: "测试",
  authority_level: "high",
  citation_type: "law_article",
  source_kind: "law_article",
  confidence_score: 1,
  confidence_threshold: 0.2,
  can_enter_external_report: true,
  external_report_allowed: true,
  resolution: {
    resolution_type: "exact_article",
    target_id: "CN-LAW-003:39",
    confidence: 1,
    failure_reason: "",
    available_actions: ["view_article"],
  },
} as CitationDetail;

describe("CitationPopover", () => {
  afterEach(() => cleanup());

  it("uses a native button and forwards the selected citation", () => {
    const onClickSource = vi.fn();
    render(
      <CitationPopover
        footnoteNumber={1}
        citation={citation}
        onClickSource={onClickSource}
      />,
    );

    screen.getByRole("button", { name: "[1] 引用" }).click();

    expect(onClickSource).toHaveBeenCalledWith(citation);
  });

  it("does not invent a low-confidence reason when policy blocks external use", () => {
    render(
      <CitationPopover
        footnoteNumber={1}
        citation={{ ...citation, external_report_allowed: false }}
      />,
    );

    expect(screen.getByText("⚠️ 仅供内部审查")).toBeInTheDocument();
    expect(screen.queryByText(/仅供内部审查（置信度不足）/)).not.toBeInTheDocument();
  });
});
