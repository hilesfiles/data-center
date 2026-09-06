import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_01132541700"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class MetaHenricoContributionAccountTest(unittest.TestCase):
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
            "2026-09-06T00:00:00+00:00",
            load_evidence(),
            load_synthesis(),
            policy,
        )
        cls.index = index
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)
        cls.evidence_fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.model_fragment = json.loads(MODEL_FRAGMENT.read_text(encoding="utf-8"))

    def test_counts_and_bounded_gate(self):
        project = self.project
        self.assertEqual((project["economic_record_count"], project["reported_actual_count"], project["projection_count"]), (13, 10, 3))
        self.assertEqual(project["modeled_synthesis_count"], 4)
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], ["public_costs", "suppliers"])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])

    def test_direct_records_preserve_scope_and_overlap_boundaries(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(records["clm_study_meta_henrico_scout_assessed_value_2025"]["value"], 2_364_906_425)
        self.assertEqual(records["clm_study_meta_henrico_electricity_2024"]["value"], 948_859_000)
        self.assertEqual(records["clm_study_meta_henrico_community_funding_2026"]["value"], 4_200_000)
        self.assertEqual(records["clm_study_meta_henrico_library_grant_fy2023"]["value"], 35_000)
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.evidence_fragment["records"]))
        self.assertIn("must not be summed", records["clm_study_meta_henrico_library_grant_fy2023"]["notes"])

    def test_only_defensible_residual_models_are_retained(self):
        models = self.project["modeled_syntheses"]
        self.assertEqual(
            {row["metric_code"] for row in models},
            {
                "study.modeled_annual_water_withdrawal",
                "study.modeled_county_gdp_comparison_gap",
                "study.modeled_county_employment_comparison_gap",
                "study.modeled_county_wage_comparison_gap",
            },
        )
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in models))
        self.assertTrue(all(row["derivation"]["method"] in {"allocation", "benchmark_application"} for row in models))
        self.assertFalse(any("causal_design" in row for row in models))
        water = next(row for row in models if row["estimate_id"] == "est_study_meta_henrico_water_withdrawal_2024")
        self.assertEqual(water["value"], 24_303_828.78)
        self.assertEqual(water["interval"]["kind"], "reported_band")

    def test_one_project_description_and_search_exhaustion_log(self):
        updates = self.evidence_fragment["project_updates"]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual(len(updates), 21)
        search_log = " ".join(row["notes"].lower() for row in updates)
        for family in ("assessor", "permit", "utility", "water", "supplier", "court", "bond", "community", "gdp", "qcew"):
            self.assertIn(family, search_log)


if __name__ == "__main__":
    unittest.main()
