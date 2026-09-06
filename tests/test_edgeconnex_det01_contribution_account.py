import unittest

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT = "prj_study_im3_building_00377585075"


class EdgeConnexDet01ContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.policy = read(MODELING_POLICY)

    def test_project_fragments_pass_semantic_contracts(self):
        validate_evidence(self.evidence, self.candidates["candidates"])
        grouped, _ = modeled_products(
            self.synthesis, self.candidates["candidates"], self.evidence, self.policy
        )
        rows = grouped[PROJECT]
        self.assertEqual(len(rows), 23)
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))
        self.assertFalse(any(row["derivation"]["method"] in {"difference_in_differences", "event_study", "synthetic_control"} for row in rows))

    def test_project_gate_and_fiscal_scope(self):
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            self.candidates,
            inventory,
            panels,
            "2026-09-05T00:00:00+00:00",
            self.evidence,
            self.synthesis,
            self.policy,
        )
        detail = next(row for row in details if row["project_id"] == PROJECT)
        self.assertEqual(detail["economic_record_count"], 50)
        self.assertEqual(detail["reported_actual_count"], 46)
        self.assertEqual(detail["projection_count"], 4)
        self.assertEqual(detail["modeled_synthesis_count"], 23)
        self.assertEqual(detail["model_completeness"]["status"], "full_modeled_account")
        rows = {row["estimate_id"]: row for row in detail["modeled_syntheses"]}
        tax = rows["est_study_edgeconnex_det01_latest_local_tax_contribution"]
        break_even = rows["est_study_edgeconnex_det01_annual_service_cost_break_even"]
        self.assertEqual(tax["value"], 255195.22)
        self.assertEqual(break_even["value"], tax["value"])
        self.assertIn("No positive or negative net fiscal result", break_even["notes"])


if __name__ == "__main__":
    unittest.main()
