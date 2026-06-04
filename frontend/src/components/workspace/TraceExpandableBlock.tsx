import { useState } from "react";
import type { TraceBlock } from "../../lib/domain";

type Props = {
  block: TraceBlock;
};

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

export function TraceExpandableBlock({ block }: Props) {
  const [expanded, setExpanded] = useState(false);
  const needsExpand = !!(block.isTruncated && block.preview);
  const displayContent = expanded || !needsExpand ? block.content : (block.preview ?? block.content);

  return (
    <div className="trace-block">
      <div className="trace-block-head">
        <span className="trace-block-label">{block.label}</span>
        <span className="trace-block-actions">
          <button className="trace-block-copy" onClick={() => copyToClipboard(block.content)} title="复制">
            ⎘
          </button>
          {needsExpand ? (
            <button className="trace-block-expand" onClick={() => setExpanded((v) => !v)}>
              {expanded ? "收起" : "展开更多"}
            </button>
          ) : null}
        </span>
      </div>
      <pre className={`trace-block-content ${block.language === "json" ? "lang-json" : ""}`}>
        {displayContent}
      </pre>
    </div>
  );
}
