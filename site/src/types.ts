export type IndexStatus =
  | "publishable"
  | "provisional"
  | "insufficient_data"
  | "not_applicable";

export interface PublicIndex {
  score?: number;
  ci_low?: number;
  ci_high?: number;
  coverage?: number;
  status: IndexStatus;
  index_score_id?: string;
}

export interface CountySummary {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  as_of_year: number;
  facility_exposure: {
    operating_count: number;
    proposed_count: number;
    cancelled_or_rejected_count?: number;
    first_operational_year?: number;
    operational_mw_observed?: number;
    operational_mw_coverage?: number;
  };
  indices: Partial<
    Record<"OEM" | "DCEDI" | "DCFDi" | "DCCCI" | "DCOI" | "BSG" | "NCB", PublicIndex>
  >;
  quality: {
    data_quality_grade: "A" | "B" | "C" | "D" | "P";
    model_confidence_grade: "A" | "B" | "C" | "D" | "P";
    component_coverage: number;
  };
  data_version: string;
  model_versions?: string[];
  generated_at: string;
}

export interface SiteMetadata {
  schema_version: "1.0.0";
  data_version: string;
  data_status: "fixture" | "provisional" | "production";
  generated_at: string;
  latest_facility_year: number;
  latest_economic_year: number | null;
  methodology_version: string;
  notices: string[];
}

export interface FacilitySourceCoverage {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  source_id: string;
  release_vintage: string;
  source_record_count: number;
  point_record_count: number;
  building_record_count: number;
  campus_record_count: number;
  named_record_count: number;
  operator_named_record_count: number;
  observed_footprint_sqft: number;
  cross_county_source_record_count: number;
  coverage_status: "source_records_present" | "no_source_record";
  generated_at: string;
}

export type CountyMapMetric =
  | "im3-source-records"
  | "real-gdp"
  | "personal-income"
  | "population"
  | "per-capita-income"
  | "covered-employment"
  | "establishments"
  | "total-wages"
  | "weekly-wage"
  | "private-construction-employment";

export interface CountyEconomicBaseline {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  year: number;
  real_gdp_usd: number | null;
  personal_income_nominal_usd: number | null;
  population: number | null;
  per_capita_personal_income_nominal_usd: number | null;
  coverage_status: "complete" | "partial" | "unavailable";
  source_ids: string[];
  release_vintage: string;
  generated_at: string;
}

export interface CountyEmploymentWagesBaseline {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  year: number;
  annual_avg_covered_employment: number | null;
  annual_avg_establishments: number | null;
  total_annual_wages_nominal_usd: number | null;
  annual_avg_weekly_wage_nominal_usd: number | null;
  private_construction_annual_avg_employment: number | null;
  coverage_status: "complete" | "partial" | "unavailable";
  source_ids: string[];
  release_vintage: string;
  generated_at: string;
}

export interface CountyEconomicHistory {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  start_year: 2001;
  end_year: 2024;
  years: Array<{
    year: number;
    real_gdp_usd: number | null;
    population: number | null;
    annual_avg_covered_employment: number | null;
    annual_avg_weekly_wage_nominal_usd: number | null;
    coverage_status: "complete" | "partial" | "unavailable";
  }>;
  complete_year_count: number;
  coverage_status: "complete" | "partial" | "unavailable";
  generated_at: string;
}

export interface CountyTreatmentAssessment {
  schema_version: "1.0.0";
  treatment_assessment_id: string;
  treatment_definition_id: "trt_first_entry_v1";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  assessment_status:
    | "eligible"
    | "candidate_events_not_first_entry"
    | "no_reviewed_dated_operational_event";
  candidate_event_count: number;
  candidate_event_evaluation_ids: string[];
  first_entry_adjudication_ids?: string[];
  candidate_rejection_count?: number;
  inventory_completeness_status?: "verified_complete" | "partial" | "not_established";
  first_entry_research_summary?: string;
  first_entry_verified: boolean;
  review_scope: "reviewed_facility_events_only";
  eligible_treatment_period?: { date?: string; year?: number; precision: string };
  eligible_cohort_year?: number;
  created_at: string;
  updated_at: string;
  record_status: "active" | "provisional";
}

export interface FirstEntryResearchCandidate {
  schema_version: "1.0.0";
  first_entry_research_candidate_id: string;
  treatment_definition_id: "trt_first_entry_v1";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  census_region: "Northeast" | "Midwest" | "South" | "West";
  active_canonical_facility_count: number;
  reviewed_operational_facility_count: number;
  dated_operational_candidate_count: number;
  panel_complete_year_count: number;
  source_record_count: number;
  named_source_record_count: number;
  priority_score: number;
  priority_tier: "first_entry_high" | "first_entry_standard" | "first_entry_deferred";
  national_rank: number;
  region_rank: number;
  initial_tranche_rank?: number;
  queue_status: "initial_tranche" | "national_backlog";
  research_status: "queued" | "in_research" | "evidence_collected" | "needs_review" | "verified" | "blocked";
  county_first_entry_adjudication_id?: string;
  adjudication_status?: "candidate_rejected_first_entry" | "first_entry_verified" | "unresolved" | "conflicting";
  inventory_completeness_status?: "verified_complete" | "partial" | "not_established";
  research_summary?: string;
}

