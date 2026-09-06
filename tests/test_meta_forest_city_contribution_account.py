import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00460089167"


class MetaForestCityContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = json.loads((ROOT / "config/v1/private-sector-study-candidates.json").read_text(encoding="utf-8"))
        inventory = {
            row["entity_id"]: row
            for row in json.loads((ROOT / "site/public/data/v1/facilities/index.json").read_text(encoding="utf-8"))
        }
        panels = {}
        for path in sorted((ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")):
            for row in json.loads(path.read_text(encoding="utf-8")):
                panels[row["county_fips"]] = row
        policy = json.loads((ROOT / "config/v1/study-modeling-policy.json").read_text(encoding="utf-8"))
        index, details, _ = build_products(
            config,
            inventory,
            panels,
            "2026-09-05T00:00:00+00:00",
            load_evidence(),
            load_synthesis(),
            policy,
        )
        cls.index = index
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_gate_and_evidence_states(self):
        project = self.project
        self.assertEqual(project["model_completeness"]["status"], "full_modeled_account")
        self.assertEqual(project["model_completeness"]["missing_categories"], [])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])
        self.assertEqual((project["economic_record_count"], project["reported_actual_count"], project["projection_count"]), (24, 21, 3))
        self.assertEqual(project["modeled_synthesis_count"], 16)
        self.assertEqual(self.index["full_modeled_county_accounts"], 6)

    def test_all_required_channels_and_comparisons_are_present(self):
        project = self.project
        categories = {row["category"] for row in [*project["economic_records"], *project["modeled_syntheses"]]}
        self.assertTrue({"investment", "construction", "suppliers", "operations", "fiscal", "public_costs", "resources", "community"} <= categories)
        metrics = {row["metric_code"] for row in project["modeled_syntheses"]}
        self.assertTrue({
            "study.modeled_county_gdp_comparison_gap",
            "study.modeled_county_employment_comparison_gap",
            "study.modeled_county_wage_comparison_gap",
        } <= metrics)

    def test_models_remain_separate_and_noncausal(self):
        models = self.project["modeled_syntheses"]
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in models))
        self.assertFalse(any(row["derivation"]["method"] in {"difference_in_differences", "event_study", "synthetic_control"} for row in models))
        tax = next(row for row in models if row["estimate_id"] == "est_study_meta_forest_city_latest_local_tax_contribution")
        threshold = next(row for row in models if row["estimate_id"] == "est_study_meta_forest_city_annual_local_service_cost_break_even")
        self.assertEqual(tax["value"], 3_901_427 - 3_582_303)
        self.assertEqual(threshold["value"], tax["value"])
        self.assertIn("No net fiscal result", threshold["notes"])

    def test_direct_resource_observation_is_preserved(self):
        electricity = next(
            row for row in self.project["economic_records"]
            if row["claim_id"] == "clm_study_meta_forest_city_electricity_2024"
        )
        self.assertEqual(electricity["basis"], "reported_actual")
        self.assertEqual(electricity["value"], 535_555_000)
        self.assertEqual(electricity["unit"], "kWh_per_year")


if __name__ == "__main__":
    unittest.main()
