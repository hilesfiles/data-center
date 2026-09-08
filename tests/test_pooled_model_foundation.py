import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_pooled_model_foundation import (  # noqa: E402
    build_chronology_screen,
    build_comparison_readiness,
    build_county_year,
    build_derived_parameter_screen,
    build_facility_year,
    build_metric_aggregation_rules,
    build_reassessment,
    load_partition_records,
)
from scripts.study_project_fragments import load_evidence, load_synthesis  # noqa: E402
from scripts.validate_data_contract import ContractValidator  # noqa: E402


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PooledModelFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = read("site/public/data/v1/study/index.json")
        cls.manifest = read("site/public/data/v1/study/manifest.json")
        cls.panel_report = read(
            "data/silver/panels/county-economic-core-2001-2024.processing-report.json"
        )
        cls.treatment_index = read(
            "site/public/data/v1/treatments/county-first-entry-resolution/index.json"
        )
        cls.candidate_config = read("config/v1/private-sector-study-candidates.json")
        cls.panel_index = read("site/public/data/v1/panels/county-economic-history/index.json")
        cls.adjudications = read("site/public/data/v1/treatments/county-first-entry-resolution/adjudications.json")
        cls.panel_counties, _ = load_partition_records(
            cls.panel_index, ROOT / "site/public/data/v1/panels"
        )
        cls.resolution_candidates, _ = load_partition_records(
            cls.treatment_index, ROOT / "site/public/data/v1/treatments"
        )
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.projects = sorted(cls.index["projects"], key=lambda row: row["project_id"])
        cls.reassessment = read("data/silver/study/pooled/synthesis-reassessment.json")
        cls.derived_screen = read("data/silver/study/pooled/derived-parameter-screen.json")
        cls.aggregation_rules = read("data/silver/study/pooled/metric-aggregation-rules.json")
        cls.chronology_screen = read("data/silver/study/pooled/project-chronology-screen.json")
        cls.comparison_screen = read("data/silver/study/pooled/comparison-pool-readiness.json")
        cls.facility_year = read("data/silver/study/pooled/facility-year-exposures.json")
        cls.county_year = read("data/silver/study/pooled/county-year-exposures.json")
        cls.foundation_manifest = read("data/silver/study/pooled/manifest.json")

    def test_artifacts_validate_against_schemas(self):
        validator = ContractValidator(ROOT / "schemas/v1")
        pairs = [
            (self.reassessment, "pooled-synthesis-reassessment.schema.json"),
            (self.derived_screen, "derived-parameter-screen.schema.json"),
            (self.aggregation_rules, "metric-aggregation-rules.schema.json"),
            (self.chronology_screen, "project-chronology-screen.schema.json"),
            (self.comparison_screen, "comparison-pool-readiness.schema.json"),
            (self.facility_year, "facility-year-exposure.schema.json"),
            (self.county_year, "county-year-exposure.schema.json"),
            (self.foundation_manifest, "pooled-foundation-manifest.schema.json"),
        ]
        for payload, schema in pairs:
            with self.subTest(schema=schema):
                self.assertEqual(
                    validator.validate_record(payload, ROOT / "schemas/v1" / schema), []
                )

    def test_reassessment_contains_every_synthesis_once_with_final_policy_decisions(self):
        expected = {row["estimate_id"] for row in self.synthesis["estimates"]}
        actual = [row["estimate_id"] for row in self.reassessment["records"]]
        self.assertEqual(len(actual), 304)
        self.assertEqual(len(actual), len(set(actual)))
        self.assertEqual(set(actual), expected)
        self.assertTrue(all(row["final_recommendation"] for row in self.reassessment["records"]))
        self.assertTrue(
            all(
                row["review_status"] == "portfolio_policy_adjudicated"
                for row in self.reassessment["records"]
            )
        )
        self.assertEqual(
            sum(self.reassessment["counts"]["substantive_dispositions"].values()),
            304,
        )

    def test_empirical_candidates_use_reported_observations_only(self):
        annual_actuals = Counter()
        projects_by_metric = {}
        for row in self.evidence["records"]:
            year = row["period"].get("year")
            if row["basis"] == "reported_actual" and year is not None and 2001 <= year <= 2024:
                annual_actuals[row["metric_code"]] += 1
                projects_by_metric.setdefault(row["metric_code"], set()).add(row["project_id"])
        for candidate in self.reassessment["empirical_metric_candidates"]:
            metric = candidate["metric_code"]
            self.assertEqual(candidate["reported_observation_count"], annual_actuals[metric])
            self.assertEqual(candidate["project_count"], len(projects_by_metric[metric]))
            self.assertGreaterEqual(candidate["project_count"], 3)
            self.assertEqual(candidate["input_policy"], "reported_actual_only_leave_one_project_out")

    def test_derived_screen_is_observation_only_and_authorizes_no_calibration(self):
        self.assertEqual(self.derived_screen["counts"]["parameter_definitions"], 12)
        self.assertEqual(self.derived_screen["counts"]["calibration_authorized_parameters"], 0)
        self.assertTrue(
            all(not row["calibration_authorized"] for row in self.derived_screen["parameters"])
        )
        evidence_by_id = {row["claim_id"]: row for row in self.evidence["records"]}
        for row in self.derived_screen["observations"]:
            numerator_rows = [evidence_by_id[claim_id] for claim_id in row["numerator_claim_ids"]]
            denominator_rows = [evidence_by_id[claim_id] for claim_id in row["denominator_claim_ids"]]
            for evidence_row in numerator_rows + denominator_rows:
                self.assertEqual(evidence_row["basis"], "reported_actual")
                self.assertEqual(evidence_row["project_id"], row["project_id"])
                self.assertEqual(evidence_row["period"]["year"], row["year"])
                self.assertEqual(evidence_row["scope"]["label"], row["scope_label"])
            self.assertAlmostEqual(
                row["value"],
                row["numerator_value"] / row["denominator_value"]
                * (100000 if row["unit"] == "employees_per_100000_square_feet" else 1),
                places=8,
            )

    def test_facility_year_spine_represents_all_projects_and_keeps_basis_separate(self):
        project_ids = {row["project_id"] for row in self.projects}
        summaries = self.facility_year["project_summaries"]
        self.assertEqual({row["project_id"] for row in summaries}, project_ids)
        self.assertEqual(len(summaries), 36)
        self.assertEqual(len(self.facility_year["project_years"]), 36 * 24)
        keys = {
            (row["project_id"], row["year"])
            for row in self.facility_year["project_years"]
        }
        self.assertEqual(len(keys), 36 * 24)
        for row in self.facility_year["project_years"]:
            counts = Counter(component["origin_kind"] for component in row["components"])
            self.assertEqual(
                row["component_counts"],
                {
                    "reported_actual": counts["reported_actual"],
                    "source_projection": counts["source_projection"],
                    "modeled_synthesis": counts["modeled_synthesis"],
                },
            )
        eligibility_by_estimate = {
            row["estimate_id"]: row["pooled_input_eligibility"]
            for row in self.reassessment["records"]
        }
        modeled_components = [
            component
            for row in self.facility_year["project_years"]
            for component in row["components"]
            if component["origin_kind"] == "modeled_synthesis"
        ]
        self.assertTrue(modeled_components)
        self.assertTrue(
            all(
                component["analysis_eligibility"]
                == eligibility_by_estimate[component["origin_id"]]
                for component in modeled_components
            )
        )

    def test_county_year_spine_uses_35_counties_and_combines_crook_projects(self):
        self.assertEqual(len(self.county_year["county_years"]), 35 * 24)
        self.assertEqual(self.county_year["counts"]["project_count"], 36)
        self.assertEqual(self.county_year["counts"]["county_count"], 35)
        self.assertEqual(
            self.county_year["shared_counties"],
            {
                "41013": [
                    "prj_study_im3_building_00397914434",
                    "prj_study_im3_campus_00019988712",
                ]
            },
        )
        self.assertTrue(
            all(not row["pooled_estimation_eligible"] for row in self.county_year["county_years"])
        )
        exposures = [
            exposure
            for row in self.county_year["county_years"]
            for exposure in row["metric_exposures"]
        ]
        self.assertEqual(len(exposures), 48)
        self.assertEqual(self.county_year["counts"]["blocked_same_county_year_metric_overlaps"], 0)
        self.assertTrue(all(len(row["contributing_project_ids"]) == 1 for row in exposures))

    def test_chronology_and_comparison_gates_remain_conservative(self):
        self.assertEqual(len(self.chronology_screen["records"]), 36)
        self.assertEqual(self.chronology_screen["counts"]["project_anchors_registered"], 36)
        self.assertEqual(self.chronology_screen["counts"]["reconstructed_project_anchors"], 3)
        self.assertTrue(all(not row["county_first_entry_verified"] for row in self.chronology_screen["records"]))
        self.assertEqual(len(self.comparison_screen["records"]), 3144)
        self.assertEqual(self.comparison_screen["counts"]["comparison_eligible_counties"], 0)
        self.assertTrue(all(not row["comparison_eligible"] for row in self.comparison_screen["records"]))
        self.assertTrue(
            all(
                set(row["observed_county_outcomes"])
                == {
                    "real_gdp_usd",
                    "population",
                    "annual_avg_covered_employment",
                    "annual_avg_weekly_wage_nominal_usd",
                    "coverage_status",
                }
                for row in self.county_year["county_years"]
            )
        )

    def test_checked_in_outputs_are_deterministic(self):
        generated_at = self.manifest["generated_at"]
        release_id = self.manifest["release_id"]
        reassessment = build_reassessment(
            self.evidence, self.synthesis, self.projects, release_id, generated_at
        )
        derived_screen = build_derived_parameter_screen(
            self.evidence, release_id, generated_at
        )
        aggregation_rules = build_metric_aggregation_rules(
            reassessment, self.synthesis, release_id, generated_at
        )
        chronology_screen = build_chronology_screen(
            self.candidate_config, self.projects, release_id, generated_at
        )
        comparison_screen = build_comparison_readiness(
            self.panel_counties,
            self.projects,
            self.resolution_candidates,
            self.adjudications,
            release_id,
            generated_at,
        )
        facility_year = build_facility_year(
            self.evidence, self.synthesis, self.projects, chronology_screen, release_id, generated_at
        )
        county_year = build_county_year(
            facility_year,
            self.projects,
            self.panel_report,
            self.treatment_index,
            aggregation_rules,
            comparison_screen,
            release_id,
            generated_at,
        )
        self.assertEqual(reassessment, self.reassessment)
        self.assertEqual(derived_screen, self.derived_screen)
        self.assertEqual(aggregation_rules, self.aggregation_rules)
        self.assertEqual(chronology_screen, self.chronology_screen)
        self.assertEqual(comparison_screen, self.comparison_screen)
        self.assertEqual(facility_year, self.facility_year)
        self.assertEqual(county_year, self.county_year)


if __name__ == "__main__":
    unittest.main()
