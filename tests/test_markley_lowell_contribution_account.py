import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT_ID = "prj_study_im3_building_00214321737"
ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"


class MarkleyLowellContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        cls.panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }

    def test_corrective_direct_account_preserves_scopes_and_one_description(self):
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        descriptions = [
            update["project_description"]
            for update in fragment["project_updates"]
            if update.get("project_description")
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual((len(fragment["sources"]), len(fragment["records"])), (28, 25))

        _, details, _ = build_products(
            self.config,
            self.inventory,
            self.panels,
            "2026-09-06T00:00:00+00:00",
        )
        markley = next(project for project in details if project["project_id"] == PROJECT_ID)
        self.assertEqual(
            (markley["economic_record_count"], markley["reported_actual_count"], markley["projection_count"]),
            (27, 20, 7),
        )
        gifts = [
            row
            for row in markley["economic_records"]
            if row["metric_code"] == "study.direct_community_contribution"
        ]
        self.assertEqual(sorted((row["period"]["year"], row["value"]) for row in gifts), [(2025, 25000), (2026, 25000)])
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in gifts))

    def test_candidate_by_candidate_decisions_and_single_model(self):
        fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        audit = " ".join(update["notes"] for update in fragment["project_updates"])
        for decision in (
            "Investment candidate:",
            "Construction candidate:",
            "Supplier candidate:",
            "Operations candidate:",
            "Fiscal candidate decisions:",
            "Resource candidate:",
            "Community-model candidate:",
            "GDP candidate:",
            "Employment candidate:",
            "Wage candidate:",
        ):
            self.assertIn(decision, audit)

        evidence = load_evidence()
        synthesis = load_synthesis()
        grouped, _ = modeled_products(synthesis, self.config["candidates"], evidence)
        rows = grouped[PROJECT_ID]
        self.assertEqual(len(rows), 1)
        threshold = rows[0]
        self.assertEqual(threshold["estimate_id"], "est_study_markley_lowell_annual_service_cost_break_even_fy2026")
        self.assertEqual(threshold["value"], 534231.97)
        self.assertEqual(threshold["category"], "public_costs")
        self.assertEqual(threshold["scope"]["inventory_allocation"], "unallocated")
        self.assertTrue(any("No positive or negative net fiscal result" in limit for limit in threshold["limitations"]))
        self.assertFalse(any(row["category"] == "county_outcome" for row in rows))


if __name__ == "__main__":
    unittest.main()
