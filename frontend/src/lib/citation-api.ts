export interface CitationDetail {
  citation_id: string;
  source_id: string;
  citation_type: string;
  title: string;
  article_no: string;
  quote_text: string;
  authority_level: string;
  binding_force: string;
  related_issue_ids: string[];
  related_fact_ids: string[];
  related_evidence_ids: string[];
  confidence_score: number;
  footnote_number: number | null;
}

export interface CitationMapResponse {
  task_id: string;
  footnote_map: Record<string, CitationDetail>;
  citation_count: number;
}

const BASE = "/api/v1/citations";

export async function fetchCitationMap(taskId: string): Promise<CitationMapResponse> {
  const res = await fetch(`${BASE}/reports/${encodeURIComponent(taskId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch citation map: ${res.status}`);
  }
  return res.json();
}

export async function fetchCitationDetail(
  citationId: string,
  taskId: string,
): Promise<CitationDetail> {
  const url = `${BASE}/${encodeURIComponent(citationId)}?task_id=${encodeURIComponent(taskId)}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch citation detail: ${res.status}`);
  }
  return res.json();
}
