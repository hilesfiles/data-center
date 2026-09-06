import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00464097467"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class AppleWashoeContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.policy = read(MODELING_POLICY)
        validate_evidence(cls.evidence, cls.candidates["candidates"])
        cls.grouped_models, _ = modeled_products(
            cls.synthesis, cls.candidates["candidates"], cls.evidence, cls.policy
        )
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        cls.index, details, _ = build_products(
            cls.candidates,
            inventory,
            panels,
            "2026-09-06T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            cls.policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT)

    def test_fragment_identity_and_strict_ownership(self):
        evidence_fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        synthesis_fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
        self.assertEqual(evidence_fragment["project_id"], PROJECT)
        self.assertEqual(synthesis_fragment["project_id"], PROJECT)
        self.assertTrue(all(row["project_id"] == PROJECT for row in evidence_fragment["records"]))
        self.assertTrue(all(row["project_id"] == PROJECT for row in evidence_fragment["project_updates"]))
        self.assertTrue(all(row["project_id"] == PROJECT for row in synthesis_fragment["estimates"]))

    def test_gate_counts_and_evidence_state_separation(self):
        project = self.project
        self.assertEqual(project["county_fips"], "32031")
        self.assertEqual(project["economic_record_count"], 12)
        self.assertEqual(project["reported_actual_count"], 6)
        self.assertEqual(project["projection_count"], 6)
        self.assertEqual(project["modeled_synthesis_count"], 9)
        self.assertEqual(project["model_completeness"]["status"], "full_modeled_account")
        self.assertEqual(project["model_completeness"]["missing_categories"], [])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])
        self.assertEqual(
            {row["basis"] for row in project["economic_records"]},
            {"reported_actual", "source_projection"},
        )
        self.assertNotIn("modeled_synthesis", {row["basis"] for row in project["economic_records"]})

    def test_all_account_categories_and_model_presentation(self):
        project = self.project
        rows = [*project["economic_records"], *project["modeled_syntheses"]]
        self.assertTrue(
            {
                "investment",
                "construction",
                "suppliers",
                "operations",
                "fiscal",
                "public_costs",
                "resources",
                "community",
            }
            <= {row["category"] for row in rows}
        )
        models = project["modeled_syntheses"]
        self.assertTrue(
            all(row["presentation"] == "modeled_not_observed_or_audited" for row in models)
        )
        self.assertFalse(
            any(
                row["derivation"]["method"]
                in {"difference_in_differences", "event_study", "synthetic_control"}
                for row in models
            )
        )

    def test_construction_base_excludes_equipment_and_preserves_phase_uncertainty(self):
        rows = {row["estimate_id"]: row for row in self.project["modeled_syntheses"]}
        construction = rows["est_study_apple_washoe_construction_eligible_spending"]
        self.assertEqual(construction["value"], 163_000_000)
        self.assertEqual(construction["period"]["kind"], "projection_horizon")
        self.assertEqual(construction["period"]["horizon_years"], 3)
        parameters = {row["name"]: row for row in construction["parameters"]}
        self.assertEqual(parameters["excluded_equipment_projection"]["value"], 742_071_428)
        self.assertEqual(
            parameters["excluded_equipment_projection"]["provenance"]["reference_id"],
            "clm_study_apple_washoe_capex_plan",
        )
        multiplier_rows = [
            row
            for row in self.project["modeled_syntheses"]
            if row["estimate_id"].startswith("est_study_apple_washoe_construction_")
            and row["derivation"]["method"] == "input_output_multiplier"
        ]
        self.assertEqual(len(multiplier_rows), 2)
        for row in multiplier_rows:
            self.assertIn(
                "clm_study_apple_washoe_construction_cost_projection_2024",
                row["derivation"]["input_claim_ids"],
            )
            self.assertNotIn(
                "clm_study_apple_washoe_capex_plan", row["derivation"]["input_claim_ids"]
            )
            self.assertEqual(row["contribution_channel"], "direct")

    def test_multiplier_provenance_and_nonoverlap_are_explicit(self):
        multipliers = [
            row
            for row in self.project["modeled_syntheses"]
            if row["derivation"]["method"] in {"input_output_multiplier", "contribution_analysis"}
        ]
        self.assertEqual(len(multipliers), 3)
        required = {
            "source_id",
            "model_name",
            "model_version",
            "geography",
            "vintage",
            "local_purchase_assumption",
            "channel_separation",
        }
        for row in multipliers:
            self.assertEqual(set(row["multiplier_provenance"]), required)
            self.assertEqual(
                row["multiplier_provenance"]["channel_separation"],
                "direct_indirect_induced_reported_separately",
            )
            self.assertFalse(
                any(
                    "switch" in claim_id.lower() or "citadel" in claim_id.lower()
                    for claim_id in row["derivation"]["input_claim_ids"]
                )
            )
        self.assertTrue(
            all(row["scope"].get("county_fips") == "32031" for row in self.project["modeled_syntheses"])
        )

    def test_fiscal_safeguards_omit_net_and_break_even_values(self):
        project = self.project
        fiscal_records = [row for row in project["economic_records"] if row["category"] == "fiscal"]
        self.assertEqual(len(fiscal_records), 1)
        self.assertEqual(fiscal_records[0]["basis"], "source_projection")
        self.assertEqual(fiscal_records[0]["value"], 200_909_110)
        forbidden = {
            "study.modeled_annual_local_service_cost_break_even",
            "study.modeled_latest_project_linked_local_tax_contribution",
            "study.net_fiscal_projection",
        }
        self.assertTrue(forbidden.isdisjoint({row["metric_code"] for row in project["modeled_syntheses"]}))
        self.assertFalse(
            any("net fiscal" in row["label"].lower() for row in project["modeled_syntheses"])
        )

    def test_three_county_comparisons_are_descriptive_fit_sensitivities(self):
        required = {
            "study.modeled_county_gdp_comparison_gap",
            "study.modeled_county_employment_comparison_gap",
            "study.modeled_county_wage_comparison_gap",
        }
        rows = [row for row in self.project["modeled_syntheses"] if row["metric_code"] in required]
        self.assertEqual({row["metric_code"] for row in rows}, required)
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["derivation"]["method"], "benchmark_application")
            self.assertNotIn("causal_design", row)
            self.assertEqual(row["interval"]["kind"], "sensitivity_envelope")
            self.assertIn("fit sensitivity", row["interval"]["interpretation"])
            self.assertIn("descriptive", row["notes"].lower())

    def test_audit_findings_and_resource_scope_are_preserved(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(records["clm_study_apple_washoe_audited_capex_2017"]["value"], 689_829_656)
        self.assertEqual(records["clm_study_apple_washoe_audited_jobs_2017"]["value"], 83)
        self.assertEqual(records["clm_study_apple_washoe_audited_wage_2017"]["value"], 38.42)
        renewable = records["clm_study_apple_washoe_renewable_capacity_2020"]
        self.assertEqual(renewable["value"], 250)
        self.assertEqual(renewable["scope"]["level"], "supporting_infrastructure")
        self.assertEqual(renewable["scope"]["inventory_allocation"], "unallocated")


if __name__ == "__main__":
    unittest.main()
