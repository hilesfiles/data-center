import unittest

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT_ID = "prj_study_im3_building_00664938835"


class ExpedientFranklinContributionAccountTest(unittest.TestCase):
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
        cls.index, details, _ = build_products(
            cls.config,
            cls.inventory,
            cls.panels,
            "2026-09-06T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            cls.policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_project_identity_evidence_states_and_account_gate(self):
        validate_evidence(self.evidence, self.config["candidates"])
        project = self.project
        self.assertEqual((project["project_id"], project["county_fips"]), (PROJECT_ID, "55079"))
        self.assertEqual(
            (project["economic_record_count"], project["reported_actual_count"], project["projection_count"]),
            (16, 15, 1),
        )
        self.assertEqual(project["modeled_synthesis_count"], 7)
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], ["community", "suppliers"])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])
        self.assertTrue(all(row["basis"] != "modeled_synthesis" for row in project["economic_records"]))

    def test_adaptive_reuse_construction_scope_and_overlap_controls(self):
        rows = {row["estimate_id"]: row for row in self.project["modeled_syntheses"]}
        eligible = rows["est_study_expedient_franklin_construction_eligible_spending_2025"]
        self.assertEqual(
            tuple(eligible["interval"][key] for key in ("low", "central", "high")),
            (348_114, 464_152, 580_190),
        )
        self.assertEqual(eligible["derivation"]["input_claim_ids"], ["clm_study_expedient_franklin_permit_pb25_0303"])
        forbidden_inputs = {
            "clm_study_expedient_franklin_permit_pm25_0174",
            "clm_study_expedient_franklin_assessed_value_2025",
            "clm_study_expedient_franklin_operating_jobs_plan_2021",
        }
        self.assertTrue(forbidden_inputs.isdisjoint(eligible["derivation"]["input_claim_ids"]))
        self.assertIn("PM25-0174", " ".join(eligible["derivation"]["assumptions"]))
        removed = {
            "est_study_expedient_franklin_construction_job_years_direct",
            "est_study_expedient_franklin_construction_job_years_indirect",
            "est_study_expedient_franklin_construction_job_years_induced",
            "est_study_expedient_franklin_construction_job_years_total",
            "est_study_expedient_franklin_local_construction_spending_2025",
        }
        self.assertTrue(removed.isdisjoint(rows))
        self.assertIn("not observed spending, a true-value bound", eligible["interval"]["interpretation"])

    def test_model_presentation_multiplier_provenance_and_comparisons(self):
        grouped, _ = modeled_products(
            self.synthesis,
            self.config["candidates"],
            self.evidence,
            self.policy,
        )
        rows = grouped[PROJECT_ID]
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))
        self.assertFalse(any(row["derivation"]["method"] == "input_output_multiplier" for row in rows))
        self.assertEqual(
            {row["estimate_id"] for row in rows},
            {
                "est_study_expedient_franklin_property_transaction_anchor_2022",
                "est_study_expedient_franklin_construction_eligible_spending_2025",
                "est_study_expedient_franklin_annual_local_service_cost_break_even",
                "est_study_expedient_franklin_facility_electricity_2026",
                "est_study_expedient_franklin_gdp_comparison_gap",
                "est_study_expedient_franklin_employment_comparison_gap",
                "est_study_expedient_franklin_wage_comparison_gap",
            },
        )

        comparisons = [row for row in rows if row["category"] == "county_outcome"]
        self.assertEqual(len(comparisons), 3)
        self.assertTrue(all(row["derivation"]["method"] == "benchmark_application" for row in comparisons))
        self.assertTrue(all(row["interval"]["kind"] == "sensitivity_envelope" for row in comparisons))
        self.assertTrue(all("causal_design" not in row for row in comparisons))
        self.assertTrue(all(
            any("must not be interpreted as a data-center effect" in limit for limit in row["limitations"])
            for row in comparisons
        ))
        self.assertTrue(all("fit sensitivity" in row["interval"]["interpretation"] for row in comparisons))

    def test_fiscal_safeguards_omit_forbidden_cost_and_net_results(self):
        rows = {row["estimate_id"]: row for row in self.project["modeled_syntheses"]}
        threshold = rows["est_study_expedient_franklin_annual_local_service_cost_break_even"]
        self.assertNotIn("est_study_expedient_franklin_latest_local_tax_contribution", rows)
        self.assertEqual(threshold["value"], 60_347.17)
        self.assertIn("not an estimate of actual public-service cost", threshold["interval"]["interpretation"])
        self.assertIn("No net fiscal result", threshold["notes"])
        tax_records = sorted(
            (
                row["period"]["year"],
                row["value"],
            )
            for row in self.project["economic_records"]
            if row["metric_code"] == "study.property_taxes_paid"
        )
        self.assertEqual(
            tax_records,
            [
                (2021, 62_597.21),
                (2022, 62_898.28),
                (2023, 58_761.16),
                (2024, 56_371.29),
                (2025, 60_347.17),
            ],
        )
        self.assertFalse(any("net_fiscal" in row["metric_code"] for row in rows.values()))
        self.assertFalse(any(
            row["category"] == "public_costs"
            and row["metric_code"] != "study.modeled_annual_local_service_cost_break_even"
            for row in rows.values()
        ))

    def test_second_pass_documents_all_eight_search_categories(self):
        source_ids = {row["source_id"] for row in self.evidence["sources"]}
        self.assertTrue(
            {
                "src_study_franklin_common_council_csm_2012",
                "src_study_wisconsin_dor_qualified_data_centers_2026",
                "src_study_wisconsin_psc_data_center_scope_2026",
                "src_study_expedient_sustainability_2026",
                "src_study_expedient_careers_milwaukee_2026",
                "src_study_cogent_expedient_mke1_2026",
                "src_study_franklin_building_permit_application_2026",
                "src_study_milwaukee_county_register_deeds_2026",
            }
            <= source_ids
        )
        updates = [row for row in self.evidence["project_updates"] if row["project_id"] == PROJECT_ID]
        self.assertEqual(len(updates), 8)
        self.assertEqual(
            {row["title"].split(" audit", 1)[0] for row in updates},
            {"Construction", "Operations", "Fiscal", "Community", "Investment", "Public-cost", "Resource", "Supplier"},
        )
        self.assertTrue(all("Source families checked:" in row["notes"] for row in updates))
        self.assertTrue(all("2026-09-06" == row["as_of"] for row in updates))


if __name__ == "__main__":
    unittest.main()
