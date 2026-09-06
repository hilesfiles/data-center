import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


PROJECT_ID = "prj_study_im3_building_00052227492"
FRAGMENT = Path(__file__).resolve().parents[1] / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"


class FlexentialChaskaContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.config = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            cls.config,
            inventory,
            panels,
            "2026-09-06T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            read(MODELING_POLICY),
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_fragment_is_project_scoped_and_boundary_safe(self):
        self.assertEqual(self.fragment["project_id"], PROJECT_ID)
        for key in ("records", "project_updates"):
            self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment[key]))
        fragment_text = json.dumps(self.fragment["records"])
        self.assertNotIn("IP Stream", fragment_text)
        self.assertNotIn("West Creek", fragment_text)
        boundary = self.fragment["project_updates"][0]["notes"]
        self.assertIn("append-only", boundary.lower())
        self.assertIn("orchestrator reconciliation", boundary)

    def test_direct_records_and_projection_are_kept_separate(self):
        validate_evidence(self.evidence, self.config["candidates"])
        added = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(len(added), 7)
        self.assertEqual(sum(row["basis"] == "reported_actual" for row in added.values()), 6)
        self.assertEqual(sum(row["basis"] == "source_projection" for row in added.values()), 1)
        self.assertEqual(
            sorted((row["period"]["year"], row["value"]) for row in added.values() if row["metric_code"] == "study.property_taxes_paid"),
            [(2023, 534_380), (2024, 551_454), (2025, 582_406)],
        )
        projection = added["clm_study_flexential_chaska_investment_projection_2014"]
        self.assertEqual((projection["value"], projection["value_qualifier"], projection["basis"]), (60_000_000, "greater_than", "source_projection"))
        self.assertEqual(added["clm_study_flexential_chaska_permit_b24_1109"]["value"], 5_861_872)

    def test_description_and_account_coverage(self):
        descriptions = [row["project_description"] for row in self.fragment["project_updates"] if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual(len([part for part in descriptions[0].split(". ") if part]), 3)
        self.assertIn("3500 Lyman Boulevard", descriptions[0])
        self.assertIn("outside this project boundary", descriptions[0])
        self.assertEqual(self.project["economic_record_count"], 16)
        self.assertEqual((self.project["reported_actual_count"], self.project["projection_count"]), (15, 1))
        self.assertEqual(self.project["model_completeness"]["status"], "incomplete")
        self.assertEqual(self.project["model_completeness"]["missing_categories"], ["community", "suppliers"])
        self.assertEqual(self.project["modeled_synthesis_count"], 0)

    def test_all_eight_categories_have_auditable_search_updates(self):
        updates = self.fragment["project_updates"]
        self.assertEqual(len(updates), 8)
        self.assertEqual(
            {row["title"].split(" audit", 1)[0] for row in updates},
            {"Investment", "Construction", "Supplier", "Operations", "Fiscal", "Public-cost", "Resource", "Community"},
        )
        self.assertTrue(all(row["as_of"] == "2026-09-06" for row in updates))
        self.assertTrue(all("Source families checked:" in row["notes"] for row in updates))


if __name__ == "__main__":
    unittest.main()
