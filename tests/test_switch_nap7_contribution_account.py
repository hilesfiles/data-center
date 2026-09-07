import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00172739953"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class SwitchNap7ContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.synthesis_fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
        cls.candidates = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        validate_evidence(cls.evidence, cls.candidates["candidates"])
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
            read(MODELING_POLICY),
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT)

    def test_fragment_identity_and_strict_ownership(self):
        self.assertEqual(self.fragment["project_id"], PROJECT)
        self.assertTrue(all(row["project_id"] == PROJECT for row in self.fragment["records"]))
        self.assertTrue(
            all(row["project_id"] == PROJECT for row in self.fragment["project_updates"])
        )
        self.assertEqual(self.synthesis_fragment["project_id"], PROJECT)
        self.assertTrue(
            all(row["project_id"] == PROJECT for row in self.synthesis_fragment["estimates"])
        )

    def test_direct_additions_preserve_evidence_states_and_boundaries(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(self.project["economic_record_count"], 16)
        self.assertEqual(self.project["reported_actual_count"], 16)
        self.assertEqual(self.project["projection_count"], 0)
        self.assertEqual(self.project["modeled_synthesis_count"], 1)
        self.assertEqual(records["clm_study_switch_nap7_floor_area_2014"]["value"], 400_000)
        self.assertEqual(
            records["clm_study_switch_nap7_floor_area_2014"]["value_qualifier"],
            "at_least",
        )
        self.assertEqual(
            records["clm_study_switch_nap7_permitted_generators_2022"]["value"], 31
        )
        self.assertEqual(records["clm_study_switch_nap7_permit_bd20_28271"]["value"], 200_000)
        self.assertEqual(
            records["clm_study_switch_nap7_property_taxes_billed_2027"]["value"],
            912_973.28,
        )
        partial = records["clm_study_switch_nap7_property_taxes_paid_partial_2027"]
        self.assertEqual(partial["value"], 228_624.01)
        self.assertIn("partial-year", partial["notes"])
        gift = records["clm_study_switch_unlv_dark_fiber_gift_2016"]
        self.assertEqual(gift["value"], 3_000_000)
        self.assertEqual(gift["scope"]["level"], "company_county")
        self.assertEqual(gift["scope"]["inventory_allocation"], "unallocated")

    def test_only_retained_model_is_assessed_liability_break_even(self):
        estimates = self.synthesis_fragment["estimates"]
        self.assertEqual(len(estimates), 1)
        estimate = estimates[0]
        self.assertEqual(estimate["category"], "public_costs")
        self.assertEqual(
            estimate["metric_code"],
            "study.modeled_annual_local_service_cost_break_even",
        )
        self.assertEqual(estimate["value"], 912_973.28)
        self.assertEqual(estimate["scope"]["level"], "campus")
        self.assertEqual(estimate["interval"]["low"], estimate["interval"]["high"])
        self.assertIn("not an estimate of actual public cost", estimate["limitations"][0])
        self.assertIn("No positive or negative net fiscal result", estimate["limitations"][-1])
        self.assertEqual(
            estimate["derivation"]["input_claim_ids"],
            ["clm_study_switch_nap7_property_taxes_billed_2027"],
        )

    def test_baseline_records_and_nonallocation_are_preserved(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        expected_baseline = {
            "clm_study_switch_nap7_taxable_property_value_fy2026",
            "clm_study_switch_nap7_account_assessed_value_fy2026",
            "clm_study_switch_nap7_taxable_property_value_fy2027",
            "clm_study_switch_nap7_account_assessed_value_fy2027",
            "clm_study_switch_core_capex_2017",
            "clm_study_switch_core_capex_2018",
            "clm_study_switch_core_capex_2021_q1",
            "clm_study_switch_core_capex_2021_q2",
            "clm_study_switch_core_capex_2021_q3",
            "clm_study_switch_core_capex_2021_q4",
        }
        self.assertTrue(expected_baseline.issubset(records))
        core_capex = [
            row
            for row in self.project["economic_records"]
            if row["metric_code"] == "study.campus_capital_expenditure"
        ]
        self.assertEqual(len(core_capex), 6)
        self.assertTrue(all("no allocation to NAP7" in row["scope"]["label"] for row in core_capex))
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in core_capex)
        )

    def test_description_search_audit_and_residual_gaps_are_explicit(self):
        descriptions = [
            row["project_description"]
            for row in self.fragment["project_updates"]
            if "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(len(descriptions[0].split(". ")), 3)
        self.assertIn("individual NAP7 building", descriptions[0])
        notes = "\n".join(row["notes"] for row in self.project["research_updates"])
        for marker in [
            "BD20-28271",
            "176-01-810-001",
            "Source 16304",
            "Switch LTD #3",
            "PUCN",
            "Martin-Harris",
            "dark-fiber",
            "2000067-413-103",
            "Great Recession",
            "reCAPTCHA",
        ]:
            self.assertIn(marker, notes)
        self.assertEqual(
            self.project["model_completeness"]["missing_categories"],
            ["suppliers"],
        )
        self.assertEqual(len(self.project["model_completeness"]["missing_county_outcomes"]), 3)


if __name__ == "__main__":
    unittest.main()
