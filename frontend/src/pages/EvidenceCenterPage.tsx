import { useMemo, useState } from "react";
import { useAppStore } from "../lib/app-store";
import { useLang } from "../lib/language";

export function EvidenceCenterPage() {
  const { t } = useLang();
  const { state } = useAppStore();
  const [keyword, setKeyword] = useState("");

  const hits = useMemo(() => {
    if (!keyword.trim()) return state.evidenceHits;
    const token = keyword.toLowerCase();
    return state.evidenceHits.filter(
      (item) => item.title.toLowerCase().includes(token) || item.snippet.toLowerCase().includes(token)
    );
  }, [keyword, state.evidenceHits]);

  return (
    <section className="page-shell">
      <div className="page-header">
        <h2>{t("evidenceCenterTitle")}</h2>
        <input
          className="resource-search"
          placeholder={t("searchPlaceholder")}
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
      </div>

      <div className="evidence-grid">
        {hits.map((hit) => (
          <article key={hit.id} className="evidence-card">
            <small>{hit.module.toUpperCase()} · {hit.source}</small>
            <h3>{hit.title}</h3>
            <p>{hit.snippet}</p>
          </article>
        ))}
        {hits.length === 0 ? <p className="resource-empty">{t("noEvidenceHits")}</p> : null}
      </div>
    </section>
  );
}
