import { useEffect, useMemo, useState } from "react";
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

type RenderToken =
  | { type: "text"; value: string }
  | { type: "footnote"; value: number }
  | { type: "basis"; value: string };

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
    .filter((item) => item.length > 0 && item !== "未检索到");
}

function shortenCitationLabel(citation: CitationDetail): string {
  const article = citation.article_no ? `第${citation.article_no}条` : "";
  return `${citation.title}${article ? ` ${article}` : ""}`;
}

function tokenizeMarkdown(markdown: string): RenderToken[] {
  if (!markdown) return [];
  const regex = /(\[(\d+)\]|【依据：[^】]+】)/g;
  const result: RenderToken[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(markdown)) !== null) {
    if (match.index > lastIndex) {
      result.push({ type: "text", value: markdown.slice(lastIndex, match.index) });
    }
    if (match[2]) {
      result.push({ type: "footnote", value: Number(match[2]) });
    } else {
      result.push({ type: "basis", value: match[1] });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < markdown.length) {
    result.push({ type: "text", value: markdown.slice(lastIndex) });
  }
  return result;
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

  const tokens = useMemo(() => tokenizeMarkdown(markdown), [markdown]);

  const basisItems = useMemo(() => {
    const items = tokens
      .filter((token): token is Extract<RenderToken, { type: "basis" }> => token.type === "basis")
      .flatMap((token) => extractBasisItems(token.value));
    return Array.from(new Set(items));
  }, [tokens]);

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
      <div className="citation-markdown-text">
        {tokens.map((token, index) => {
          if (token.type === "text") {
            return <span key={index}>{token.value}</span>;
          }

          if (token.type === "footnote") {
            const citation = citationMap[String(token.value)];
            if (!citation) {
              return <span key={index}>[{token.value}]</span>;
            }
            return (
              <span
                key={index}
                className="citation-marker-inline"
                onClick={() => handleOpenCitation(citation)}
                style={{ cursor: "pointer" }}
              >
                <CitationPopover
                  footnoteNumber={token.value}
                  citation={citation}
                  onClickSource={handleOpenCitation}
                />
              </span>
            );
          }

          const basisEntries = extractBasisItems(token.value)
            .map((raw) => ({ raw, citation: resolvedBasisMap[raw] }))
            .filter((item) => item.citation);

          if (basisEntries.length === 0) {
            return <span key={index}>{token.value}</span>;
          }

          return (
            <span key={index} className="citation-basis-inline">
              <span className="citation-basis-prefix">依据</span>
              {basisEntries.map(({ raw, citation }, itemIndex) => (
                <span
                  key={`${raw}-${itemIndex}`}
                  className="citation-marker-inline"
                  onClick={() => citation && handleOpenCitation(citation)}
                  style={{ cursor: citation ? "pointer" : "default" }}
                >
                  {citation ? (
                    <CitationPopover
                      footnoteNumber={citation.footnote_number ?? itemIndex + 1}
                      citation={citation}
                      onClickSource={handleOpenCitation}
                      label={shortenCitationLabel(citation)}
                    />
                  ) : null}
                </span>
              ))}
            </span>
          );
        })}
      </div>
      {selectedCitation ? (
        <CitationArticleDrawer citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
      ) : null}
    </>
  );
}
