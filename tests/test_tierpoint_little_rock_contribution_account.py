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
        cls.synthesis_fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
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
        self.assertTrue(SYNTHESIS_FRAGMENT.exists())
        self.assertEqual(self.synthesis_fragment["project_id"], PROJECT)
        self.assertTrue(
            all(row["project_id"] == PROJECT for row in self.synthesis_fragment["estimates"])
        )

    def test_direct_records_preserve_source_definitions(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(self.project["economic_record_count"], 27)
        self.assertEqual(self.project["reported_actual_count"], 27)
        self.assertEqual(self.project["projection_count"], 0)
        self.assertEqual(self.project["modeled_synthesis_count"], 47)
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
            "publishes protected school/city/county component aggregations",
            "8,760 coverage hours",
            "$89,797.97",
            "June 2011 payment remains ambiguous",
        ]:
            self.assertIn(marker, notes)

    def test_modeled_tax_levies_preserve_recipients_and_exclude_2025(self):
        models = self.project["modeled_syntheses"]
        totals = [
            row for row in models
            if row["metric_code"] == "study.modeled_real_property_gross_levy"
        ]
        self.assertEqual([row["period"]["year"] for row in totals],
                         [2011, 2012, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026])
        self.assertEqual([row["value"] for row in totals],
                         [31912.7, 28358.54, 31146.28, 33978.05, 36809.82,
                          39641.59, 42803.64, 46721.02, 50968.68, 96643.03, 89797.97])
        self.assertFalse(any(row["period"].get("year") == 2025 for row in models))
        for total in totals:
            self.assertEqual(total["aggregation"]["role"], "total")
            self.assertEqual(len(total["aggregation"]["component_estimate_ids"]), 3)
            self.assertIn("not an observed bill", total["interval"]["interpretation"])
            self.assertIn("personal property", " ".join(total["limitations"]).lower())

    def test_continuous_coverage_floor_is_not_employee_headcount(self):
        row = next(
            item for item in self.project["modeled_syntheses"]
            if item["estimate_id"] ==
            "est_study_tierpoint_little_rock_minimum_continuous_coverage_fte_2012"
        )
        self.assertAlmostEqual(row["value"], 8760 / 2080)
        self.assertEqual(row["basis"], "modeled_synthesis")
        self.assertEqual(row["presentation"], "modeled_not_observed_or_audited")
        self.assertIn("No relief factor", " ".join(row["derivation"]["assumptions"]))
        self.assertIn("not employee headcount", row["limitations"][0].lower())

    def test_transformer_sensitivities_use_one_2n_side(self):
        rows = {row["metric_code"]: row for row in self.project["modeled_syntheses"]}
        capacity = rows["study.modeled_one_side_service_real_power_capacity"]
        energy = rows["study.modeled_annual_it_electricity_sensitivity"]
        self.assertEqual((capacity["interval"]["low"], capacity["value"], capacity["interval"]["high"]),
                         (2.4, 2.7, 3.0))
        self.assertEqual((energy["interval"]["low"], energy["value"], energy["interval"]["high"]),
                         (2628000, 7391250, 16425000))
        self.assertIn("one 2N transformer side", " ".join(capacity["derivation"]["assumptions"]))
        parameter_names = {item["name"] for item in energy["parameters"]}
        self.assertTrue({"central_power_factor", "central_utilization", "central_case_pue"}
                        <= parameter_names)
        self.assertIn("not metered campus use", energy["scope"]["label"])

    def test_models_never_enter_reported_actuals_or_cash_receipts(self):
        actual_ids = {row["claim_id"] for row in self.project["economic_records"]}
        model_ids = {row["estimate_id"] for row in self.project["modeled_syntheses"]}
        self.assertTrue(actual_ids.isdisjoint(model_ids))
        self.assertTrue(all(row["basis"] == "modeled_synthesis"
                            for row in self.project["modeled_syntheses"]))
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited"
                            for row in self.project["modeled_syntheses"]))
        self.assertFalse(any(row["metric_code"] in {
            "study.property_taxes_paid", "study.property_tax_receipts"
        } for row in self.project["modeled_syntheses"]))

    def test_account_remains_intentionally_incomplete(self):
        completeness = self.project["model_completeness"]
        self.assertEqual(completeness["status"], "incomplete")
        self.assertEqual(completeness["covered_categories"], ["fiscal", "operations", "resources"])
        self.assertEqual(completeness["modeled_categories"], ["fiscal", "operations", "resources"])
        self.assertEqual(
            completeness["missing_categories"],
            ["community", "construction", "investment", "public_costs", "suppliers"],
        )
        self.assertEqual(len(completeness["missing_county_outcomes"]), 3)


if __name__ == "__main__":
    unittest.main()
