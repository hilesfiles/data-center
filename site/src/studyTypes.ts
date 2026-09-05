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
  modeled_synthesis_count: number;
  model_completeness: ModelCompleteness;
}

export interface ModelCompleteness {
  status: "full_modeled_account" | "incomplete";
  required_categories: string[];
  covered_categories: string[];
  modeled_categories: string[];
  required_county_outcomes: string[];
  covered_county_outcomes: string[];
  missing_categories: string[];
  missing_county_outcomes: string[];
  direct_evidence_gap_count: number;
  definition: string;
}

export interface StudyIndex {
  schema_version: "1.0.0";
  release_id: string;
  generated_at: string;
  screen_date: string;
  selection_basis: string;
  scope: string;
  economic_evidence_status: "not_yet_collected" | "partial";
  full_modeled_county_accounts: number;
  modeling_policy_version: string;
  counts: {
    projects: number; counties: number; states: number; campus_targets: number;
    history_evidence_available: number; groups: Record<string, number>;
    projects_with_economic_evidence: number; economic_records: number;
    reported_actual_records: number; projection_records: number; modeled_synthesis_records: number;
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
  modeled_syntheses: ModeledSynthesis[];
  modeled_sources: EconomicSource[];
  modeled_scope_note: string;
  synthesis_version: string;
  modeling_policy_version: string;
  research_updates: { project_id: string; source_id: string; as_of: string; title: string; notes: string; source: EconomicSource }[];
  evidence_version: string;
  analysis_readiness: {
    construction: "not_assessed" | "modeled_available";
    operations: "not_assessed" | "modeled_available";
    fiscal: "not_assessed" | "modeled_available";
    causal: "not_assessed" | "causal_model_available";
  };
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
  unit: "USD" | "USD_per_hour" | "FTE" | "employees" | "workers" | "jobs" | "kWh_per_year" | "gallons_per_year" | "million_gallons_per_day" | "MW" | "generators" | "square_feet" | "percent" | "establishments";
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

export interface ModeledSynthesis {
  estimate_id: string; project_id: string; metric_code: string;
  label: string; category: string; value: number;
  unit: "USD" | "USD_per_year" | "USD_per_FTE" | "USD_per_hour" | "FTE" | "job_years" | "employees" | "workers" | "jobs" | "kWh_per_year" | "MWh_per_year" | "MW" | "percent" | "ratio" | "PUE_ratio" | "WUE_liters_per_kWh" | "gallons_per_year" | "gallons_per_day" | "million_gallons_per_day" | "metric_tons_co2e_per_year" | "acre_feet_per_year" | "square_feet" | "establishments" | "index_points" | "percentage_points";
  measure_type: "stock" | "flow" | "rate" | "peak" | "change" | "effect";
  basis: "modeled_synthesis";
  period: { kind: "calendar_year" | "fiscal_year" | "tax_year" | "source_year"; year: number; label: string } |
    { kind: "construction_period"; start_date: string; end_date: string; label: string } |
    { kind: "historical_peak" | "cumulative"; report_date: string; label: string } |
    { kind: "projection_horizon"; report_date: string; horizon_years: number; label: string };
  scope: { level: "facility" | "campus" | "company_county" | "county" | "multi_county" | "utility_service_area" | "state" | "supporting_infrastructure" | "ftz_activated_area"; label: string; geography_id?: string; county_fips?: string; state_abbr?: string; inventory_allocation: "allocated" | "unallocated" | "not_applicable"; allocation_method?: string };
  interval: { kind: "point_estimate" | "deterministic_counterfactual" | "sensitivity_envelope" | "confidence_interval" | "credible_interval" | "reported_band"; low: number; central: number; high: number; confidence_level?: number; interpretation: string };
  contribution_channel: "direct" | "indirect" | "induced" | "total" | "not_applicable";
  aggregation: { aggregation_id: string; role: "standalone" | "component" | "total"; component_estimate_ids?: string[]; overlap_policy: "do_not_sum_outside_declared_total" };
  parameters: { name: string; value: number; unit: string; provenance: { kind: "claim" | "source" | "assumption"; reference_id?: string; detail: string }; transformation: string }[];
  confidence: "low" | "medium" | "high";
  confidence_rationale: string;
  decision_relevance: string;
  evidence_search: { direct_observation_status: "not_found" | "partial" | "not_applicable"; source_projection_status: "not_found" | "available_separately" | "not_applicable"; remaining_evidence_gap: string };
  derivation: { method: "band_midpoint" | "benchmark_application" | "allocation" | "interpolation" | "extrapolation" | "engineering_estimate" | "statutory_counterfactual" | "sensitivity_analysis" | "input_output_multiplier" | "contribution_analysis" | "difference_in_differences" | "event_study" | "synthetic_control" | "strategic_infrastructure_model"; model_version: string; formula: string; input_claim_ids: string[]; input_source_ids: string[]; assumptions: string[] };
  multiplier_provenance?: { source_id: string; model_name: string; model_version: string; geography: string; vintage: string; local_purchase_assumption: string; channel_separation: "direct_indirect_induced_reported_separately" };
  causal_design?: { treatment_timing: string; comparison_design: string; outcome_definition: string; pre_period: string; post_period: string; diagnostics: string[]; limitations: string[] };
  limitations: string[];
  presentation: "modeled_not_observed_or_audited";
  notes: string; annual_series_key?: string; reviewed_on: string;
}
