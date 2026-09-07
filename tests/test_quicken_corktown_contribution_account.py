import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00903236619"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class QuickenCorktownContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read(CONFIG)
        cls.policy = read(MODELING_POLICY)
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.model_fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        validate_evidence(cls.evidence, cls.candidates["candidates"])
        cls.models_by_project, _ = modeled_products(
            cls.synthesis, cls.candidates["candidates"], cls.evidence, cls.policy
        )

    def test_scoped_counts_and_basis_split(self):
        self.assertEqual(self.fragment["project_id"], PROJECT)
        self.assertEqual(self.model_fragment["project_id"], PROJECT)
        self.assertEqual(len(self.fragment["sources"]), 14)
        self.assertEqual(len(self.fragment["records"]), 4)
        self.assertEqual(len(self.fragment["project_updates"]), 11)
        self.assertEqual(len(self.model_fragment["estimates"]), 2)
        self.assertTrue(all(row["project_id"] == PROJECT for row in self.fragment["records"]))
        self.assertTrue(all(row["project_id"] == PROJECT for row in self.fragment["project_updates"]))

        merged = [row for row in self.evidence["records"] if row["project_id"] == PROJECT]
        self.assertEqual(len(merged), 8)
        self.assertEqual(sum(row["basis"] == "reported_actual" for row in merged), 7)
        self.assertEqual(sum(row["basis"] == "source_projection" for row in merged), 1)
        models = {row["metric_code"]: row for row in self.models_by_project[PROJECT]}
        self.assertEqual(
            set(models),
            {
                "study.modeled_facility_electricity_consumption",
                "study.modeled_construction_labor_income_direct",
            },
        )
        self.assertEqual(
            models["study.modeled_facility_electricity_consumption"]["interval"],
            {
                "kind": "sensitivity_envelope",
                "low": 3066000,
                "central": 6132000,
                "high": 12264000,
                "interpretation": "The reported 1.4 MW available-power nameplate is annualized at 25%, 50% and 100% utilization. The high endpoint is the mathematical continuous-load ceiling for that nameplate, not a forecast, true-value bound or confidence interval.",
            },
        )
        labor_interval = models["study.modeled_construction_labor_income_direct"]["interval"]
        self.assertEqual(
            (labor_interval["low"], labor_interval["central"], labor_interval["high"]),
            (682344, 1364688, 2729376),
        )

    def test_one_project_description_and_boundary_contract(self):
        descriptions = [
            row["project_description"]
            for row in self.fragment["project_updates"]
            if "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        description = descriptions[0]
        self.assertGreaterEqual(len(description), 80)
        self.assertLessEqual(len(description), 1000)
        for marker in [
            "1401 Rosa Parks Boulevard",
            "Detroit's Corktown",
            "May 2014",
            "June 30, 2015",
            "35,920 rentable square feet",
            "partial tenancy",
        ]:
            self.assertIn(marker, description)

    def test_new_records_preserve_qualifiers_and_nonallocation(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(
            {key: row["value"] for key, row in records.items()},
            {
                "clm_study_quicken_technology_center_floor_area_2015": 66000,
                "clm_study_quicken_technology_center_power_capacity_2015": 1.4,
                "clm_study_quicken_technology_center_electricians_2015": 70,
                "clm_study_quicken_dte_rerouting_projection_2014": 24044.58,
            },
        )
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in records.values())
        )
        self.assertEqual(
            records["clm_study_quicken_dte_rerouting_projection_2014"]["basis"],
            "source_projection",
        )
        self.assertEqual(
            records["clm_study_quicken_technology_center_electricians_2015"]["value_qualifier"],
            "approximately",
        )

    def test_evidence_matrix_and_model_boundaries_are_auditable(self):
        notes = "\n".join(row["notes"] for row in self.fragment["project_updates"])
        for marker in [
            "08990518.03",
            "08008283-303",
            "PA 198",
            "15 Quicken-family projects",
            "2014 council resolution",
            "BLD2019-03107",
            "ELE2019-03832",
            "ENG-21-19",
            "00036222",
            "worker residence",
            "$4.8 million",
            "recipient-confirmed",
            "County effects: reject",
        ]:
            self.assertIn(marker, notes)

        models = {row["metric_code"]: row for row in self.model_fragment["estimates"]}
        payroll = models["study.modeled_construction_labor_income_direct"]
        self.assertEqual(
            (payroll["interval"]["low"], payroll["value"], payroll["interval"]["high"]),
            (682344, 1364688, 2729376),
        )
        self.assertTrue(all(row["confidence"] == "low" for row in models.values()))
        self.assertFalse(
            any(
                row["metric_code"]
                in {
                    "study.modeled_operating_payroll",
                    "study.modeled_annual_local_service_cost_break_even",
                    "study.modeled_county_gdp_comparison_gap",
                }
                for row in models.values()
            )
        )


if __name__ == "__main__":
    unittest.main()
