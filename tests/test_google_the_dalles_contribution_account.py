import unittest

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT_ID = "prj_study_im3_campus_00231769626"


class GoogleTheDallesContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.policy = read(MODELING_POLICY)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        cls.panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            cls.config,
            cls.inventory,
            cls.panels,
            "2026-09-06T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            cls.policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_incremental_account_preserves_baseline_and_has_one_description(self):
        validate_evidence(self.evidence, self.config["candidates"])
        project = self.project
        self.assertEqual((project["project_id"], project["county_fips"]), (PROJECT_ID, "41065"))
        self.assertEqual(
            (project["economic_record_count"], project["reported_actual_count"], project["projection_count"]),
            (27, 23, 4),
        )
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(
            project["model_completeness"]["missing_categories"],
            ["public_costs", "resources", "suppliers"],
        )
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])
        tax_rows = [
            row for row in project["economic_records"]
            if row["metric_code"] in {"study.account_assessed_value", "study.property_taxes_billed"}
        ]
        self.assertEqual(len(tax_rows), 12)
        descriptions = [
            row["project_description"]
            for row in self.evidence["project_updates"]
            if row["project_id"] == PROJECT_ID and "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(descriptions[0].count("."), 2)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)

    def test_actual_forecast_and_permit_scopes_remain_distinct(self):
        rows = self.project["economic_records"]
        actuals = {row["claim_id"]: row for row in rows if row["basis"] == "reported_actual"}
        self.assertEqual(actuals["clm_study_google_dalles_employees_2021"]["value"], 120)
        self.assertEqual(actuals["clm_study_google_dalles_onsite_contractor_vendor_jobs_2021"]["value"], 400)
        self.assertEqual(actuals["clm_study_google_dalles_cumulative_investment_2021"]["value"], 5_000_000_000)
        self.assertEqual(actuals["clm_study_google_dalles_cgcc_simulation_lab_grant_2024"]["value"], 50_000)

        forecasts = [row for row in rows if row["basis"] == "source_projection"]
        self.assertEqual(len(forecasts), 4)
        self.assertEqual({row["period"]["kind"] for row in forecasts}, {"projection_horizon"})
        self.assertEqual(
            {(row["metric_code"], row["value"]) for row in forecasts},
            {("study.campus_investment_projection", 600_000_000), ("study.operating_jobs_projection", 10)},
        )

        permits = [row for row in rows if row["metric_code"] == "study.permitted_construction_value"]
        self.assertEqual(len(permits), 6)
        self.assertEqual(len({row["source_locator"] for row in permits}), 6)
        self.assertTrue(all("not audited" in row["notes"] for row in permits))
        self.assertFalse(any("annual_series_key" in row for row in permits))

    def test_eight_search_updates_document_negative_findings(self):
        updates = [
            row for row in self.evidence["project_updates"]
            if row["project_id"] == PROJECT_ID and " audit" in row["title"]
        ]
        self.assertEqual(len(updates), 8)
        self.assertTrue(all(row["as_of"] == "2026-09-06" for row in updates))
        notes = " ".join(row["notes"] for row in updates)
        for term in (
            "assessor",
            "permit",
            "utility",
            "environmental",
            "careers",
            "supplier",
            "recipient",
            "No records requests",
        ):
            self.assertIn(term, notes)

    def test_models_are_only_low_confidence_descriptive_county_benchmarks(self):
        grouped, _ = modeled_products(
            self.synthesis,
            self.config["candidates"],
            self.evidence,
            self.policy,
        )
        rows = grouped[PROJECT_ID]
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {row["metric_code"]: row["value"] for row in rows},
            {
                "study.modeled_county_gdp_comparison_gap": 69.31,
                "study.modeled_county_employment_comparison_gap": 22.32,
                "study.modeled_county_wage_comparison_gap": 17.06,
            },
        )
        self.assertEqual({row["category"] for row in rows}, {"county_outcome"})
        self.assertTrue(all(row["confidence"] == "low" for row in rows))
        self.assertTrue(all(row["derivation"]["method"] == "benchmark_application" for row in rows))
        self.assertTrue(all(row["interval"]["kind"] == "sensitivity_envelope" for row in rows))
        self.assertTrue(all("causal_design" not in row for row in rows))
        self.assertTrue(all(
            any("must not be interpreted as a data-center effect" in limit for limit in row["limitations"])
            for row in rows
        ))
        self.assertFalse(any("net_fiscal" in row["metric_code"] for row in rows))


if __name__ == "__main__":
    unittest.main()
