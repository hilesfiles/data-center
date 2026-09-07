import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00626785488"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class MetaLosLunasContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
        config = read_json(ROOT / "config/v1/private-sector-study-candidates.json")
        inventory = {
            row["entity_id"]: row
            for row in read_json(ROOT / "site/public/data/v1/facilities/index.json")
        }
        panels = {}
        for path in sorted((ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")):
            for row in read_json(path):
                panels[row["county_fips"]] = row
        policy = read_json(ROOT / "config/v1/study-modeling-policy.json")
        _, details, _ = build_products(
            config,
            inventory,
            panels,
            "2026-09-06T00:00:00+00:00",
            load_evidence(),
            load_synthesis(),
            policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)
        cls.fragment = read_json(EVIDENCE_FRAGMENT)

    def test_corrective_audit_counts_and_model_gate(self):
        project = self.project
        self.assertEqual(len(self.fragment["sources"]), 40)
        self.assertEqual(len(self.fragment["records"]), 18)
        self.assertEqual(
            (project["economic_record_count"], project["reported_actual_count"], project["projection_count"]),
            (20, 20, 0),
        )
        self.assertEqual(project["modeled_synthesis_count"], 0)
        self.assertFalse(MODEL_FRAGMENT.exists())
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], ["investment", "suppliers"])
        self.assertEqual(
            project["model_completeness"]["missing_county_outcomes"],
            [
                "study.modeled_county_employment_comparison_gap",
                "study.modeled_county_gdp_comparison_gap",
                "study.modeled_county_wage_comparison_gap",
            ],
        )

    def test_new_direct_records_are_unallocated_and_non_additive(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        jobs = records["clm_study_meta_los_lunas_jobs_supported_2026"]
        funding = records["clm_study_meta_los_lunas_community_funding_2026"]
        united_way = records["clm_study_meta_los_lunas_uwncnm_contribution_2025"]
        self.assertEqual((jobs["value"], jobs["value_qualifier"]), (400, "greater_than"))
        self.assertEqual((funding["value"], funding["value_qualifier"]), (6_200_000, "greater_than"))
        self.assertEqual((united_way["value"], united_way["value_qualifier"]), (5_000, "at_least"))
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in records.values()))
        self.assertIn("must not be summed", funding["notes"])
        self.assertIn("non-additive", united_way["notes"])

    def test_each_model_candidate_has_a_separate_ineligibility_decision(self):
        expected_titles = {
            *(f"Model candidate - {category}: ineligible" for category in (
                "investment", "construction", "suppliers", "operations",
                "fiscal", "public costs", "resources", "community",
            )),
            *(f"Outcome model candidate - {outcome}: ineligible" for outcome in ("GDP", "employment", "wages")),
        }
        decisions = {
            row["title"]: row
            for row in self.fragment["project_updates"]
            if "candidate" in row["title"]
        }
        self.assertEqual(set(decisions), expected_titles)
        self.assertTrue(all("No " in row["notes"] for row in decisions.values()))

    def test_description_and_source_family_search_trail_are_complete(self):
        updates = self.fragment["project_updates"]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual(len(updates), 24)
        search_log = " ".join(row["notes"].lower() for row in updates)
        for family in (
            "bond", "assessor", "treasurer", "permit", "court", "utility",
            "water", "wastewater", "contractor", "supplier", "community",
            "recipient", "gdp", "qcew", "employment", "wage",
        ):
            self.assertIn(family, search_log)


if __name__ == "__main__":
    unittest.main()
