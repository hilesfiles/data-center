import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_01024051963"


class MetaEagleMountainContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
        config = read_json(ROOT / "config/v1/private-sector-study-candidates.json")
        inventory = {
            row["entity_id"]: row
            for row in read_json(ROOT / "site/public/data/v1/facilities/index.json")
        }
        panels = {}
        for path in sorted((ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")):
            for row in read_json(path):
                panels[row["county_fips"]] = row
        policy = read_json(ROOT / "config/v1/study-modeling-policy.json")
        _, details, _ = build_products(
            config,
            inventory,
            panels,
            "2026-09-06T00:00:00+00:00",
            load_evidence(),
            load_synthesis(),
            policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_audit_adds_direct_anchors_without_filling_unsupported_gaps(self):
        project = self.project
        self.assertEqual(
            (project["economic_record_count"], project["reported_actual_count"], project["projection_count"]),
            (12, 8, 4),
        )
        self.assertEqual(project["modeled_synthesis_count"], 0)
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], ["public_costs", "suppliers"])
        self.assertEqual(
            project["model_completeness"]["missing_county_outcomes"],
            [
                "study.modeled_county_employment_comparison_gap",
                "study.modeled_county_gdp_comparison_gap",
                "study.modeled_county_wage_comparison_gap",
            ],
        )

    def test_actuals_projections_scopes_and_description_are_explicit(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(records["clm_study_meta_eagle_mountain_capex_2024"]["value"], 1_500_000_000)
        self.assertEqual(records["clm_study_meta_eagle_mountain_operations_jobs_2024"]["value"], 300)
        self.assertEqual(records["clm_study_meta_eagle_mountain_taxable_value_2023"]["value"], 305_404_000)
        self.assertEqual(records["clm_study_meta_eagle_mountain_community_funding_2026"]["value"], 5_200_000)
        self.assertEqual(records["clm_study_meta_eagle_mountain_existing_generators_2022"]["basis"], "reported_actual")
        self.assertEqual(records["clm_study_meta_eagle_mountain_proposed_generators_2022"]["basis"], "source_projection")
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in records.values()))

        updates = [
            update for update in load_evidence()["project_updates"]
            if update["project_id"] == PROJECT_ID
        ]
        descriptions = [update["project_description"] for update in updates if "project_description" in update]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertGreaterEqual(len(updates), 14)


if __name__ == "__main__":
    unittest.main()
