import json
import re
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_point_06685432442"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class SwitchCitadelContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
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

    def test_scoped_fragment_counts_and_evidence_states(self):
        self.assertEqual(self.fragment["project_id"], PROJECT)
        self.assertEqual(len(self.fragment["sources"]), 15)
        self.assertEqual(len(self.fragment["records"]), 10)
        self.assertEqual(len(self.fragment["project_updates"]), 14)
        self.assertEqual(
            sum(row["basis"] == "reported_actual" for row in self.fragment["records"]),
            9,
        )
        self.assertEqual(
            sum(row["basis"] == "source_projection" for row in self.fragment["records"]),
            1,
        )
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.fragment["records"])
        )
        self.assertEqual(
            (
                self.project["economic_record_count"],
                self.project["reported_actual_count"],
                self.project["projection_count"],
            ),
            (86, 78, 8),
        )

    def test_current_goed_tax_and_sec_records_are_bounded(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(records["clm_study_switch_storey_audit_jobs_2020_rev2025"]["value"], 324)
        self.assertEqual(records["clm_study_switch_storey_audit_capex_2020_rev2025"]["value"], 452_372_959)
        self.assertIn("identical", records["clm_study_switch_storey_audit_capex_2020_rev2025"]["notes"])
        self.assertEqual(records["clm_study_switch_citadel_taxable_value_2027"]["value"], 313_997_081)
        self.assertIn("no bill is derived", records["clm_study_switch_citadel_taxable_value_2027"]["notes"])
        self.assertEqual(records["clm_study_switch_citadel_capex_2021_q1"]["value"], 59_600_000)
        self.assertEqual(records["clm_study_switch_citadel_capex_2021_q3"]["value"], 48_200_000)
        self.assertEqual(records["clm_study_switch_citadel_capex_2021_q4"]["value"], 37_800_000)
        self.assertTrue(
            all(
                "not used in the revised capital-floor model" in records[claim]["notes"]
                for claim in (
                    "clm_study_switch_citadel_capex_2021_q1",
                    "clm_study_switch_citadel_capex_2021_q3",
                    "clm_study_switch_citadel_capex_2021_q4",
                )
            )
        )
        gift = records["clm_study_switch_unr_hpc_services_commitment_2017"]
        self.assertEqual((gift["value"], gift["value_qualifier"]), (3_400_000, "greater_than"))
        self.assertEqual(gift["basis"], "source_projection")

    def test_superseded_direct_claims_have_atomic_removal_directive(self):
        update = next(row for row in self.fragment["project_updates"] if row["title"].startswith("GOED audit"))
        self.assertIn("ORCHESTRATOR REMOVAL DIRECTIVE", update["notes"])
        for claim_id in (
            "clm_study_switch_storey_audit_jobs_2020",
            "clm_study_switch_storey_audit_wage_2020",
            "clm_study_switch_storey_audit_capex_2020",
        ):
            self.assertIn(claim_id, update["notes"])

    def test_all_34_legacy_models_have_one_explicit_disposition(self):
        current_ids = {
            row["estimate_id"]
            for row in self.synthesis["estimates"]
            if row["project_id"] == PROJECT
        }
        self.assertEqual(len(current_ids), 4)
        update = next(
            row for row in self.fragment["project_updates"]
            if row["title"].startswith("Legacy synthesis disposition")
        )
        decisions = re.findall(r"(?:^|\s)\d{2} (est_study_[a-z0-9_]+) — (RETAIN|REVISE|REMOVE)", update["notes"])
        self.assertEqual(len(decisions), 34)
        self.assertEqual(len({estimate_id for estimate_id, _ in decisions}), 34)
        self.assertEqual(
            {estimate_id for estimate_id, decision in decisions if decision == "RETAIN"},
            current_ids,
        )
        self.assertEqual(
            {decision: sum(value == decision for _, value in decisions) for decision in ("RETAIN", "REVISE", "REMOVE")},
            {"RETAIN": 4, "REVISE": 0, "REMOVE": 30},
        )
        self.assertFalse(SYNTHESIS_FRAGMENT.exists())
        self.assertIn("append-only", update["notes"])

    def test_description_and_search_matrix_are_explicit(self):
        descriptions = [
            row["project_description"]
            for row in self.fragment["project_updates"]
            if "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        search_log = " ".join(row["notes"].lower() for row in self.fragment["project_updates"])
        for marker in (
            "assessor", "treasurer", "budget", "permit", "inspection", "utility",
            "water", "wastewater", "contractor", "supplier", "community", "recipient",
            "recorder", "bond", "gdp", "qcew", "employment", "wage",
        ):
            self.assertIn(marker, search_log)


if __name__ == "__main__":
    unittest.main()
