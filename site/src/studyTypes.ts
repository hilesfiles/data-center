export interface StudyProjectSummary {
  project_id: string;
  name: string;
  inventory_entity_id: string;
  inventory_entity_type: "campus" | "facility";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  operator_label: string;
  study_group: "Hyperscale" | "Colocation" | "Private enterprise";
  membership_status: "research_candidate";
  sector_status: "provisional_private_sector";
  history_status: "evidence_available" | "needs_research";
  documented_timing: string;
  panel_years: number;
  detail_path: string;
  latitude: number;
  longitude: number;
  economic_record_count: number;
  reported_actual_count: number;
  projection_count: number;
}

export interface StudyIndex {
  schema_version: "1.0.0";
  release_id: string;
  generated_at: string;
  screen_date: string;
  selection_basis: string;
  scope: string;
  economic_evidence_status: "not_yet_collected" | "partial";
  counts: {
    projects: number; counties: number; states: number; campus_targets: number;
    history_evidence_available: number; groups: Record<string, number>;
    projects_with_economic_evidence: number; economic_records: number;
    reported_actual_records: number; projection_records: number;
  };
  projects: StudyProjectSummary[];
}

export interface StudyProject extends StudyProjectSummary {
  schema_version: "1.0.0";
  release_id: string;
  generated_at: string;
  inventory_name: string;
  research_value: string;
  history: { description: string; anchor: { date?: string; year?: number; precision: string } | null; date_note: string };
  sources: { source_id: string; title: string; url: string }[];
  evidence_gaps: { code: string; label: string; status: "not_yet_collected" | "partial" | "projections_only"; needed: string }[];
  economic_records: EconomicRecord[];
  economic_sources: EconomicSource[];
  economic_scope_note: string;
  research_updates: { project_id: string; source_id: string; as_of: string; title: string; notes: string; source: EconomicSource }[];
  evidence_version: string;
  analysis_readiness: Record<"construction" | "operations" | "fiscal" | "causal", "not_assessed">;
  legacy_first_entry_note: string | null;
  scope_note: string;
}

export interface EconomicSource {
  source_id: string; title: string; url: string; publisher: string;
  retrieved_on: string; notes: string;
  review_method: "pdf_text_and_page_image" | "web_pdf_text" | "web_page" | "structured_data";
}

export interface EconomicRecord {
  claim_id: string; project_id: string; metric_code: string;
  label: string; category: string; value: number;
  unit: "USD" | "USD_per_hour" | "FTE" | "employees" | "workers" | "jobs" | "gallons_per_year" | "million_gallons_per_day" | "MW" | "generators" | "square_feet" | "percent" | "establishments";
  measure_type: "stock" | "flow" | "rate" | "peak";
  value_qualifier?: "exact" | "at_least" | "greater_than" | "up_to" | "approximately";
  basis: "reported_actual" | "source_projection";
  period: { kind: "fiscal_year" | "calendar_year" | "tax_year"; year: number; label: string } |
    { kind: "reported_snapshot"; report_date: string; label: string } |
    { kind: "projection_horizon"; report_date: string; horizon_years?: number; label: string } |
    { kind: "source_year"; year: number; label: string } |
    { kind: "historical_peak"; report_date?: string; label: string } |
    { kind: "cumulative"; report_date?: string; label: string };
  scope: { level: "campus" | "company_county" | "multi_campus_county" | "supporting_infrastructure" | "county_context"; label: string; county_fips: string; inventory_allocation: "unallocated" };
  source_id: string; pdf_page?: number; printed_page?: string; source_locator: string;
  notes: string; annual_series_key?: string; aggregation: "none";
}
