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

    def test_project_identity_evidence_states_and_incomplete_account_gate(self):
        self.assertEqual(self.detail["project_id"], PROJECT)
        self.assertEqual(self.detail["county_fips"], "19155")
        self.assertEqual(self.detail["economic_record_count"], 31)
        self.assertEqual(self.detail["reported_actual_count"], 27)
        self.assertEqual(self.detail["projection_count"], 4)
        self.assertEqual(self.detail["modeled_synthesis_count"], 8)

        records = self.detail["economic_records"]
        actual = {row["claim_id"]: row for row in records if row["basis"] == "reported_actual"}
        forecasts = {row["claim_id"]: row for row in records if row["basis"] == "source_projection"}
        self.assertEqual(actual["clm_study_google_council_bluffs_actual_qualified_investment_2019"]["value"], 1_700_000_000)
        self.assertEqual(actual["clm_study_google_council_bluffs_final_jobs_2019"]["value"], 70)
        self.assertEqual(actual["clm_study_google_council_bluffs_actual_qualified_investment_2012"]["value"], 300_000_000)
        self.assertEqual(actual["clm_study_google_council_bluffs_final_jobs_2012"]["value"], 60)
        self.assertEqual(forecasts["clm_study_google_council_bluffs_state_tax_credit_contract_2012"]["value"], 36_600_000)
        self.assertEqual(forecasts["clm_study_google_council_bluffs_state_tax_credit_contract_2007"]["value"], 1_406_250)
        self.assertTrue(all(row["period"]["kind"] == "projection_horizon" for row in forecasts.values()))

        gate = self.detail["model_completeness"]
        self.assertEqual(gate["status"], "incomplete")
        self.assertEqual(gate["missing_categories"], ["suppliers"])
        self.assertEqual(gate["missing_county_outcomes"], [])
        self.assertEqual(set(gate["modeled_categories"]), {"construction", "resources"})

    def test_second_pass_parcel_permit_tax_and_community_observations(self):
        records = {row["claim_id"]: row for row in self.detail["economic_records"]}
        self.assertEqual(records["clm_study_google_cb_bunge_electrical_permit_value_2025"]["value"], 92_462_323)
        self.assertEqual(records["clm_study_google_council_bluffs_tetra_cooling_permit_value_2025"]["value"], 9_060_288)

        self.assertEqual(records["clm_study_google_tetra_assessed_value_2024"]["value"], 60_934_800)
        self.assertEqual(records["clm_study_google_tetra_taxable_value_2024"]["value"], 54_777_467)
        self.assertEqual(records["clm_study_google_questa_assessed_value_2025"]["value"], 438_398_000)
        self.assertEqual(records["clm_study_google_questa_taxable_value_2025"]["value"], 394_490_002)
        self.assertEqual(records["clm_study_google_questa_property_taxes_billed_2025"]["value"], 14_710_524)

        paid = sorted(
            (row["period"]["year"], row["value"])
            for row in records.values()
            if row["metric_code"] == "study.property_taxes_paid"
        )
        self.assertEqual(paid, [
            (2018, 881_640), (2019, 876_638), (2020, 903_970), (2021, 895_088),
            (2022, 907_082), (2023, 1_365_420), (2024, 2_063_852),
        ])
        self.assertFalse(any(year == 2025 for year, _ in paid))
        tetra_2025_bill = records["clm_study_google_tetra_property_taxes_billed_2025"]
        self.assertIn("Billed amount, not paid", tetra_2025_bill["notes"])
        self.assertEqual(records["clm_study_google_iowa_western_computing_center_grant_2011"]["value"], 100_000)

    def test_audit_log_covers_required_source_families_and_negative_results(self):
        updates = [row for row in self.evidence["project_updates"] if row["project_id"] == PROJECT]
        text = " ".join(row["title"] + " " + row["notes"] for row in updates).lower()
        for phrase in [
            "assessor", "treasurer", "permit", "contractor", "sewer", "abatement",
            "ieda", "revenue", "water", "electric", "workforce", "community",
            "no invoices", "no project-specific exemption", "no facility load",
        ]:
            self.assertIn(phrase, text)

        source_ids = {row["source_id"] for row in self.evidence["sources"]}
        self.assertTrue({
            "src_study_pottawattamie_tax_tetra_744411476005",
            "src_study_pottawattamie_tax_questa_744333101001",
            "src_study_pottawattamie_gis_google_parcels_2026",
            "src_study_council_bluffs_permits_2025_09",
            "src_study_iowa_ieda_2016_google_council_bluffs",
            "src_study_iowa_dor_data_center_incentives_2025",
            "src_study_google_environmental_report_2025",
        }.issubset(source_ids))

    def test_permit_anchored_multiplier_models_and_removed_weak_models(self):
        rows = self.grouped[PROJECT]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))
        by_id = {row["estimate_id"]: row for row in rows}
        self.assertNotIn("est_study_google_council_bluffs_construction_eligible_spending", by_id)
        self.assertNotIn("est_study_google_council_bluffs_local_construction_spending", by_id)
        self.assertFalse(any(row["category"] == "suppliers" for row in rows))

        job_rows = [row for row in rows if row["metric_code"].startswith("study.modeled_construction_job_years_")]
        self.assertEqual({row["contribution_channel"] for row in job_rows}, {"direct", "indirect", "induced", "total"})
        self.assertEqual(
            {row["contribution_channel"]: row["value"] for row in job_rows},
            {"direct": 626.49, "indirect": 150.25, "induced": 111.12, "total": 888.23},
        )
        self.assertTrue(all(row["interval"]["kind"] == "point_estimate" for row in job_rows))
        self.assertTrue(all(row["derivation"]["method"] == "input_output_multiplier" for row in job_rows))
        self.assertTrue(all(set(row["derivation"]["input_claim_ids"]) == {
            "clm_study_google_cb_bunge_electrical_permit_value_2025",
            "clm_study_google_council_bluffs_tetra_cooling_permit_value_2025",
        } for row in job_rows))
        self.assertTrue(all("no pottawattamie county supplier share" in row["multiplier_provenance"]["local_purchase_assumption"].lower() for row in job_rows))
        total = next(row for row in job_rows if row["contribution_channel"] == "total")
        self.assertEqual(total["aggregation"]["role"], "total")
        self.assertEqual(len(total["aggregation"]["component_estimate_ids"]), 3)

    def test_unallocated_water_fiscal_safeguards_and_descriptive_comparisons(self):
        rows = self.grouped[PROJECT]
        water = next(row for row in rows if row["metric_code"] == "study.modeled_annual_water_consumption")
        self.assertEqual(water["value"], 1_010_200_000)
        self.assertEqual(water["derivation"]["method"], "engineering_estimate")
        self.assertEqual(water["scope"]["inventory_allocation"], "unallocated")
        self.assertNotIn("allocation_method", water["scope"])
        self.assertEqual(water["interval"]["kind"], "point_estimate")

        self.assertFalse(any(
            "net_fiscal" in row["metric_code"] or "service_cost_break_even" in row["metric_code"]
            for row in rows
        ))
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
