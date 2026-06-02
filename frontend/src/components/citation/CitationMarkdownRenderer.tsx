import { useEffect, useMemo, useState } from "react";
import {
  fetchCitationMap,
  type CitationDetail,
} from "../../lib/citation-api";
import { CitationPopover } from "./CitationPopover";
import { CitationArticleDrawer } from "./CitationArticleDrawer";

interface Props {
  markdown: string;
  taskId: string;
}

/**
 * Reusable component that renders markdown text with interactive citation markers.
 * Parses [n] footnote markers and replaces them with CitationPopover components
 * that show source info on hover and open an ArticleDrawer on click.
 */
export function CitationMarkdownRenderer({ markdown, taskId }: Props) {
  const [citationMap, setCitationMap] = useState<Record<string, CitationDetail>>({});
  const [selectedCitation, setSelectedCitation] = useState<CitationDetail | null>(null);

  useEffect(() => {
    if (!taskId) return;
    fetchCitationMap(taskId)
      .then((res) => setCitationMap(res.footnote_map))
      .catch(() => setCitationMap({}));
  }, [taskId]);

  const parts = useMemo(() => {
    if (!markdown) return [];
    const citationRegex = /\[(\d+)\]/g;
    const result: (string | number)[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = citationRegex.exec(markdown)) !== null) {
      if (match.index > lastIndex) {
        result.push(markdown.slice(lastIndex, match.index));
      }
      result.push(parseInt(match[1], 10));
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < markdown.length) {
      result.push(markdown.slice(lastIndex));
    }
    return result;
  }, [markdown]);

  if (!markdown) {
    return <span className="citation-markdown-empty">—</span>;
  }

  return (
    <>
      <pre className="citation-markdown-text">
        {parts.map((part, i) => {
          if (typeof part === "number") {
            const citation = citationMap[String(part)];
            if (citation) {
              return (
                <span
                  key={i}
                  className="citation-marker-inline"
                  onClick={() => setSelectedCitation(citation)}
                  style={{ cursor: "pointer" }}
                >
                  <CitationPopover
                    footnoteNumber={part}
                    citation={citation}
                    onClickSource={() => setSelectedCitation(citation)}
                  />
                </span>
              );
            }
            return <span key={i}>[{part}]</span>;
          }
          return <span key={i}>{part}</span>;
        })}
      </pre>
      {selectedCitation && (
        <CitationArticleDrawer
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </>
  );
}
