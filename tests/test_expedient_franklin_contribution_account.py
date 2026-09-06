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
            (12, 11, 1),
        )
        self.assertEqual(project["modeled_synthesis_count"], 15)
        self.assertEqual(project["model_completeness"]["status"], "full_modeled_account")
        self.assertEqual(project["model_completeness"]["missing_categories"], [])
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

        components = [
            rows["est_study_expedient_franklin_construction_job_years_direct"],
            rows["est_study_expedient_franklin_construction_job_years_indirect"],
            rows["est_study_expedient_franklin_construction_job_years_induced"],
        ]
        total = rows["est_study_expedient_franklin_construction_job_years_total"]
        self.assertEqual([row["contribution_channel"] for row in components], ["direct", "indirect", "induced"])
        self.assertEqual(total["aggregation"]["role"], "total")
        self.assertEqual(set(total["aggregation"]["component_estimate_ids"]), {row["estimate_id"] for row in components})
        self.assertTrue(all(row["aggregation"]["role"] == "component" for row in components))

    def test_model_presentation_multiplier_provenance_and_comparisons(self):
        grouped, _ = modeled_products(
            self.synthesis,
            self.config["candidates"],
            self.evidence,
            self.policy,
        )
        rows = grouped[PROJECT_ID]
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))

        multiplier_rows = [row for row in rows if row["derivation"]["method"] == "input_output_multiplier"]
        self.assertGreaterEqual(len(multiplier_rows), 6)
        required = {
            "source_id",
            "model_name",
            "model_version",
            "geography",
            "vintage",
            "local_purchase_assumption",
            "channel_separation",
        }
        self.assertTrue(all(required <= set(row["multiplier_provenance"]) for row in multiplier_rows))
        self.assertTrue(all(
            row["multiplier_provenance"]["channel_separation"] == "direct_indirect_induced_reported_separately"
            for row in multiplier_rows
        ))

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
        tax = rows["est_study_expedient_franklin_latest_local_tax_contribution"]
        threshold = rows["est_study_expedient_franklin_annual_local_service_cost_break_even"]
        self.assertEqual(tax["value"], 60_347.17)
        self.assertEqual(threshold["value"], tax["value"])
        self.assertIn("not an estimate of actual public-service cost", threshold["interval"]["interpretation"])
        self.assertIn("No net fiscal result", threshold["notes"])
        self.assertFalse(any("net_fiscal" in row["metric_code"] for row in rows.values()))
        self.assertFalse(any(
            row["category"] == "public_costs"
            and row["metric_code"] != "study.modeled_annual_local_service_cost_break_even"
            for row in rows.values()
        ))


if __name__ == "__main__":
    unittest.main()
