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
