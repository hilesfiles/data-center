import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00359930465"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class EquinixSe3ContributionAccountTest(unittest.TestCase):
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
        self.assertEqual(len(self.fragment["sources"]), 27)
        self.assertEqual(len(self.fragment["records"]), 21)
        self.assertEqual(len(self.fragment["project_updates"]), 12)
        self.assertEqual(len(self.model_fragment["estimates"]), 8)
        self.assertTrue(all(row["project_id"] == PROJECT for row in self.fragment["records"]))
        self.assertTrue(
            all(row["project_id"] == PROJECT for row in self.fragment["project_updates"])
        )

        merged = [row for row in self.evidence["records"] if row["project_id"] == PROJECT]
        self.assertEqual(len(merged), 22)
        self.assertEqual(sum(row["basis"] == "reported_actual" for row in merged), 20)
        self.assertEqual(sum(row["basis"] == "source_projection" for row in merged), 2)
        models = {row["metric_code"]: row for row in self.models_by_project[PROJECT]}
        self.assertEqual(
            set(models),
            {
                "study.modeled_facility_electricity_consumption",
                "study.modeled_annual_local_service_cost_break_even",
                "study.modeled_construction_labor_income_direct",
                "study.modeled_construction_value_award_category",
                "study.modeled_minimum_continuous_coverage_fte_equivalent",
                "study.modeled_minimum_continuous_security_wage_cost",
                "study.modeled_electricity_cost_benchmark",
                "study.modeled_location_based_electricity_emissions",
            },
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
            "2020 Fifth Avenue",
            "King County",
            "March 14, 2013",
            "four-level leasehold",
            "36,457-square-foot",
            "parcel 0659000905",
            "SE2",
            "9 MW",
        ]:
            self.assertIn(marker, description)

    def test_direct_records_preserve_scope_and_payment_timing(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        investment = records["clm_study_digital_realty_2020_fifth_jv_cash_2011"]
        self.assertEqual(investment["value"], 4100000)
        self.assertEqual(investment["value_qualifier"], "approximately")
        self.assertIn("50%", investment["scope"]["label"])
        self.assertEqual(
            records["clm_study_equinix_se3_permit_value_6229374"]["value"], 8846783
        )
        self.assertEqual(
            records["clm_study_equinix_se3_permit_value_6262351"]["value"], 2474000
        )
        self.assertEqual(
            records["clm_study_equinix_se3_property_taxes_billed_2026"]["value"],
            391063.45,
        )
        paid = records["clm_study_equinix_se3_property_taxes_paid_2026"]
        self.assertEqual(paid["value"], 195531.73)
        self.assertEqual(paid["period"]["kind"], "reported_snapshot")
        self.assertIn("Partial", paid["notes"])

        assessed = [
            row
            for row in self.fragment["records"]
            if row["metric_code"] == "study.account_assessed_value"
        ]
        self.assertEqual(len(assessed), 14)
        self.assertEqual(
            [row["period"]["year"] for row in assessed], list(range(2013, 2027))
        )
        self.assertTrue(
            all("Landlord real-property parcel" in row["scope"]["label"] for row in assessed)
        )
        power = records["clm_study_equinix_se3_power_allocation_2011"]
        self.assertEqual(power["basis"], "source_projection")
        self.assertEqual(power["value_qualifier"], "up_to")

    def test_evidence_matrix_and_model_boundaries_are_auditable(self):
        notes = "\n".join(row["notes"] for row in self.fragment["project_updates"])
        for marker in [
            "407 records",
            "6229374-CN",
            "6262351-CN",
            "3010224-LU",
            "6336933-SS",
            "acct_nbr='065900090500'",
            "x48t-7chj",
            "50,482 total project worker hours",
            "$96.707 million",
            "$40,749.49 Waterfront LID assessment",
            "recipient-confirmed",
            "County employment: reject",
            "county GDP: reject",
            "data.seattle.gov/resource/76t5-zqzr.json",
            "6294137-CN",
            "Printed pages 16-17",
            "$27.38 Seattle-Bellevue-Everett",
            "$50 million-$100 million private-building award category",
            "Supplier/non-labor residual: reject",
            "$17.18 near-opening",
            "635.267 lb CO2e/MWh",
        ]:
            self.assertIn(marker, notes)

        models = {row["metric_code"]: row for row in self.models_by_project[PROJECT]}
        energy = models["study.modeled_facility_electricity_consumption"]
        self.assertEqual(
            (energy["interval"]["low"], energy["value"], energy["interval"]["high"]),
            (19710000, 39420000, 78840000),
        )
        self.assertEqual(energy["confidence"], "low")
        threshold = models["study.modeled_annual_local_service_cost_break_even"]
        self.assertEqual(
            (threshold["interval"]["low"], threshold["value"], threshold["interval"]["high"]),
            (391063.45, 391063.45, 391063.45),
        )
        self.assertTrue(
            any("not an estimate of actual public cost" in row for row in threshold["limitations"])
        )
        labor = models["study.modeled_construction_labor_income_direct"]
        self.assertEqual(
            (labor["interval"]["low"], labor["value"], labor["interval"]["high"]),
            (1036647.87, 1382197.16, 1727746.45),
        )
        self.assertEqual(labor["parameters"][0]["value"], 50482)
        self.assertEqual(labor["parameters"][1]["value"], 27.38)
        self.assertEqual(labor["confidence"], "low")
        self.assertTrue(any("Not certified payroll" in row for row in labor["limitations"]))

        construction = models["study.modeled_construction_value_award_category"]
        self.assertEqual(
            (
                construction["interval"]["low"],
                construction["value"],
                construction["interval"]["high"],
            ),
            (50000000, 75000000, 100000000),
        )
        self.assertTrue(any("Not an exact or audited" in row for row in construction["limitations"]))

        coverage = models["study.modeled_minimum_continuous_coverage_fte_equivalent"]
        self.assertEqual(
            (
                coverage["interval"]["low"],
                coverage["value"],
                coverage["interval"]["high"],
            ),
            (4.2115384615, 4.8432692308, 5.475),
        )
        self.assertTrue(any("Not observed headcount" in row for row in coverage["limitations"]))

        wage_cost = models["study.modeled_minimum_continuous_security_wage_cost"]
        self.assertEqual(
            (
                wage_cost["interval"]["low"],
                wage_cost["value"],
                wage_cost["interval"]["high"],
            ),
            (150496.8, 229586.46, 259532.52),
        )
        self.assertEqual(wage_cost["parameters"][1]["value"], 17.18)
        self.assertEqual(wage_cost["parameters"][2]["value"], 22.79)

        electricity_cost = models["study.modeled_electricity_cost_benchmark"]
        self.assertEqual(
            (
                electricity_cost["interval"]["low"],
                electricity_cost["value"],
                electricity_cost["interval"]["high"],
            ),
            (1200339, 2605662, 10777428),
        )
        self.assertTrue(any("Not an observed bill" in row for row in electricity_cost["limitations"]))

        emissions = models["study.modeled_location_based_electricity_emissions"]
        self.assertAlmostEqual(emissions["interval"]["low"], 5679.4811256599)
        self.assertAlmostEqual(emissions["value"], 11358.9622513199)
        self.assertAlmostEqual(emissions["interval"]["high"], 22717.9245026397)
        self.assertEqual(emissions["parameters"][3]["value"], 635.267)
        self.assertTrue(any("Not measured site emissions" in row for row in emissions["limitations"]))


if __name__ == "__main__":
    unittest.main()
