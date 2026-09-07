import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis
from scripts.validate_data_contract import ContractValidator


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00598261190"
FRAGMENT = (
    ROOT
    / "config/v1/study-economic-evidence.projects"
    / f"{PROJECT_ID}.json"
)
MODEL_FRAGMENT = (
    ROOT
    / "config/v1/study-modeled-synthesis.projects"
    / f"{PROJECT_ID}.json"
)


class StateFarmOlatheContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
        cls.fragment = read_json(FRAGMENT)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        config = read_json(ROOT / "config/v1/private-sector-study-candidates.json")
        inventory = {
            row["entity_id"]: row
            for row in read_json(ROOT / "site/public/data/v1/facilities/index.json")
        }
        panels = {}
        for path in sorted(
            (ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")
        ):
            for row in read_json(path):
                panels[row["county_fips"]] = row
        policy = read_json(ROOT / "config/v1/study-modeling-policy.json")
        _, details, _ = build_products(
            config,
            inventory,
            panels,
            "2026-09-06T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_fragment_and_merged_evidence_pass_contract_validation(self):
        self.assertEqual(self.fragment["project_id"], PROJECT_ID)
        self.assertEqual(len(self.fragment["records"]), 7)
        self.assertTrue(
            all(row["project_id"] == PROJECT_ID for row in self.fragment["records"])
        )
        issues = ContractValidator(ROOT / "schemas/v1").validate_record(
            self.evidence,
            ROOT / "schemas/v1/study-economic-evidence.schema.json",
        )
        self.assertEqual(issues, [])

    def test_audit_adds_actual_anchors_and_bounded_models_without_manufacturing_completion(self):
        project = self.project
        self.assertEqual(
            (
                project["economic_record_count"],
                project["reported_actual_count"],
                project["projection_count"],
                project["modeled_synthesis_count"],
            ),
            (32, 32, 0, 4),
        )
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(
            project["model_completeness"]["missing_categories"],
            ["community", "suppliers"],
        )
        self.assertEqual(
            project["model_completeness"]["missing_county_outcomes"],
            [],
        )
        self.assertTrue(MODEL_FRAGMENT.exists())

    def test_permit_operations_and_resource_facts_preserve_scope(self):
        rows = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(
            rows["clm_study_state_farm_olathe_permitted_construction_value_2015"]["value"],
            81_555_000,
        )
        self.assertEqual(
            rows["clm_study_state_farm_olathe_permitted_tenant_finish_value_2017"]["value"],
            28_000_000,
        )
        self.assertEqual(
            rows["clm_study_state_farm_olathe_operating_floor_area_2017"]["value"],
            193_953,
        )
        self.assertEqual(
            rows["clm_study_state_farm_olathe_occupied_share_2017"]["value"],
            100,
        )
        self.assertEqual(
            rows["clm_study_state_farm_olathe_critical_it_load_2017"]["value"],
            6.66,
        )
        self.assertEqual(
            rows["clm_study_state_farm_olathe_critical_it_load_2025"]["value"],
            7.5,
        )
        added = [row for row in rows.values() if row["reviewed_on"] == "2026-09-06"]
        self.assertTrue(all(row["basis"] == "reported_actual" for row in added))
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in added)
        )
        permit_notes = " ".join(
            row["notes"] for row in added if row["metric_code"] == "study.permitted_construction_value"
        ).lower()
        self.assertIn("not summed", permit_notes)
        self.assertIn("not audited expenditure", permit_notes)

        hpip = rows["clm_study_state_farm_olathe_hpip_capital_investment_2020"]
        self.assertEqual(hpip["value"], 282_100_000)
        self.assertEqual(hpip["source_id"], "src_study_kansas_commerce_hpip_state_farm_2026")
        self.assertIn("not summed", hpip["notes"])

    def test_last_resort_models_are_bounded_and_noncausal(self):
        modeled = {row["metric_code"]: row for row in self.project["modeled_syntheses"]}
        self.assertEqual(
            set(modeled),
            {
                "study.modeled_annual_local_service_cost_break_even",
                "study.modeled_county_employment_comparison_gap",
                "study.modeled_county_gdp_comparison_gap",
                "study.modeled_county_wage_comparison_gap",
            },
        )
        threshold = modeled["study.modeled_annual_local_service_cost_break_even"]
        self.assertEqual(threshold["value"], 2_298_781.14)
        self.assertEqual(threshold["interval"]["kind"], "point_estimate")
        self.assertIn("not an estimate of actual public-service cost", threshold["interval"]["interpretation"])

        comparisons = [row for metric, row in modeled.items() if "comparison_gap" in metric]
        self.assertEqual(
            {row["metric_code"]: row["value"] for row in comparisons},
            {
                "study.modeled_county_gdp_comparison_gap": 5.6,
                "study.modeled_county_employment_comparison_gap": 0.72,
                "study.modeled_county_wage_comparison_gap": 2.23,
            },
        )
        self.assertTrue(all(row["confidence"] == "low" for row in comparisons))
        self.assertTrue(all(row["derivation"]["method"] == "benchmark_application" for row in comparisons))
        self.assertTrue(all(row["interval"]["kind"] == "sensitivity_envelope" for row in comparisons))
        self.assertTrue(all("causal_design" not in row for row in comparisons))
        self.assertTrue(all(row["aggregation"]["role"] == "standalone" for row in modeled.values()))

    def test_description_and_persistent_search_ledger_are_published(self):
        updates = [
            update
            for update in self.evidence["project_updates"]
            if update["project_id"] == PROJECT_ID
        ]
        descriptions = [
            update["project_description"]
            for update in updates
            if "project_description" in update
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1_000)
        self.assertEqual(descriptions[0].count("."), 3)
        self.assertGreaterEqual(len(updates), 12)

        ledger = " ".join(
            f"{update['title']} {update['notes']}" for update in updates
        ).lower()
        for term in (
            "boundary",
            "construction",
            "supplier",
            "fiscal",
            "public-cost",
            "incentive",
            "utility",
            "water",
            "workforce",
            "community",
            "planning",
            "county outcomes",
        ):
            self.assertIn(term, ledger)
        self.assertIn("no executed agreement", ledger)
        self.assertIn("no realized", ledger)
        self.assertIn("no primary site record identifies the serving utility", ledger)
        self.assertIn("model-candidate decision table", ledger)
        self.assertIn("input-output model is rejected", ledger)
        self.assertIn("supplier and community gaps remain open", ledger)
        self.assertIn("no causal attribution", ledger)
        self.assertIn("no cash grant", ledger)


if __name__ == "__main__":
    unittest.main()
