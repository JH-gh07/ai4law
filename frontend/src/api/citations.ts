import { apiFetch } from "./client";

export type CitationResolutionType =
  | "exact_article"
  | "source_overview"
  | "external_verified"
  | "unresolved";

export interface CitationResolution {
  resolution_type: CitationResolutionType;
  target_id: string;
  confidence: number;
  failure_reason: string;
  available_actions: string[];
}

export interface CitationDetail {
  citation_id: string;
  module: string;
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
  source_kind: string;
  source_url?: string;
  citation_granularity?: "article" | "source";
  publish_date?: string;
  effective_date?: string;
  source_status?: string;
  is_recent?: boolean;
  amendment_note?: string;
  allowed_usage: string[];
  can_enter_external_report: boolean;
  external_report_allowed: boolean;
  confidence_threshold: number;
  knowledge_url: string;
  anchor: string;
  section_id: string;
  clause_id: string;
  open_mode: string;
  can_jump: boolean;
  resolution: CitationResolution;
}

export interface CitationMapResponse {
  task_id: string;
  module: string;
  footnote_map: Record<string, CitationDetail>;
  citation_count: number;
}

const BASE = "/api/v1/citations";
const citationMapRequests = new Map<string, Promise<CitationMapResponse>>();

export async function fetchCitationMap(taskId: string, moduleKey?: string): Promise<CitationMapResponse> {
  const query = moduleKey ? `?module=${encodeURIComponent(moduleKey)}` : "";
  const url = `${BASE}/reports/${encodeURIComponent(taskId)}${query}`;
  const pending = citationMapRequests.get(url);
  if (pending) return pending;

  const request = apiFetch(url)
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Failed to fetch citation map: ${res.status}`);
      }
      return res.json() as Promise<CitationMapResponse>;
    })
    .finally(() => {
      if (citationMapRequests.get(url) === request) {
        citationMapRequests.delete(url);
      }
    });
  citationMapRequests.set(url, request);
  return request;
}

export async function fetchCitationDetail(
  citationId: string,
  taskId: string,
  moduleKey?: string,
): Promise<CitationDetail> {
  const searchParams = new URLSearchParams({ task_id: taskId });
  if (moduleKey) {
    searchParams.set("module", moduleKey);
  }
  const url = `${BASE}/${encodeURIComponent(citationId)}?${searchParams.toString()}`;
  const res = await apiFetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch citation detail: ${res.status}`);
  }
  return res.json();
}
