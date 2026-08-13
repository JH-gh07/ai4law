import type { FindingRecord } from "../../lib/document-ir";

const FIELD_LABELS: Record<string, string> = {
  statement: "现状",
  legal_basis: "法规依据",
  recommendation: "整改建议",
  suggested_revision: "建议修改文本",
};

const RISK_LABELS: Record<string, string> = {
  HIGH: "高风险",
  MEDIUM: "中风险",
  LOW: "低风险",
};

function riskLevelLabel(level?: string): string {
  return (level && RISK_LABELS[level]) || level || "未评级";
}

export function FindingView({
  finding,
  fieldOrder = ["statement", "legal_basis", "recommendation", "suggested_revision"],
}: {
  finding: FindingRecord;
  fieldOrder?: string[];
}) {
  const risk = finding.risk_level ?? "MEDIUM";
  return (
    <article
      className={`finding-card finding-risk-${risk.toLowerCase()}`}
      data-finding-id={finding.finding_id}
    >
      <header className="finding-header">
        <h4 className="finding-title">
          <span className="finding-id">{finding.finding_id}</span>
          <span className="finding-title-text">{finding.title}</span>
        </h4>
        {/* risk is conveyed by text + icon, never color alone */}
        <span className={`finding-risk finding-risk-badge-${risk.toLowerCase()}`}>
          {riskLevelLabel(risk)}
        </span>
      </header>
      <dl className="finding-fields">
        {fieldOrder.map((field) => {
          if (field === "legal_basis") {
            const entries = legalBasisEntries(finding);
            if (!entries || entries.length === 0) return null;
            return (
              <div className="finding-field" key={field}>
                <dt>{FIELD_LABELS[field] ?? field}</dt>
                <dd>
                  {entries.length === 1 ? (
                    <span>{entries[0]}</span>
                  ) : (
                    <ul className="finding-basis-list">
                      {entries.map((entry, index) => (
                        <li key={index}>{entry}</li>
                      ))}
                    </ul>
                  )}
                </dd>
              </div>
            );
          }
          const value = fieldValue(finding, field);
          if (!value) return null;
          return (
            <div className="finding-field" key={field}>
              <dt>{FIELD_LABELS[field] ?? field}</dt>
              <dd>{value}</dd>
            </div>
          );
        })}
      </dl>
    </article>
  );
}

function fieldValue(finding: FindingRecord, field: string): string | null {
  switch (field) {
    case "statement":
      return finding.statement || null;
    case "recommendation":
      return finding.recommendation || null;
    case "suggested_revision":
      return finding.suggested_revision || null;
    default: {
      const value = (finding as unknown as Record<string, unknown>)[field];
      return typeof value === "string" && value ? value : null;
    }
  }
}

/**
 * Render the legal-basis field as one entry per line.
 *
 * ``basis_entries`` is authoritative when present: each entry carries a
 * human-readable label plus an attributed rationale (``label：rationale``),
 * mirroring the Markdown renderer's ``_legal_basis_lines``. Pure-label entries
 * keep only the label. Modules without ``basis_entries`` (e.g. BCR) fall back
 * to the legacy ``legal_basis`` shim joined with ``；``.
 */
function legalBasisEntries(finding: FindingRecord): string[] | null {
  if (finding.basis_entries && finding.basis_entries.length > 0) {
    return finding.basis_entries.map((entry) =>
      entry.rationale ? `${entry.label}：${entry.rationale}` : entry.label,
    );
  }
  if (finding.legal_basis && finding.legal_basis.length > 0) {
    return [finding.legal_basis.join("；")];
  }
  return null;
}