export interface CountyEntityResolutionCoverage {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  release_vintage: string;
  source_record_count: number;
  campus_linked_facility_count: number;
  operator_linked_record_count: number;
  pending_candidate_count: number;
  point_building_candidate_count: number;
  campus_membership_candidate_count: number;
  resolution_status:
    | "review_pending"
    | "governed_links_present"
    | "source_only"
    | "no_source_record";
  generated_at: string;
}

export interface PublicEntityResolutionRecord {
  schema_version: "1.0.0";
  entity_id: string;
  entity_type: "facility" | "campus";
  source_layer: "point" | "building" | "campus";
  source_record_id: string;
  campus_id?: string;
  campus_membership_status:
    | "linked_by_governed_rule"
    | "review_pending"
    | "not_linked"
    | "not_applicable";
  operator_id?: string;
  operator_canonical_name?: string;
  operator_resolution_status: "exact_text_normalized" | "source_operator_absent";
  pending_candidate_ids: string[];
  resolution_status: "governed_links_present" | "review_pending" | "source_only";
  release_vintage: string;
  generated_at: string;
}

export interface CountyEntityAdjudicationCoverage {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  reviewed_candidate_count: number;
  pending_candidate_count: number;
  merged_source_record_count: number;
  distinct_contained_facility_count: number;
  campus_linked_facility_count: number;
  adjudication_status: "review_pending" | "reviewed" | "no_candidate" | "no_source_record";
  generated_at: string;
}

export interface PublicEntityAdjudicationRecord {
  schema_version: "1.0.0";
  source_entity_id: string;
  resolved_entity_id: string;
  identity_status: "merged" | "distinct_within_building" | "unchanged" | "review_pending";
  container_facility_id?: string;
  campus_id?: string;
  candidate_outcomes: Array<{
    resolution_candidate_id: string;
    decision: "merge" | "do_not_merge" | "accept" | "reject" | "escalate";
  }>;
  generated_at: string;
}

export interface CountyLifecycleVerificationCoverage {
  schema_version: "1.0.0";
  county_fips: string;
  county_name: string;
  state_abbr: string;
  active_canonical_facility_count: number;
  queued_facility_count: number;
  in_research_facility_count: number;
  needs_review_facility_count: number;
  verified_facility_count: number;
  unknown_status_facility_count: number;
  coverage_status:
    | "pilot_queued"
    | "pilot_in_progress"
    | "pilot_reviewed"
    | "national_initial_tranche"
    | "national_in_progress"
    | "national_reviewed"
    | "national_backlog"
    | "backlog"
    | "no_active_facility";
  generated_at: string;
}

export interface LifecycleVerificationCandidate {
  schema_version: "1.0.0";
  verification_candidate_id: string;
  facility_id: string;
  canonical_name: string;
  primary_county_fips: string;
  county_name: string;
  state_abbr: string;
  priority_score: number;
  priority_tier: "pilot_high" | "pilot_standard" | "backlog";
  evidence_status: "no_external_evidence" | "partial" | "sufficient" | "conflicting";
  review_status: "queued" | "in_research" | "evidence_collected" | "needs_review" | "verified" | "blocked";
}

export interface PublicLifecycleVerificationRecord {
  schema_version: "1.0.0";
  verification_candidate_id: string;
  facility_id: string;
  canonical_name: string;
  resolution_status: "resolved" | "provisional" | "disputed" | "unresolved";
  resolved_current_status?: string;
  resolution_confidence?: number;
}

export interface NationalLifecyclePriorityRecord {
  schema_version: "1.0.0";
  national_priority_id: string;
  initial_tranche_rank: number;
  facility_id: string;
  canonical_name: string;
  primary_county_fips: string;
  county_name: string;
  state_abbr: string;
  census_region: "Northeast" | "Midwest" | "South" | "West";
  priority_score: number;
  priority_tier: "national_high" | "national_standard" | "national_deferred";
}

export interface PublicNationalLifecycleVerificationRecord {
  schema_version: "1.0.0";
  national_priority_id: string;
  initial_tranche_rank: number;
  facility_id: string;
  canonical_name: string;
  census_region: "Northeast" | "Midwest" | "South" | "West";
  review_status: "in_research" | "needs_review" | "verified";
  resolution_status: "resolved" | "provisional" | "disputed" | "unresolved";
  resolved_current_status?: string;
  resolution_confidence?: number;
}
