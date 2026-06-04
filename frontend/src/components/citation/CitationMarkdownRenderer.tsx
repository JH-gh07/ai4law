import { Fragment, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchCitationMap, type CitationDetail } from "../../lib/citation-api";
import { fetchKnowledgeCitation } from "../../lib/knowledge-api";
import type { ModuleKey } from "../../lib/domain";
import { CitationArticleDrawer } from "./CitationArticleDrawer";
import { CitationPopover } from "./CitationPopover";

interface Props {
  markdown: string;
  taskId: string;
  moduleKey?: ModuleKey;
}

function isBasisOnlyParagraph(text: string): boolean {
  const trimmed = text.trim();
  return /^【依据：[^】]+】$/.test(trimmed);
}

function buildFallbackKnowledgeUrl(citation: CitationDetail): string | null {
  if (!citation.source_id) return null;
  const params = new URLSearchParams();
  if (citation.article_no) {
    params.set("article", citation.article_no);
  } else if (citation.section_id) {
    params.set("section", citation.section_id);
  } else if (citation.clause_id) {
    params.set("clause", citation.clause_id);
  } else if (citation.anchor) {
    params.set("anchor", citation.anchor);
  }
  const query = params.toString();
  return `/knowledge/laws/${encodeURIComponent(citation.source_id)}${query ? `?${query}` : ""}`;
}

