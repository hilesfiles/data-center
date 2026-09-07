import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00838817907"
FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class TierPointCharlotteCl4ContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.synthesis_fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
        cls.config = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            cls.config,
            inventory,
            panels,
            "2026-09-07T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            read(MODELING_POLICY),
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_fragment_is_valid_scoped_and_direct_only(self):
        self.assertEqual(self.fragment["project_id"], PROJECT_ID)
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment["records"]))
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment["project_updates"]))
        validate_evidence(self.evidence, self.config["candidates"])
        self.assertEqual(len(self.fragment["records"]), 45)
        self.assertTrue(all(row["basis"] == "reported_actual" for row in self.fragment["records"]))
        self.assertEqual(self.synthesis_fragment["project_id"], PROJECT_ID)
        self.assertEqual(len(self.synthesis_fragment["estimates"]), 3)
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.synthesis_fragment["estimates"]))
        self.assertEqual(self.project["economic_record_count"], 87)
        self.assertEqual((self.project["reported_actual_count"], self.project["projection_count"]), (87, 0))
        self.assertEqual(self.project["modeled_synthesis_count"], 3)

    def test_building_records_preserve_timing_and_measure_boundaries(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(records["clm_study_tierpoint_cl4_opening_floor_area_2014"]["value"], 39_300)
        self.assertEqual(records["clm_study_tierpoint_cl4_opening_raised_floor_area_2014"]["value"], 10_380)
        self.assertEqual(records["clm_study_tierpoint_cl4_opening_usable_ups_2014"]["value"], 1.215)
        self.assertEqual(records["clm_study_tierpoint_cl4_landlord_floor_area_2020"]["value"], 60_850)
        self.assertEqual(
            (
                records["clm_study_tierpoint_cl4_current_total_floor_area_2026"]["value"],
                records["clm_study_tierpoint_cl4_current_total_floor_area_2026"]["value_qualifier"],
            ),
            (60_000, "at_least"),
        )
        self.assertEqual(
            (
                records["clm_study_tierpoint_cl4_current_raised_floor_area_2026"]["value"],
                records["clm_study_tierpoint_cl4_current_raised_floor_area_2026"]["value_qualifier"],
            ),
            (20_000, "at_least"),
        )
        self.assertEqual(records["clm_study_tierpoint_cl4_spec_total_floor_area_2024"]["value"], 60_000)
        self.assertEqual(records["clm_study_tierpoint_cl4_spec_production_floor_area_2024"]["value_qualifier"], "at_least")
        permit = records["clm_study_tierpoint_cl4_permitted_construction_value_2021"]
        self.assertEqual(permit["value"], 2_580_200)
        self.assertIn("administrative", permit["notes"])
        claim_ids = " ".join(records)
        for excluded in ("14399000", "425000", "370600", "297000", "575000000"):
            self.assertNotIn(excluded, claim_ids)

    def test_county_business_patterns_are_complete_context_not_cl4_claims(self):
        records = self.fragment["records"]
        county = [row for row in records if row["scope"]["level"] == "county_context"]
        self.assertEqual(len(county), 36)
        self.assertEqual({row["period"]["year"] for row in county}, set(range(2012, 2024)))
        self.assertEqual(
            {row["metric_code"] for row in county},
            {
                "study.county_industry_establishments",
                "study.county_industry_employment",
                "study.county_industry_annual_payroll",
            },
        )
        employment = {
            row["period"]["year"]: row["value"]
            for row in county
            if row["metric_code"] == "study.county_industry_employment"
        }
        payroll = {
            row["period"]["year"]: row["value"]
            for row in county
            if row["metric_code"] == "study.county_industry_annual_payroll"
        }
        self.assertEqual((employment[2012], employment[2023]), (1_744, 3_505))
        self.assertEqual((payroll[2012], payroll[2023]), (132_728_000, 313_468_000))
        self.assertTrue(all("not CL4" in row["notes"] or "not a project contribution" in row["notes"] for row in county))
        operations_gap = next(row for row in self.project["evidence_gaps"] if row["code"] == "operations")
        self.assertEqual(operations_gap["status"], "partial")
        self.assertIn("cannot establish CL4 employment", self.fragment["scope_note"])

    def test_description_and_all_evidence_families_are_auditable(self):
        descriptions = [row["project_description"] for row in self.fragment["project_updates"] if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual(len([part for part in descriptions[0].split(". ") if part]), 4)
        self.assertIn("1805 Center Park Drive", descriptions[0])
        self.assertIn("Charlotte-North Myers", descriptions[0])
        updates = self.fragment["project_updates"]
        self.assertEqual(len(updates), 12)
        self.assertEqual(
            {row["title"] for row in updates[:8]},
            {
                "Investment audit and project boundary",
                "Construction audit",
                "Supplier audit",
                "Operations audit",
                "Fiscal audit",
                "Public-cost audit",
                "Resource audit",
                "Community audit",
            },
        )
        self.assertTrue(all(row["as_of"] == "2026-09-07" for row in updates))
        self.assertTrue(all("Source families checked:" in row["notes"] for row in updates[:8]))
        source_ids = {row["source_id"] for row in self.fragment["sources"]}
        self.assertEqual(len(source_ids), 36)
        self.assertEqual(len([source_id for source_id in source_ids if not source_id.startswith("src_study_census_cbp_")]), 24)
        self.assertTrue(
            {
                "src_study_windstream_charlotte_four_opening_2014",
                "src_study_sfr_cl4_groundbreaking_2013",
                "src_study_mapletree_cl4_valuation_2020",
                "src_study_sec_cl4_lease_schedule_2017",
                "src_study_mecklenburg_accela_cl4_2026",
                "src_study_mecklenburg_cl4_permit_b3960984_2021",
                "src_study_mecklenburg_air_permit_database_2026",
                "src_study_ncdor_data_center_exemption_repeal_2026",
                "src_study_ncuc_cl4_docket_search_2026",
                "src_study_tierpoint_green_finance_2024",
            }.issubset(source_ids)
        )

    def test_exclusions_models_and_remaining_rejections_are_explicit(self):
        notes = " ".join(row["notes"] for row in self.fragment["project_updates"])
        for excluded in (
            "$14.399 million",
            "$425,000",
            "$370,600",
            "$297,000",
            "$575 million",
            "wrong jurisdiction",
            "four-versus-two",
        ):
            self.assertIn(excluded, notes)
        model_notes = self.fragment["project_updates"][-1]["notes"]
        for candidate in (
            "Investment",
            "Construction",
            "Suppliers",
            "Fiscal",
            "Public costs",
            "Community",
            "County employment and wages",
            "County GDP",
        ):
            self.assertIn(f"{candidate}: rejected", model_notes)
        self.assertIn("Modeled additions: three", model_notes)
        estimates = {row["estimate_id"]: row for row in self.synthesis_fragment["estimates"]}
        self.assertEqual(
            estimates["est_study_tierpoint_cl4_minimum_noc_coverage_fte_2014"]["interval"],
            {
                "kind": "sensitivity_envelope",
                "low": 4.2115384615,
                "central": 4.8432692308,
                "high": 5.475,
                "interpretation": "Low, central and high apply 0%, 15% and 30% relief factors to the theoretical 8,760 annual coverage hours divided by 2,080 paid hours per FTE. This is the staffing capacity for one simultaneous post, not an observed employee-count interval.",
            },
        )
        self.assertIn(
            "not added",
            " ".join(estimates["est_study_tierpoint_cl4_minimum_security_coverage_fte_2026"]["limitations"]),
        )
        energy = estimates["est_study_tierpoint_cl4_opening_electricity_sensitivity_2014"]
        self.assertEqual((energy["interval"]["low"], energy["value"], energy["interval"]["high"]), (3_193_020, 7_450_380, 12_772_080))
        self.assertIn("not actual annual consumption", energy["notes"])
        resource_notes = next(row["notes"] for row in self.fragment["project_updates"] if row["title"] == "Resource audit")
        self.assertIn("530 refrigeration tons x 12,000 Btu/hour", resource_notes)
        for proposed in (
            "study.operating_utility_service_capacity_kva",
            "study.operating_cooling_capacity_tons",
            "study.installed_emergency_generator_count",
            "study.emergency_fuel_storage_capacity_gallons",
        ):
            self.assertIn(proposed, self.fragment["scope_note"])
        self.assertEqual(
            self.project["model_completeness"]["missing_categories"],
            ["community", "investment", "public_costs", "suppliers"],
        )


if __name__ == "__main__":
    unittest.main()
