import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KnowledgeContentRenderer } from "./KnowledgeContentRenderer";

describe("KnowledgeContentRenderer", () => {
  it("renders plain text as a paragraph", () => {
    render(<KnowledgeContentRenderer content="Hello world" />);
    expect(screen.getByText("Hello world")).toBeDefined();
  });

  it("renders Markdown headings", () => {
    const content = [
      "# Title",
      "",
      "## Subtitle",
    ].join("\n");
    render(<KnowledgeContentRenderer content={content} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Title");
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Subtitle");
  });

  it("renders Markdown lists", () => {
    const content = ["- item 1", "- item 2"].join("\n");
    render(<KnowledgeContentRenderer content={content} />);
    expect(screen.getByText("item 1")).toBeDefined();
    expect(screen.getByText("item 2")).toBeDefined();
  });

  it("renders Markdown tables with scroll wrapper", () => {
    render(
      <KnowledgeContentRenderer
        content={"| A | B |\n|---|---|\n| 1 | 2 |"}
      />
    );
    expect(screen.getByRole("table")).toBeDefined();
    // Table is wrapped in scroll div
    const table = screen.getByRole("table");
    expect(table.closest(".kc-table-scroll")).toBeDefined();
  });

  it("renders links with safe attributes", () => {
    render(
      <KnowledgeContentRenderer
        content="[example](https://example.com)"
      />
    );
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders blockquotes", () => {
    render(<KnowledgeContentRenderer content="> quoted text" />);
    expect(screen.getByText("quoted text")).toBeDefined();
  });

  it("does NOT execute raw HTML tags", () => {
    render(
      <KnowledgeContentRenderer
        content={'<script>alert("xss")</script>'}
      />
    );
    // The script tag text should appear as escaped text, not execute
    expect(screen.queryByText(/alert/)).toBeDefined();
  });

  it("does NOT allow dangerouslySetInnerHTML through Markdown", () => {
    render(
      <KnowledgeContentRenderer
        content={'<img src=x onerror=alert(1)>'}
      />
    );
    // Should be rendered as text, not as an img element
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("renders with evidence variant class", () => {
    const { container } = render(
      <KnowledgeContentRenderer content="text" variant="evidence" />
    );
    expect(container.querySelector(".kc-renderer-evidence")).toBeDefined();
  });

  it("applies custom className", () => {
    const { container } = render(
      <KnowledgeContentRenderer content="text" className="custom" />
    );
    expect(container.querySelector(".custom")).toBeDefined();
  });
});
