import { useState } from "react";
import type { TraceBlock } from "../../lib/domain";
import type { Language } from "../../lib/i18n";
import { getTraceI18n } from "../../lib/trace-i18n";

type Props = {
  block: TraceBlock;
  lang: Language;
};

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

export function TraceExpandableBlock({ block, lang }: Props) {
  const t = getTraceI18n(lang);
  const [expanded, setExpanded] = useState(false);
  const needsExpand = !!(block.isTruncated && block.preview);
  const displayContent = expanded || !needsExpand ? block.content : (block.preview ?? block.content);

  return (
    <div className="trace-block">
      <div className="trace-block-head">
        <span className="trace-block-label">{block.label}</span>
        <span className="trace-block-actions">
          <button className="trace-block-copy" onClick={() => copyToClipboard(block.content)} title={t.copy}>
            ⎘
          </button>
          {needsExpand ? (
            <button className="trace-block-expand" onClick={() => setExpanded((v) => !v)}>
              {expanded ? t.collapse : t.expandMore}
            </button>
          ) : null}
        </span>
      </div>
      {block.summary ? <div className="trace-block-summary">{block.summary}</div> : null}
      <pre className={`trace-block-content ${block.language === "json" ? "lang-json" : ""}`}>
        {displayContent}
      </pre>
    </div>
  );
}
