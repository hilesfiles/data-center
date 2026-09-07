import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00438078069"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class MetaAltoonaContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
        config = read_json(ROOT / "config/v1/private-sector-study-candidates.json")
        inventory = {row["entity_id"]: row for row in read_json(ROOT / "site/public/data/v1/facilities/index.json")}
        panels = {}
        for path in sorted((ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")):
            for row in read_json(path):
                panels[row["county_fips"]] = row
        policy = read_json(ROOT / "config/v1/study-modeling-policy.json")
        _, details, _ = build_products(
            config,
            inventory,
            panels,
            "2026-09-07T00:00:00+00:00",
            load_evidence(),
            load_synthesis(),
            policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)
        cls.fragment = read_json(EVIDENCE_FRAGMENT)

    def test_direct_account_counts_and_bounded_gaps(self):
        project = self.project
        self.assertEqual(
            (project["economic_record_count"], project["reported_actual_count"], project["projection_count"]),
            (99, 92, 7),
        )
        self.assertEqual(project["modeled_synthesis_count"], 0)
        self.assertFalse(MODEL_FRAGMENT.exists())
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], ["suppliers"])
        self.assertEqual(
            project["model_completeness"]["missing_county_outcomes"],
            [
                "study.modeled_county_employment_comparison_gap",
                "study.modeled_county_gdp_comparison_gap",
                "study.modeled_county_wage_comparison_gap",
            ],
        )

    def test_direct_records_preserve_award_phase_and_resource_boundaries(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(records["clm_study_meta_altoona_ieda_actual_investment_13"]["value"], 4_372_163_473)
        self.assertEqual(records["clm_study_meta_altoona_ieda_actual_investment_19"]["value"], 817_900_000)
        self.assertEqual(records["clm_study_meta_altoona_temporary_building_pilot_projection_2024"]["basis"], "source_projection")
        self.assertEqual(records["clm_study_meta_altoona_electricity_2024"]["value"], 1_585_392_000)
        self.assertEqual(records["clm_study_meta_altoona_permitted_generators_2024"]["value"], 112)
        self.assertEqual(records["clm_study_meta_altoona_assessor_atn1_floor_area_2026"]["value"], 312_131)
        self.assertIn("candidate crosswalk", records["clm_study_meta_altoona_assessor_atn1_floor_area_2026"]["notes"])
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.fragment["records"]))
        self.assertIn("must not be summed", records["clm_study_meta_altoona_community_grants_2015"]["notes"])

    def test_all_active_real_estate_accounts_remain_separate(self):
        active_pins = {
            "792303400004",
            "792310100002",
            "792310200008",
            "792310300006",
            "792310377001",
            "792303400006",
            "792310100004",
            "792310200006",
            "792310200007",
            "792310401005",
        }
        added = self.fragment["records"]
        payments = [row for row in added if row["metric_code"] == "study.property_taxes_paid"]
        taxable = [row for row in added if row["metric_code"] == "study.taxable_assessed_value"]
        appraised = [row for row in added if row["metric_code"] == "study.appraised_property_value"]
        self.assertEqual((len(payments), len(taxable), len(appraised)), (50, 10, 10))
        self.assertEqual({row["scope"]["label"].split("PIN ")[1].split(";")[0] for row in payments}, active_pins)
        self.assertEqual({row["period"]["year"] for row in payments}, set(range(2020, 2025)))
        self.assertFalse(any(row["metric_code"] == "study.property_tax_billed" for row in added))

    def test_description_search_matrix_and_candidate_status_are_explicit(self):
        updates = self.fragment["project_updates"]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertGreaterEqual(len(updates), 14)
        search_log = " ".join(row["notes"].lower() for row in updates)
        for family in (
            "assessor",
            "permit",
            "utility",
            "incentive",
            "supplier",
            "workforce",
            "community",
            "recipient",
            "qcew",
            "gdp",
        ):
            self.assertIn(family, search_log)
        self.assertIn("all 34 results", search_log)
        self.assertIn("do not cover any realized public-cost", updates[-1]["notes"].lower())
        self.assertIn("candidate_corrected_pending_adversarial_review", updates[-1]["notes"])
        self.assertIn("zero modeled records", search_log)


if __name__ == "__main__":
    unittest.main()
