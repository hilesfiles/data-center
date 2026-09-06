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
        self.assertEqual(project["economic_record_count"], 21)
        self.assertEqual(project["reported_actual_count"], 15)
        self.assertEqual(project["projection_count"], 6)
        self.assertEqual(project["modeled_synthesis_count"], 7)
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], ["suppliers"])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])
        self.assertEqual(
            {row["basis"] for row in project["economic_records"]},
            {"reported_actual", "source_projection"},
        )
        self.assertNotIn("modeled_synthesis", {row["basis"] for row in project["economic_records"]})

    def test_all_account_categories_and_model_presentation(self):
        project = self.project
        rows = [*project["economic_records"], *project["modeled_syntheses"]]
        categories = {row["category"] for row in rows}
        self.assertEqual(
            categories,
            {
                "investment",
                "construction",
                "operations",
                "fiscal",
                "public_costs",
                "resources",
                "community",
                "county_outcome",
            },
        )
        self.assertNotIn("suppliers", categories)
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
            self.assertEqual(row["evidence_search"]["direct_observation_status"], "partial")
            self.assertEqual(
                {p["value"] for p in row["parameters"] if p["name"].endswith("transfer_factor")},
                {0.5, 1, 1.5},
            )

    def test_multiplier_provenance_and_nonoverlap_are_explicit(self):
        multipliers = [
            row
            for row in self.project["modeled_syntheses"]
            if row["derivation"]["method"] in {"input_output_multiplier", "contribution_analysis"}
        ]
        self.assertEqual(len(multipliers), 2)
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
        self.assertEqual(len(fiscal_records), 3)
        forecast = next(row for row in fiscal_records if row["basis"] == "source_projection")
        self.assertEqual(forecast["value"], 200_909_110)
        assessed = [row for row in fiscal_records if row["metric_code"] == "study.account_assessed_value"]
        self.assertEqual([row["value"] for row in assessed], [109_529_832, 147_033_277])
        self.assertFalse(
            any(
                row["metric_code"] in {"study.property_taxes_billed", "study.property_taxes_paid"}
                for row in fiscal_records
            )
        )
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

    def test_second_pass_direct_records_keep_units_scopes_and_nonadditivity(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        permits = [
            records["clm_study_apple_washoe_permit_huckleberry_phase1_2017"],
            records["clm_study_apple_washoe_permit_huckleberry_phase2_2017"],
            records["clm_study_apple_washoe_permit_isabel_2018"],
        ]
        self.assertEqual(
            [row["value"] for row in permits],
            [37_913_134.77, 9_140_880, 50_720_905.86],
        )
        self.assertTrue(all(row["metric_code"] == "study.permitted_construction_value" for row in permits))
        self.assertTrue(
            all(
                "not" in row["notes"].lower()
                and any(word in row["notes"].lower() for word in {"sum", "add"})
                for row in permits
            )
        )

        water = records["clm_study_apple_washoe_water_right_capacity_2015"]
        self.assertAlmostEqual(water["value"], 0.111592808)
        self.assertEqual(water["unit"], "million_gallons_per_day")
        self.assertIn("not measured", water["notes"].lower())

        electricity = records["clm_study_apple_washoe_electricity_use_2025"]
        self.assertEqual(electricity["value"], 422_000_000)
        self.assertEqual(electricity["scope"]["level"], "campus")
        self.assertEqual(electricity["annual_series_key"], "apple_washoe_electricity_use")

        gifts = [
            records["clm_study_apple_fbnn_contribution_floor_2022"],
            records["clm_study_apple_fbnn_contribution_floor_2023"],
        ]
        self.assertTrue(all(row["value"] == 10_000 for row in gifts))
        self.assertTrue(all(row["value_qualifier"] == "at_least" for row in gifts))
        self.assertTrue(all(row["scope"]["level"] == "company_county" for row in gifts))

    def test_search_audit_is_explicit_and_unsupported_models_are_pruned(self):
        notes = "\n".join(row["notes"] for row in self.project["research_updates"])
        for marker in [
            "15-3589",
            "084-110-29",
            "17-11002",
            "Reno Technology Park",
            "200653833-6172",
            "Food Bank of Northern Nevada",
            "tax-expenditure reports",
        ]:
            self.assertIn(marker, notes)

        estimate_ids = {row["estimate_id"] for row in self.project["modeled_syntheses"]}
        self.assertNotIn("est_study_apple_washoe_local_construction_spending", estimate_ids)
        self.assertNotIn("est_study_apple_washoe_induced_household_output_2024", estimate_ids)
        self.assertEqual(self.project["model_completeness"]["missing_categories"], ["suppliers"])


if __name__ == "__main__":
    unittest.main()
