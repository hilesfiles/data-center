import unittest

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT = "prj_study_im3_building_01073720208"


class GoogleCouncilBluffsContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.policy = read(MODELING_POLICY)
        validate_evidence(cls.evidence, cls.candidates["candidates"])
        cls.grouped, _ = modeled_products(
            cls.synthesis, cls.candidates["candidates"], cls.evidence, cls.policy
        )
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            cls.candidates,
            inventory,
            panels,
            "2026-09-06T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            cls.policy,
        )
        cls.detail = next(row for row in details if row["project_id"] == PROJECT)

    def test_project_identity_evidence_states_and_account_gate(self):
        self.assertEqual(self.detail["project_id"], PROJECT)
        self.assertEqual(self.detail["county_fips"], "19155")
        self.assertEqual(self.detail["economic_record_count"], 9)
        self.assertEqual(self.detail["reported_actual_count"], 6)
        self.assertEqual(self.detail["projection_count"], 3)
        self.assertEqual(self.detail["modeled_synthesis_count"], 10)

        records = self.detail["economic_records"]
        actual = {row["claim_id"]: row for row in records if row["basis"] == "reported_actual"}
        forecasts = {row["claim_id"]: row for row in records if row["basis"] == "source_projection"}
        self.assertEqual(actual["clm_study_google_council_bluffs_actual_qualified_investment_2019"]["value"], 1_700_000_000)
        self.assertEqual(actual["clm_study_google_council_bluffs_final_jobs_2019"]["value"], 70)
        self.assertEqual(actual["clm_study_google_council_bluffs_stem_contribution_2019_2023"]["value"], 285_000)
        self.assertEqual(forecasts["clm_study_google_council_bluffs_state_tax_credit_contract_2012"]["value"], 36_600_000)
        self.assertTrue(all(row["period"]["kind"] == "projection_horizon" for row in forecasts.values()))

        taxpayer_stocks = [row for row in actual.values() if row["metric_code"] == "study.taxable_property_value"]
        self.assertEqual([row["value"] for row in taxpayer_stocks], [96_600_000, 61_300_000, 23_900_000])
        self.assertEqual(len({row["scope"]["label"] for row in taxpayer_stocks}), 3)

        gate = self.detail["model_completeness"]
        self.assertEqual(gate["status"], "full_modeled_account")
        self.assertEqual(len(gate["covered_categories"]), 8)
        self.assertEqual(len(gate["covered_county_outcomes"]), 3)
        self.assertEqual(gate["missing_categories"], [])
        self.assertEqual(gate["missing_county_outcomes"], [])

    def test_model_presentation_construction_scope_and_multiplier_provenance(self):
        rows = self.grouped[PROJECT]
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))

        by_id = {row["estimate_id"]: row for row in rows}
        construction_base = by_id["est_study_google_council_bluffs_construction_eligible_spending"]
        self.assertEqual(construction_base["value"], 850_000_000)
        self.assertEqual(construction_base["interval"]["low"], 425_000_000)
        self.assertEqual(construction_base["interval"]["high"], 1_275_000_000)
        self.assertIn("IT equipment", " ".join(construction_base["limitations"]))

        job_rows = [row for row in rows if row["metric_code"].startswith("study.modeled_construction_job_years_")]
        self.assertEqual({row["contribution_channel"] for row in job_rows}, {"direct", "indirect", "induced", "total"})
        self.assertTrue(all(row["derivation"]["method"] == "input_output_multiplier" for row in job_rows))
        self.assertTrue(all(row["multiplier_provenance"]["source_id"] == "src_study_pwc_data_center_market_2021" for row in job_rows))
        self.assertTrue(all(row["multiplier_provenance"]["channel_separation"] == "direct_indirect_induced_reported_separately" for row in job_rows))
        total = next(row for row in job_rows if row["contribution_channel"] == "total")
        self.assertEqual(total["aggregation"]["role"], "total")
        self.assertEqual(len(total["aggregation"]["component_estimate_ids"]), 3)

    def test_resource_allocation_fiscal_safeguards_and_descriptive_comparisons(self):
        rows = self.grouped[PROJECT]
        water = next(row for row in rows if row["metric_code"] == "study.modeled_annual_water_consumption")
        self.assertEqual(water["derivation"]["method"], "allocation")
        self.assertEqual(water["scope"]["inventory_allocation"], "allocated")
        self.assertEqual(water["interval"]["kind"], "sensitivity_envelope")

        forbidden = [
            row for row in rows
            if "net_fiscal" in row["metric_code"] or "service_cost_break_even" in row["metric_code"]
        ]
        self.assertEqual(forbidden, [])
        self.assertFalse(any(row["category"] in {"fiscal", "public_costs"} for row in rows))

        comparison_codes = {
            "study.modeled_county_gdp_comparison_gap",
            "study.modeled_county_employment_comparison_gap",
            "study.modeled_county_wage_comparison_gap",
        }
        comparisons = [row for row in rows if row["metric_code"] in comparison_codes]
        self.assertEqual({row["metric_code"] for row in comparisons}, comparison_codes)
        self.assertTrue(all(row["derivation"]["method"] == "benchmark_application" for row in comparisons))
        self.assertTrue(all("causal_design" not in row for row in comparisons))
        self.assertTrue(all(row["interval"]["kind"] == "sensitivity_envelope" for row in comparisons))
        self.assertTrue(all("fit sensitivity" in row["interval"]["interpretation"] for row in comparisons))
        self.assertTrue(all("descriptive" in " ".join(row["limitations"]).lower() for row in comparisons))


if __name__ == "__main__":
    unittest.main()
