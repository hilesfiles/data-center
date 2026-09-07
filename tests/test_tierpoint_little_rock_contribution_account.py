import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00388148510"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class TierPointLittleRockContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        candidates = read(CONFIG)
        evidence = load_evidence()
        synthesis = load_synthesis()
        validate_evidence(evidence, candidates["candidates"])
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            candidates,
            inventory,
            panels,
            "2026-09-07T00:00:00+00:00",
            evidence,
            synthesis,
            read(MODELING_POLICY),
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT)

    def test_fragment_identity_and_strict_ownership(self):
        self.assertEqual(self.fragment["project_id"], PROJECT)
        self.assertTrue(all(row["project_id"] == PROJECT for row in self.fragment["records"]))
        self.assertTrue(
            all(row["project_id"] == PROJECT for row in self.fragment["project_updates"])
        )
        self.assertFalse(SYNTHESIS_FRAGMENT.exists())

    def test_direct_records_preserve_source_definitions(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(self.project["economic_record_count"], 27)
        self.assertEqual(self.project["reported_actual_count"], 27)
        self.assertEqual(self.project["projection_count"], 0)
        self.assertEqual(self.project["modeled_synthesis_count"], 0)
        operator = records["clm_study_tierpoint_little_rock_operator_floor_area_2026"]
        raised = records["clm_study_tierpoint_little_rock_raised_floor_area_2024"]
        assessor = records["clm_study_tierpoint_little_rock_assessor_floor_area_2026"]
        self.assertEqual(operator["value"], 30_000)
        self.assertEqual(operator["value_qualifier"], "greater_than")
        self.assertEqual(assessor["value"], 30_970)
        self.assertEqual(assessor["value_qualifier"], "exact")
        self.assertEqual(raised["value"], 9_000)
        self.assertEqual(raised["value_qualifier"], "greater_than")
        self.assertIn("nested", raised["notes"])
        self.assertNotEqual(operator["source_id"], assessor["source_id"])

    def test_description_search_matrix_and_model_decisions_are_explicit(self):
        descriptions = [
            row["project_description"]
            for row in self.fragment["project_updates"]
            if "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(len(descriptions[0].split(". ")), 4)
        self.assertIn("adjacent trampoline/car-wash property", descriptions[0])
        notes = "\n".join(row["notes"] for row in self.fragment["project_updates"])
        for marker in [
            "44L0750200100",
            "202319722",
            "Z-4933-J",
            "60-04506",
            "60002155",
            "4001 Rodney Parham",
            "QACF",
            "Arkansas Transparency",
            "APSC",
            "Central Arkansas Water",
            "Operations Technician I",
            "recipient-side",
            "EPA ECHO/FRS",
            "2001-2024",
            "difference-in-differences",
            "No synthesis fragment is added",
            "8,760 coverage hours",
            "$89,797.97",
            "June 2011 payment remains ambiguous",
        ]:
            self.assertIn(marker, notes)

    def test_account_remains_intentionally_incomplete(self):
        completeness = self.project["model_completeness"]
        self.assertEqual(completeness["status"], "incomplete")
        self.assertEqual(completeness["covered_categories"], ["fiscal", "operations"])
        self.assertEqual(
            completeness["missing_categories"],
            ["community", "construction", "investment", "public_costs", "resources", "suppliers"],
        )
        self.assertEqual(len(completeness["missing_county_outcomes"]), 3)


if __name__ == "__main__":
    unittest.main()
