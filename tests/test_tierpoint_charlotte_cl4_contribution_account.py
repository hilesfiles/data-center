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
        self.assertEqual(len(self.fragment["records"]), 40)
        self.assertTrue(all(row["basis"] == "reported_actual" for row in self.fragment["records"]))
        self.assertFalse(SYNTHESIS_FRAGMENT.exists())
        self.assertEqual(self.project["economic_record_count"], 82)
        self.assertEqual((self.project["reported_actual_count"], self.project["projection_count"]), (82, 0))
        self.assertEqual(self.project["modeled_synthesis_count"], 0)

    def test_building_records_preserve_timing_and_measure_boundaries(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(records["clm_study_tierpoint_cl4_opening_floor_area_2014"]["value"], 39_300)
        self.assertEqual(records["clm_study_tierpoint_cl4_opening_usable_ups_2014"]["value"], 1.215)
        self.assertEqual(records["clm_study_tierpoint_cl4_landlord_floor_area_2020"]["value"], 60_850)
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

    def test_exclusions_and_model_rejections_are_explicit(self):
        notes = " ".join(row["notes"] for row in self.fragment["project_updates"])
        for excluded in (
            "$14.399 million",
            "$425,000",
            "$370,600",
            "$297,000",
            "$575 million",
            "wrong jurisdiction",
            "two versus four generators",
        ):
            self.assertIn(excluded, notes)
        model_notes = self.fragment["project_updates"][-1]["notes"]
        for candidate in (
            "Investment",
            "Construction",
            "Suppliers",
            "Operations",
            "Fiscal",
            "Public costs",
            "Resources",
            "Community",
            "County employment and wages",
            "County GDP",
        ):
            self.assertIn(f"{candidate}: rejected", model_notes)
        self.assertIn("Modeled additions: zero", model_notes)
        self.assertEqual(
            self.project["model_completeness"]["missing_categories"],
            ["community", "investment", "public_costs", "suppliers"],
        )


if __name__ == "__main__":
    unittest.main()