function compactText(value: string): string {
  return value.replace(/\s+/g, "").replace(/[《》【】[\]（）()：:；;，,。、“”"'']/g, "").toLowerCase();
}

function chineseNumberToInt(raw: string): number | null {
  if (!raw) return null;
  if (/^\d+$/.test(raw)) return Number(raw);

  const digitMap: Record<string, number> = {
    零: 0,
    〇: 0,
    一: 1,
    二: 2,
    两: 2,
    三: 3,
    四: 4,
    五: 5,
    六: 6,
    七: 7,
    八: 8,
    九: 9,
  };
  const unitMap: Record<string, number> = {
    十: 10,
    百: 100,
    千: 1000,
    万: 10000,
  };

  let result = 0;
  let section = 0;
  let number = 0;

  for (const char of raw) {
    if (char in digitMap) {
      number = digitMap[char];
      continue;
    }
    const unit = unitMap[char];
    if (!unit) continue;
    if (unit === 10000) {
      section = (section + (number || 0)) * unit;
      result += section;
      section = 0;
      number = 0;
      continue;
    }
    if (number === 0) number = 1;
    section += number * unit;
    number = 0;
  }

  const total = result + section + number;
  return total > 0 ? total : null;
}

function extractArticleNo(value: string): string {
  const match = value.match(/第\s*([0-9]+|[零〇一二两三四五六七八九十百千万]+)\s*条/);
  if (!match) return "";
  const parsed = chineseNumberToInt(match[1]);
  return parsed ? String(parsed) : "";
}

function extractBasisItems(block: string): string[] {
  const inner = block.replace(/^【依据：/, "").replace(/】$/, "").trim();
  return inner
    .split(/[；;]+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0 && item !== "未检索到" && item !== "未检索到相关法规");
}

function shortenCitationLabel(citation: CitationDetail): string {
  const article = citation.article_no ? `第${citation.article_no}条` : "";
  return `${citation.title}${article ? ` ${article}` : ""}`;
}

function findCitationFromMap(rawBasis: string, citationMap: Record<string, CitationDetail>): CitationDetail | null {
  const articleNo = extractArticleNo(rawBasis);
  const titleCandidate = rawBasis.replace(/第\s*([0-9]+|[零〇一二两三四五六七八九十百千万]+)\s*条/g, "").trim();
  const normalizedTitle = compactText(titleCandidate || rawBasis);

  const candidates = Object.values(citationMap).filter((item) => {
    const normalizedSource = compactText(item.title);
    return normalizedTitle.includes(normalizedSource) || normalizedSource.includes(normalizedTitle);
  });

  if (candidates.length === 0) return null;
  if (articleNo) {
    const exact = candidates.find((item) => item.article_no === articleNo);
    if (exact) return exact;
  }
  return candidates[0] ?? null;
}

function buildResolvedCitation(
  rawBasis: string,
  matched: Record<string, string>,
  preview: string,
): CitationDetail | null {
  const sourceId = matched.source_id ?? "";
  if (!sourceId) return null;
  const articleNo = extractArticleNo(rawBasis);
  const params = new URLSearchParams();
  if (articleNo) {
    params.set("article", articleNo);
  }
  return {
    citation_id: `resolved:${sourceId}:${articleNo || compactText(rawBasis)}`,
    module: "knowledge",
    source_id: sourceId,
    citation_type: "law_article",
    title: matched.title ?? rawBasis,
    article_no: articleNo,
    quote_text: preview,
    authority_level: matched.authority_level ?? matched.authority ?? "medium",
    binding_force: matched.binding_force ?? "recommended",
    related_issue_ids: [],
    related_fact_ids: [],
    related_evidence_ids: [],
    confidence_score: 1,
    footnote_number: null,
    source_kind: matched.category ?? "law_article",
    source_url: matched.source_url ?? "",
    allowed_usage: [],
    can_enter_external_report: true,
    external_report_allowed: true,
    confidence_threshold: 0.2,
    knowledge_url: `/knowledge/laws/${encodeURIComponent(sourceId)}${params.toString() ? `?${params.toString()}` : ""}`,
    anchor: "",
    section_id: "",
    clause_id: "",
    open_mode: "new_tab",
    can_jump: true,
  };
}

function renderInlineCitationText(
  value: string,
  citationMap: Record<string, CitationDetail>,
  resolvedBasisMap: Record<string, CitationDetail | null>,
  onOpenCitation: (citation: CitationDetail) => void,
): Array<string | JSX.Element> {
  const regex = /(\[(\d+)\]|【依据：[^】]+】)/g;
  const result: Array<string | JSX.Element> = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(value)) !== null) {
    if (match.index > lastIndex) {
      result.push(value.slice(lastIndex, match.index));
    }

    if (match[2]) {
      const footnoteNumber = Number(match[2]);
      const citation = citationMap[String(footnoteNumber)];
      if (!citation) {
        result.push(match[0]);
      } else {
        result.push(
          <span
            key={`footnote-${match.index}-${footnoteNumber}`}
            className="citation-marker-inline"
            onClick={() => onOpenCitation(citation)}
            style={{ cursor: "pointer" }}
          >
            <CitationPopover
              footnoteNumber={footnoteNumber}
              citation={citation}
              onClickSource={onOpenCitation}
            />
          </span>,
        );
      }
    } else {
      const entries = extractBasisItems(match[0])
        .map((raw) => ({ raw, citation: resolvedBasisMap[raw] }))
        .filter((item) => item.citation);

      if (entries.length === 0) {
        result.push(match[0]);
      } else {
        result.push(
          <span key={`basis-${match.index}`} className="citation-basis-inline">
            <span className="citation-basis-prefix">依据</span>
            {entries.map(({ raw, citation }, idx) =>
              citation ? (
                <span
                  key={`${raw}-${idx}`}
                  className="citation-marker-inline"
                  onClick={() => onOpenCitation(citation)}
                  style={{ cursor: "pointer" }}
                >
                  <CitationPopover
                    footnoteNumber={citation.footnote_number ?? idx + 1}
                    citation={citation}
                    onClickSource={onOpenCitation}
                    label={shortenCitationLabel(citation)}
                  />
                </span>
              ) : null,
            )}
          </span>,
        );
      }
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < value.length) {
    result.push(value.slice(lastIndex));
  }

  return result;
}

function flattenTextChildren(children: unknown): string | null {
  if (typeof children === "string") return children;
  if (typeof children === "number") return String(children);
  if (Array.isArray(children)) {
    const parts = children.map(flattenTextChildren);
    if (parts.every((item) => typeof item === "string")) {
      return parts.join("");
    }
  }
  return null;
}

export function CitationMarkdownRenderer({ markdown, taskId, moduleKey }: Props) {
  const [citationMap, setCitationMap] = useState<Record<string, CitationDetail>>({});
  const [selectedCitation, setSelectedCitation] = useState<CitationDetail | null>(null);
  const [resolvedBasisMap, setResolvedBasisMap] = useState<Record<string, CitationDetail | null>>({});

  useEffect(() => {
    if (!taskId) return;
    fetchCitationMap(taskId, moduleKey)
      .then((res) => setCitationMap(res.footnote_map))
      .catch(() => setCitationMap({}));
  }, [taskId, moduleKey]);

  const basisItems = useMemo(() => {
    const blocks = markdown.match(/【依据：[^】]+】/g) ?? [];
    return Array.from(new Set(blocks.flatMap(extractBasisItems)));
  }, [markdown]);

  useEffect(() => {
    if (basisItems.length === 0) {
      setResolvedBasisMap({});
      return;
    }

    let cancelled = false;

    const resolveAll = async () => {
      const next: Record<string, CitationDetail | null> = {};
      await Promise.all(
        basisItems.map(async (item) => {
          const fromMap = findCitationFromMap(item, citationMap);
          if (fromMap) {
            next[item] = fromMap;
            return;
          }
          try {
            const resolved = await fetchKnowledgeCitation(item);
            next[item] = resolved.matched ? buildResolvedCitation(item, resolved.matched, resolved.preview) : null;
          } catch {
            next[item] = null;
          }
        }),
      );
      if (!cancelled) {
        setResolvedBasisMap(next);
      }
    };

    void resolveAll();
    return () => {
      cancelled = true;
    };
  }, [basisItems, citationMap]);

  if (!markdown) {
    return <span className="citation-markdown-empty">—</span>;
  }

  const handleOpenCitation = (citation: CitationDetail) => {
    const targetUrl = citation.knowledge_url || buildFallbackKnowledgeUrl(citation);
    if (citation.can_jump && targetUrl) {
      window.open(targetUrl, "_blank", "noopener,noreferrer");
      return;
    }
    setSelectedCitation(citation);
  };

  return (
    <>
      <div className="citation-markdown-text workspace-report-richtext">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p({ children }) {
              const text = flattenTextChildren(children);
              if (!text) {
                return <p>{children}</p>;
              }
              return (
                <p className={isBasisOnlyParagraph(text) ? "workspace-legal-basis-block" : undefined}>
                  {renderInlineCitationText(text, citationMap, resolvedBasisMap, handleOpenCitation)}
                </p>
              );
            },
            li({ children }) {
              const text = flattenTextChildren(children);
              if (!text) {
                return <li>{children}</li>;
              }
              return <li>{renderInlineCitationText(text, citationMap, resolvedBasisMap, handleOpenCitation)}</li>;
            },
            blockquote({ children }) {
              const text = flattenTextChildren(children);
              if (!text) {
                return <blockquote>{children}</blockquote>;
              }
              return <blockquote>{renderInlineCitationText(text, citationMap, resolvedBasisMap, handleOpenCitation)}</blockquote>;
            },
            td({ children }) {
              const text = flattenTextChildren(children);
              if (!text) {
                return <td>{children}</td>;
              }
              return <td>{renderInlineCitationText(text, citationMap, resolvedBasisMap, handleOpenCitation)}</td>;
            },
            th({ children }) {
              return <th>{children}</th>;
            },
            text({ children }) {
              const text = flattenTextChildren(children);
              if (!text) {
                return <Fragment>{children}</Fragment>;
              }
              return <>{renderInlineCitationText(text, citationMap, resolvedBasisMap, handleOpenCitation)}</>;
            },
          }}
        >
          {markdown}
        </ReactMarkdown>
      </div>
      {selectedCitation ? (
        <CitationArticleDrawer citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
      ) : null}
    </>
  );
}
