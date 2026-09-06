import unittest

from scripts.build_private_sector_study import CONFIG, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT_ID = "prj_study_im3_building_00888253616"


class NttSv1ContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        cls.panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }

    def test_sv1_additions_preserve_baseline_forecasts_and_scopes(self):
        _, details, _ = build_products(
            self.config,
            self.inventory,
            self.panels,
            "2026-09-06T00:00:00+00:00",
        )
        sv1 = next(project for project in details if project["project_id"] == PROJECT_ID)
        self.assertEqual(
            (sv1["economic_record_count"], sv1["reported_actual_count"], sv1["projection_count"]),
            (17, 15, 2),
        )
        self.assertEqual(len([r for r in sv1["economic_records"] if r.get("annual_series_key") == "ntt_sv1_regular_property_tax_paid"]), 9)
        description = sv1["project_description"]
        self.assertGreaterEqual(description.count("."), 2)
        self.assertGreaterEqual(len(description), 80)
        self.assertLessEqual(len(description), 1000)
        self.assertEqual(len(description), len(description.strip()))

    def test_sv1_models_validate_and_remain_descriptive(self):
        evidence = load_evidence()
        synthesis = load_synthesis()
        grouped, _ = modeled_products(synthesis, self.config["candidates"], evidence)
        rows = grouped[PROJECT_ID]
        self.assertEqual(len(rows), 4)
        county_rows = [row for row in rows if row["category"] == "county_outcome"]
        self.assertEqual(len(county_rows), 3)
        self.assertTrue(all(row["derivation"]["method"] == "benchmark_application" for row in county_rows))
        self.assertTrue(all("causal_design" not in row for row in county_rows))
        threshold = next(row for row in rows if row["category"] == "public_costs")
        self.assertEqual(threshold["value"], 1024370.76)
        self.assertIn("No net fiscal result", threshold["notes"])


if __name__ == "__main__":
    unittest.main()
