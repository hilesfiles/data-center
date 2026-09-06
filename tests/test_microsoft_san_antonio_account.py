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
                          sum(r["basis"] == "source_projection" for r in rows)), (19, 10, 9))
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
        self.assertEqual(
            next(r for r in rows if r["claim_id"].endswith("floor_area_2026"))["value"],
            463_350,
        )
        self.assertEqual(
            sorted(r["value"] for r in rows if r["metric_code"] == "study.appraised_property_value"),
            [86_400, 91_391_490, 112_000_000],
        )
        self.assertEqual(
            sorted(r["value"] for r in rows if r["metric_code"] == "study.property_taxes_paid"),
            [2_093_024.14, 2_564_994.88],
        )
        self.assertFalse(any(r["source_id"] == "src_study_microsoft_san_antonio_impact_2026" for r in rows))

    def test_search_audit_is_explicit_and_description_is_unique(self):
        updates = [u for u in self.evidence["project_updates"] if u["project_id"] == PROJECT_ID]
        audits = [u for u in updates if u["title"].startswith("Search audit —")]
        self.assertEqual(len(audits), 8)
        for update in audits:
            for field in ("Portal/source family:", "Query/identifier:", "Date range:",
                          "Documents inspected:", "Result:"):
                self.assertIn(field, update["notes"])
        descriptions = [u["project_description"] for u in updates if u.get("project_description")]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertIn("5150 Rogers Road", descriptions[0])
        self.assertIn("463,350 square feet", descriptions[0])

    def test_only_bounded_noncausal_county_models_remain(self):
        grouped, _ = modeled_products(self.synthesis, self.config["candidates"], self.evidence)
        rows = grouped[PROJECT_ID]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["presentation"] == "modeled_not_observed_or_audited" for r in rows))
        self.assertTrue(all(r["category"] == "county_outcome" for r in rows))
        self.assertTrue(all(r["derivation"]["method"] == "benchmark_application" for r in rows))
        self.assertTrue(all("causal_design" not in r for r in rows))
        self.assertTrue(all(r["interval"]["low"] <= r["value"] <= r["interval"]["high"] for r in rows))
        self.assertTrue(all(
            any(p["name"] == "operating_by_year_anchor"
                and p["provenance"]["reference_id"].endswith("operating_employee_floor_2013")
                for p in r["parameters"])
            for r in rows
        ))
        self.assertTrue(all(any("must not be interpreted as a data-center effect" in limit
                                for limit in r["limitations"]) for r in rows))
        removed = {
            "est_study_microsoft_san_antonio_construction_eligible_spending",
            "est_study_microsoft_san_antonio_local_construction_spending",
            "est_study_microsoft_san_antonio_construction_job_years_total",
            "est_study_microsoft_san_antonio_construction_labor_income_total",
            "est_study_microsoft_san_antonio_operating_fte_total",
            "est_study_microsoft_san_antonio_operating_labor_income_total",
            "est_study_microsoft_san_antonio_operating_supplier_output",
            "est_study_microsoft_san_antonio_induced_household_output",
        }
        self.assertTrue(removed.isdisjoint({r["estimate_id"] for r in rows}))

    def test_generated_account_preserves_bounded_incompleteness(self):
        index, details, _ = build_products(
            self.config, self.inventory, self.panels, "2026-09-06T00:00:00+00:00",
            self.evidence, self.synthesis,
        )
        project = next(r for r in details if r["project_id"] == PROJECT_ID)
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["economic_record_count"], 19)
        self.assertEqual(project["modeled_synthesis_count"], 3)
        self.assertEqual(project["model_completeness"]["missing_categories"], ["suppliers"])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])
        self.assertEqual(next(r for r in index["projects"] if r["project_id"] == PROJECT_ID)
                         ["model_completeness"]["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
