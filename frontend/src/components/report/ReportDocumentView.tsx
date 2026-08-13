import type { JSX } from "react";
import type {
  Block,
  DocumentIR,
  FindingRecord,
  FindingSummaryBlock,
  SectionIR,
} from "../../lib/document-ir";
import { ClauseTree } from "./ClauseTree";
import { FindingView } from "./FindingView";

const WARNING_LABELS: Record<string, string> = {
  info: "提示",
  warning: "警告",
  error: "错误",
  fatal: "严重",
};

function findingMap(document: DocumentIR): Map<string, FindingRecord> {
  return new Map(document.findings.map((finding) => [finding.finding_id, finding]));
}

function BlockNode({ block, findings }: { block: Block; findings: Map<string, FindingRecord> }) {
  switch (block.type) {
    case "paragraph":
      return <p className="ir-paragraph">{block.text}</p>;
    case "claim":
      return <p className="ir-claim">{block.text}</p>;
    case "list":
      return <ListRenderer items={block.items} ordered={block.ordered ?? false} />;
    case "table":
      return (
        <table className="ir-table">
          <thead>
            <tr>{block.headers.map((header, index) => <th key={index}>{header}</th>)}</tr>
          </thead>
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      );
    case "warning": {
      const severity = block.severity ?? "warning";
      return (
        <aside className={`ir-warning ir-warning-${severity}`}>
          <span className="ir-warning-label">{WARNING_LABELS[severity] ?? severity}</span>
          <span>{block.text}</span>
        </aside>
      );
    }
    case "key_value":
      return (
        <dl className="ir-keyvalue">
          {block.items.map((item, index) => (
            <div className="ir-keyvalue-row" key={index}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      );
    case "finding_summary":
      return <FindingSummaryTable block={block} findings={findings} />;
    case "finding_detail": {
      const finding = findings.get(block.finding_ref);
      if (!finding) {
        return <p className="ir-missing-ref">找不到 finding：{block.finding_ref}</p>;
      }
      return <FindingView finding={finding} fieldOrder={block.field_order} />;
    }
    case "finding_reference": {
      const finding = findings.get(block.finding_ref);
      if (!finding) {
        return <p className="ir-missing-ref">找不到 finding：{block.finding_ref}</p>;
      }
      return (
        <p className="ir-finding-reference">
          参见 <strong>{finding.finding_id}</strong> {finding.title}
          {block.note ? `：${block.note}` : ""}
        </p>
      );
    }
    case "clause_group":
      return (
        <section className="ir-clause-group">
          <h5>{block.title}</h5>
          <ClauseTree clauses={block.clauses} />
        </section>
      );
    case "page_break":
      return <hr className="ir-page-break" aria-label={block.reason} />;
    case "citation_note":
      return (
        <ol className="ir-citation-note">
          {block.citation_refs.map((citationId) => <li key={citationId}>{citationId}</li>)}
        </ol>
      );
    default:
      // Exhaustive by construction; a truly unknown block renders a recovery
      // note instead of throwing (defensive, not the happy path).
      return (
        <p className="ir-unknown-block">
          未知内容块：{(block as { type?: string }).type ?? "unknown"}
        </p>
      );
  }
}

function ListRenderer({
  items,
  ordered,
  depth = 0,
}: {
  items: Array<{ text: string; children?: Array<{ text: string; children?: unknown[] }> }>;
  ordered: boolean;
  depth?: number;
}) {
  const Tag = (ordered ? "ol" : "ul") as "ol" | "ul";
  return (
    <Tag className={depth === 0 ? "ir-list" : "ir-list-nested"}>
      {items.map((item, index) => (
        <li key={index}>
          {item.text}
          {item.children && item.children.length > 0 ? (
            <ListRenderer
              items={item.children as Array<{ text: string; children?: Array<{ text: string; children?: unknown[] }> }>}
              ordered={ordered}
              depth={depth + 1}
            />
          ) : null}
        </li>
      ))}
    </Tag>
  );
}

function FindingSummaryTable({
  block,
  findings,
}: {
  block: FindingSummaryBlock;
  findings: Map<string, FindingRecord>;
}) {
  const columns = block.columns ?? ["finding_id", "risk_level", "title", "status"];
  const labels: Record<string, string> = {
    finding_id: "编号",
    risk_level: "风险等级",
    title: "标题",
    status: "状态",
  };
  return (
    <table className="ir-table ir-summary-table">
      <thead>
        <tr>{columns.map((column) => <th key={column}>{labels[column] ?? column}</th>)}</tr>
      </thead>
      <tbody>
        {block.finding_refs.map((ref) => {
          const finding = findings.get(ref);
          if (!finding) return null;
          return (
            <tr key={ref}>
              {columns.map((column) => (
                <td key={column}>{summaryCell(finding, column)}</td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function summaryCell(finding: FindingRecord, column: string): string {
  const value = (finding as unknown as Record<string, unknown>)[column];
  return value == null ? "" : String(value);
}

function SectionView({
  section,
  findings,
}: {
  section: SectionIR;
  findings: Map<string, FindingRecord>;
}) {
  const level = Math.min(Math.max(section.level, 1), 6);
  const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;
  const title = section.ordinal ? `${section.ordinal} ${section.title}` : section.title;
  return (
    <section className="ir-section">
      <HeadingTag>{title}</HeadingTag>
      <div className="ir-section-body">
        {section.blocks.map((block) => (
          <BlockNode key={block.block_id} block={block} findings={findings} />
        ))}
      </div>
    </section>
  );
}

export function ReportDocumentView({ document }: { document: DocumentIR }) {
  const findings = findingMap(document);
  return (
    <article className="report-document">
      {document.metadata?.title ? (
        <header className="report-document-header">
          <h3>{document.metadata.title}</h3>
          {document.metadata.company_name ? <p>{document.metadata.company_name}</p> : null}
        </header>
      ) : null}
      {document.sections.map((section) => (
        <SectionView key={section.section_id} section={section} findings={findings} />
      ))}
    </article>
  );
}
