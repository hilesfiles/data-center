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

