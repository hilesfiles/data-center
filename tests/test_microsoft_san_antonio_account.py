import unittest

from scripts.build_private_sector_study import CONFIG, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT_ID = "prj_study_im3_building_00364289074"


class MicrosoftSanAntonioAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.inventory = {r["entity_id"]: r for r in read(PUBLIC / "facilities/index.json")}
        cls.panels = {
            r["county_fips"]: r
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for r in read(path)
        }

    def test_evidence_states_and_scope_are_preserved(self):
        validate_evidence(self.evidence, self.config["candidates"])
        rows = [r for r in self.evidence["records"] if r["project_id"] == PROJECT_ID]
        self.assertEqual((len(rows), sum(r["basis"] == "reported_actual" for r in rows),
                          sum(r["basis"] == "source_projection" for r in rows)), (13, 4, 9))
        self.assertEqual(
            next(r for r in rows if r["claim_id"].endswith("operating_employee_floor_2013"))["value_qualifier"],
            "greater_than",
        )
        self.assertEqual(
            next(r for r in rows if r["claim_id"].endswith("permitted_renovation_value_2018"))["value"],
            2_771_000,
        )
        self.assertEqual(
            next(r for r in rows if r["claim_id"].endswith("recycled_water_plan_2008"))["basis"],
            "source_projection",
        )
        self.assertFalse(any(r["source_id"] == "src_study_microsoft_san_antonio_impact_2026" for r in rows))

    def test_modeled_rows_are_reproducible_and_noncausal(self):
        grouped, _ = modeled_products(self.synthesis, self.config["candidates"], self.evidence)
        rows = grouped[PROJECT_ID]
        by_id = {r["estimate_id"]: r for r in rows}
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(r["presentation"] == "modeled_not_observed_or_audited" for r in rows))
        self.assertEqual(
            tuple(by_id["est_study_microsoft_san_antonio_construction_job_years_total"]["interval"][k]
                  for k in ("low", "central", "high")),
            (1837.31, 3674.62, 5511.93),
        )
        local = by_id["est_study_microsoft_san_antonio_local_construction_spending"]
        self.assertEqual((local["interval"]["low"], local["value"], local["interval"]["high"]),
                         (52_500_000, 168_000_000, 346_500_000))
        operating = by_id["est_study_microsoft_san_antonio_operating_fte_total"]
        self.assertEqual((operating["interval"]["low"], operating["value"], operating["interval"]["high"]),
                         (490.19, 555.54, 620.9))
        comparisons = [r for r in rows if r["category"] == "county_outcome"]
        self.assertEqual(len(comparisons), 3)
        self.assertTrue(all(r["derivation"]["method"] == "benchmark_application" for r in comparisons))
        self.assertTrue(all("causal_design" not in r for r in comparisons))
        self.assertTrue(all(any("must not be interpreted as a data-center effect" in limit
                                for limit in r["limitations"]) for r in comparisons))

    def test_generated_account_passes_completion_gate(self):
        index, details, _ = build_products(
            self.config, self.inventory, self.panels, "2026-09-05T00:00:00+00:00",
            self.evidence, self.synthesis,
        )
        project = next(r for r in details if r["project_id"] == PROJECT_ID)
        self.assertEqual(project["model_completeness"]["status"], "full_modeled_account")
        self.assertEqual(project["economic_record_count"], 13)
        self.assertEqual(project["modeled_synthesis_count"], 11)
        self.assertEqual(project["model_completeness"]["missing_categories"], [])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])
        self.assertEqual(next(r for r in index["projects"] if r["project_id"] == PROJECT_ID)
                         ["model_completeness"]["status"], "full_modeled_account")


if __name__ == "__main__":
    unittest.main()
