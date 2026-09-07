import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis
from scripts.validate_data_contract import ContractValidator


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00500820007"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class MetaFortWorthContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = json.loads(
            (ROOT / "config/v1/private-sector-study-candidates.json").read_text(encoding="utf-8")
        )
        inventory = {
            row["entity_id"]: row
            for row in json.loads(
                (ROOT / "site/public/data/v1/facilities/index.json").read_text(encoding="utf-8")
            )
        }
        panels = {}
        for path in sorted(
            (ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")
        ):
            for row in json.loads(path.read_text(encoding="utf-8")):
                panels[row["county_fips"]] = row
        policy = json.loads(
            (ROOT / "config/v1/study-modeling-policy.json").read_text(encoding="utf-8")
        )
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
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.evidence = load_evidence()

    def test_fragment_and_merged_evidence_pass_contract_validation(self):
        self.assertEqual(len(self.fragment["sources"]), 23)
        self.assertEqual(len(self.fragment["records"]), 22)
        issues = ContractValidator(ROOT / "schemas/v1").validate_record(
            self.evidence,
            ROOT / "schemas/v1/study-economic-evidence.schema.json",
        )
        self.assertEqual(issues, [])

    def test_provisional_account_counts_and_gate(self):
        project = self.project
        self.assertEqual(
            (
                project["economic_record_count"],
                project["reported_actual_count"],
                project["projection_count"],
            ),
            (23, 18, 5),
        )
        self.assertEqual(project["modeled_synthesis_count"], 0)
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], [])
        self.assertEqual(
            project["model_completeness"]["missing_county_outcomes"],
            [
                "study.modeled_county_employment_comparison_gap",
                "study.modeled_county_gdp_comparison_gap",
                "study.modeled_county_wage_comparison_gap",
            ],
        )
        self.assertFalse(MODEL_FRAGMENT.exists())

    def test_direct_records_preserve_boundary_time_and_nonadditivity(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(records["clm_study_meta_fort_worth_audited_construction_2017"]["value"], 784_208_681)
        self.assertEqual(records["clm_study_meta_fort_worth_local_construction_spend_2017"]["value"], 74_215_330)
        self.assertEqual(records["clm_study_meta_fort_worth_assessed_value_2024"]["value"], 2_289_681_525)
        self.assertEqual(records["clm_study_meta_fort_worth_electricity_2024"]["value"], 1_109_004_000)
        self.assertEqual(records["clm_study_meta_fort_worth_water_main_payment_2018"]["value"], 879_851.31)
        self.assertTrue(all(row["scope"]["county_fips"] == "48439" for row in self.fragment["records"]))
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.fragment["records"])
        )
        self.assertIn(
            "must not be summed",
            records["clm_study_meta_fort_worth_investment_2026"]["notes"],
        )

    def test_source_projections_remain_distinct_from_actuals(self):
        projections = [row for row in self.project["economic_records"] if row["basis"] == "source_projection"]
        self.assertEqual(len(projections), 5)
        self.assertTrue(all(row["period"]["kind"] == "projection_horizon" for row in projections))
        self.assertEqual(
            {row["metric_code"] for row in projections},
            {"study.operational_jobs_supported", "study.permitted_construction_value"},
        )
        self.assertEqual(
            sorted(row["value"] for row in projections if row["metric_code"] == "study.permitted_construction_value"),
            [6_000_000, 109_000_000, 300_000_000, 531_000_000],
        )

    def test_all_categories_have_direct_or_source_projected_evidence(self):
        categories = {row["category"] for row in self.project["economic_records"]}
        self.assertEqual(
            categories,
            {
                "investment",
                "construction",
                "suppliers",
                "operations",
                "fiscal",
                "public_costs",
                "resources",
                "community",
            },
        )

    def test_one_description_search_ledger_and_provisional_status(self):
        updates = self.fragment["project_updates"]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertIn("634,395-square-foot", descriptions[0])
        self.assertIn("14100 Park Vista", descriptions[0])
        self.assertEqual(len(updates), 23)
        self.assertIn("candidate_pending_adversarial_review", updates[-1]["notes"])
        search_log = " ".join(row["notes"].lower() for row in updates)
        for term in (
            "assessor",
            "permit",
            "utility",
            "water",
            "supplier",
            "court",
            "bond",
            "community",
            "gdp",
            "qcew",
            "catalog",
            "rejected",
        ):
            self.assertIn(term, search_log)


if __name__ == "__main__":
    unittest.main()
