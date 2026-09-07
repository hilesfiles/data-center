import json
import re
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence
from scripts.study_modeled_synthesis import load_synthesis


PROJECT_ID = "prj_study_im3_building_00978934687"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class DigitalCrossroadHammondContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        cls.panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }

    def test_fragment_adds_direct_accounts_and_one_description(self):
        fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        descriptions = [
            update["project_description"]
            for update in fragment["project_updates"]
            if update.get("project_description")
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertGreaterEqual(len(re.findall(r"[.!?](?:\s|$)", descriptions[0])), 2)
        self.assertLessEqual(len(re.findall(r"[.!?](?:\s|$)", descriptions[0])), 4)
        self.assertEqual((len(fragment["sources"]), len(fragment["records"])), (8, 17))
        self.assertTrue(all(row["basis"] == "reported_actual" for row in fragment["records"]))
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in fragment["records"])
        )

        claims = {row["claim_id"]: row for row in fragment["records"]}
        self.assertEqual(claims["clm_study_dx_hammond_jv_personal_assessed_value_2025"]["value"], 29673490)
        self.assertEqual(claims["clm_study_dx_hammond_jv_personal_taxes_paid_2024"]["value"], 1020970.76)
        self.assertEqual(claims["clm_study_dx_hammond_jv_personal_taxes_paid_partial_2025"]["value"], 475072.57)
        self.assertEqual(claims["clm_study_digital_crossroad_real_taxes_paid_partial_2025"]["value"], 320433.74)
        self.assertEqual(claims["clm_study_digital_crossroad_permitted_generators_2025"]["value"], 12)
        self.assertEqual(claims["clm_study_dx_permitted_water_withdrawal_capacity_2025"]["value"], 910.08)
        self.assertIn("no zero is inferred", claims["clm_study_dx_permitted_water_withdrawal_capacity_2025"]["notes"].lower())
        personal_gross = sum(
            row["value"]
            for row in fragment["records"]
            if row["metric_code"] == "study.gross_property_tax_distribution"
        )
        self.assertAlmostEqual(personal_gross, 1113616.40, places=2)
        self.assertAlmostEqual(personal_gross - 141017.68 - 22453.58, 950145.14, places=2)

        _, details, _ = build_products(
            self.config,
            self.inventory,
            self.panels,
            "2026-09-06T00:00:00+00:00",
        )
        project = next(row for row in details if row["project_id"] == PROJECT_ID)
        self.assertEqual(
            (project["economic_record_count"], project["reported_actual_count"], project["projection_count"]),
            (130, 120, 10),
        )

    def test_all_legacy_models_have_explicit_dispositions(self):
        base = json.loads((ROOT / "config/v1/study-modeled-synthesis.json").read_text(encoding="utf-8"))
        legacy_ids = {
            row["estimate_id"] for row in base["estimates"] if row["project_id"] == PROJECT_ID
        }
        self.assertEqual(len(legacy_ids), 43)

        fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        audit = " ".join(update["notes"] for update in fragment["project_updates"])
        decisions = re.findall(
            r"MODEL DECISION — (REMOVE|REVISE) — (est_study_[a-z0-9_]+):",
            audit,
        )
        self.assertEqual(len(decisions), 43)
        self.assertEqual({estimate_id for _, estimate_id in decisions}, legacy_ids)
        self.assertEqual(sum(decision == "REVISE" for decision, _ in decisions), 2)
        self.assertEqual(sum(decision == "REMOVE" for decision, _ in decisions), 41)

    def test_corrective_synthesis_has_only_two_nonadditive_tax_models(self):
        fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
        self.assertEqual(len(fragment["estimates"]), 2)
        self.assertEqual({row["value"] for row in fragment["estimates"]}, {1662655.90})
        self.assertEqual(
            {row["metric_code"] for row in fragment["estimates"]},
            {
                "study.modeled_latest_project_linked_local_tax_contribution",
                "study.modeled_annual_local_service_cost_break_even",
            },
        )
        for row in fragment["estimates"]:
            self.assertEqual(row["scope"]["inventory_allocation"], "unallocated")
            self.assertEqual(row["aggregation"]["overlap_policy"], "do_not_sum_outside_declared_total")
            self.assertIn("Supersedes est_study_", row["notes"])
        threshold = next(row for row in fragment["estimates"] if row["category"] == "public_costs")
        self.assertTrue(any("not an estimate of actual public-service cost" in item for item in threshold["limitations"]))
        self.assertTrue(any("No positive or negative fiscal margin" in item for item in threshold["derivation"]["assumptions"]))

        evidence = load_evidence()
        synthesis = load_synthesis()
        claim_ids = {row["claim_id"] for row in evidence["records"]}
        source_ids = {row["source_id"] for row in evidence["sources"]}
        for row in synthesis["estimates"]:
            if row["project_id"] != PROJECT_ID or not row["estimate_id"].endswith("_reaudit_2026"):
                continue
            self.assertTrue(set(row["derivation"]["input_claim_ids"]) <= claim_ids)
            self.assertTrue(set(row["derivation"]["input_source_ids"]) <= source_ids)


if __name__ == "__main__":
    unittest.main()
