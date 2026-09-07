import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00300974499"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class AppleMesaContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read(CONFIG)
        cls.policy = read(MODELING_POLICY)
        cls.evidence_fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.synthesis_fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        validate_evidence(cls.evidence, cls.candidates["candidates"])
        cls.models_by_project, _ = modeled_products(
            cls.synthesis, cls.candidates["candidates"], cls.evidence, cls.policy
        )

    def test_scoped_fragments_and_account_counts(self):
        evidence = self.evidence_fragment
        synthesis = self.synthesis_fragment
        self.assertEqual(evidence["project_id"], PROJECT)
        self.assertEqual(synthesis["project_id"], PROJECT)
        self.assertEqual(len(evidence["sources"]), 13)
        self.assertEqual(len(evidence["records"]), 25)
        self.assertEqual(len(evidence["project_updates"]), 16)
        self.assertEqual(len(synthesis["estimates"]), 3)
        self.assertTrue(all(row["project_id"] == PROJECT for row in evidence["records"]))
        self.assertTrue(all(row["project_id"] == PROJECT for row in evidence["project_updates"]))
        self.assertTrue(all(row["project_id"] == PROJECT for row in synthesis["estimates"]))

        merged_records = [row for row in self.evidence["records"] if row["project_id"] == PROJECT]
        self.assertEqual(len(merged_records), 105)
        self.assertEqual(sum(row["basis"] == "reported_actual" for row in merged_records), 101)
        self.assertEqual(sum(row["basis"] == "source_projection" for row in merged_records), 4)

    def test_exactly_one_project_description_meets_contract(self):
        descriptions = [
            row["project_description"]
            for row in self.evidence_fragment["project_updates"]
            if "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        description = descriptions[0]
        self.assertGreaterEqual(len(description), 80)
        self.assertLessEqual(len(description), 1000)
        self.assertEqual(description.count("."), 2)
        for marker in [
            "3740 South Signal Butte Road",
            "converted and expanded",
            "October 2015",
            "March 2017",
            "real-estate parcel",
            "later data-hall permits",
        ]:
            self.assertIn(marker, description)

    def test_second_pass_adds_all_omitted_completed_positive_permits(self):
        records = {row["claim_id"]: row for row in self.evidence_fragment["records"]}
        floor = records.pop("clm_study_apple_mesa_assessor_floor_area_2026")
        self.assertEqual(floor["value"], 1_255_156)
        self.assertEqual(floor["metric_code"], "study.operating_property_floor_area")
        self.assertEqual(floor["scope"]["inventory_allocation"], "unallocated")

        expected = {
            "clm_study_apple_mesa_permit_bld2016_00031": 1_500_000,
            "clm_study_apple_mesa_permit_bld2016_00032": 5_300_000,
            "clm_study_apple_mesa_permit_bld2016_00182": 1_000_000,
            "clm_study_apple_mesa_permit_bld2016_00394": 38_000_000,
            "clm_study_apple_mesa_permit_bld2016_00395": 59_150_000,
            "clm_study_apple_mesa_permit_bld2016_00922": 420_000,
            "clm_study_apple_mesa_permit_bld2016_01167": 263_670,
            "clm_study_apple_mesa_permit_bld2016_01169": 75_525,
            "clm_study_apple_mesa_permit_bld2016_01475": 315_000,
            "clm_study_apple_mesa_permit_bld2016_01477": 185_000,
            "clm_study_apple_mesa_permit_bld2016_01685": 230_000,
            "clm_study_apple_mesa_permit_bld2016_01686": 430_000,
            "clm_study_apple_mesa_permit_bld2016_01690": 900_000,
            "clm_study_apple_mesa_permit_bld2016_02234": 490_000,
            "clm_study_apple_mesa_permit_bld2016_02279": 410_000,
            "clm_study_apple_mesa_permit_bld2016_03428": 800_000,
            "clm_study_apple_mesa_permit_bld2016_03847": 14_995,
            "clm_study_apple_mesa_permit_pmt18_09704": 50_000,
            "clm_study_apple_mesa_permit_pmt20_12382": 201_262.82,
            "clm_study_apple_mesa_permit_pmt22_15542": 196_120,
            "clm_study_apple_mesa_permit_pmt24_07843": 10_013.64,
            "clm_study_apple_mesa_permit_pmt24_12190": 900_000,
            "clm_study_apple_mesa_permit_pmt24_13677": 1_560_000,
            "clm_study_apple_mesa_permit_pmt25_01154": 1_000_000,
        }
        self.assertEqual({key: row["value"] for key, row in records.items()}, expected)
        self.assertTrue(
            all(row["metric_code"] == "study.permitted_construction_value" for row in records.values())
        )
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in records.values()))
        self.assertTrue(
            all(
                any(marker in row["notes"].lower() for marker in ("not", "neither", "rather than"))
                for row in records.values()
            )
        )

    def test_three_corrected_models_use_only_business_personal_property(self):
        rows = {row["estimate_id"]: row for row in self.synthesis_fragment["estimates"]}
        self.assertEqual(
            {key: row["value"] for key, row in rows.items()},
            {
                "est_study_apple_mesa_bpp_ftz_property_tax_reduction_2023": 3_250_864.51,
                "est_study_apple_mesa_bpp_ftz_property_tax_reduction_2024": 2_421_356.69,
                "est_study_apple_mesa_bpp_ftz_property_tax_reduction_2025": 2_127_179.6,
            },
        )
        for row in rows.values():
            self.assertEqual(row["derivation"]["method"], "statutory_counterfactual")
            self.assertEqual(row["scope"]["level"], "company_county")
            self.assertTrue(
                all("bpp" in claim_id for claim_id in row["derivation"]["input_claim_ids"])
            )
            self.assertFalse(
                any("real_property" in claim_id for claim_id in row["derivation"]["input_claim_ids"])
            )
            self.assertIn("not a cash grant", " ".join(row["limitations"]).lower())

    def test_all_27_legacy_models_have_explicit_decisions(self):
        audit = next(
            row
            for row in self.evidence_fragment["project_updates"]
            if row["title"] == "All 27 legacy models individually adjudicated under policy 1.3.0"
        )
        notes = audit["notes"]
        legacy_ids = {
            "est_study_apple_mesa_onsite_water_2025",
            "est_study_apple_mesa_ftz_employment_2024",
            "est_study_apple_mesa_ftz_payroll_2024",
            "est_study_apple_mesa_ioc_credit_realized",
            "est_study_apple_mesa_ftz_property_tax_reduction_2023",
            "est_study_apple_mesa_ftz_property_tax_reduction_2024",
            "est_study_apple_mesa_ftz_property_tax_reduction_2025",
            "est_study_apple_mesa_ftz_export_duty_avoidance_2024",
            "est_study_apple_mesa_allocated_employment_2024",
            "est_study_apple_mesa_allocated_payroll_2024",
            "est_study_apple_mesa_electricity_cost_2025",
            "est_study_apple_mesa_location_emissions_2025",
            "est_study_apple_mesa_cooling_water_savings_potential_2025",
            "est_study_full_apple_mesa_annualized_capital",
            "est_study_full_apple_mesa_local_construction_spend",
            "est_study_full_apple_mesa_construction_job_years_total",
            "est_study_full_apple_mesa_construction_labor_income_total",
            "est_study_full_apple_mesa_operating_fte_total",
            "est_study_full_apple_mesa_operating_labor_income_total",
            "est_study_full_apple_mesa_operating_supplier_output",
            "est_study_full_apple_mesa_household_output",
            "est_study_full_apple_mesa_latest_local_tax_contribution",
            "est_study_full_apple_mesa_annual_local_service_cost_break_even",
            "est_study_full_apple_mesa_wastewater",
            "est_study_full_apple_mesa_employment_comparison_gap",
            "est_study_full_apple_mesa_gdp_comparison_gap",
            "est_study_full_apple_mesa_wage_comparison_gap",
        }
        self.assertEqual(len(legacy_ids), 27)
        self.assertTrue(all(estimate_id in notes for estimate_id in legacy_ids))
        self.assertIn("Exact tally: 0 retain, 3 revise, 24 remove.", notes)
        self.assertIn("explicit orchestration removal directives", notes)

    def test_search_matrix_preserves_material_queries_and_negative_findings(self):
        notes = "\n".join(row["notes"] for row in self.evidence_fragment["project_updates"])
        for marker in [
            "212 records",
            "PMT18-04958",
            "$343,013.61",
            "304-33-005S",
            "993-72-704",
            "Resolution 12520",
            "plant 64404",
            "Greenfield Water Reclamation Plant",
            "Platypus Development LLC",
            "worker residence",
            "recipient-side",
            "parallel trend",
        ]:
            self.assertIn(marker, notes)


if __name__ == "__main__":
    unittest.main()
