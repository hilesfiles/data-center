import json
import math
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00844371952"
EVIDENCE_PATH = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"
MODEL_PATH = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT}.json"


class GoogleBridgeportContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = read(EVIDENCE_PATH)
        cls.model_fragment = read(MODEL_PATH)
        cls.candidates = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.policy = read(MODELING_POLICY)
        validate_evidence(cls.evidence, cls.candidates["candidates"])
        cls.grouped, _ = modeled_products(
            cls.synthesis, cls.candidates["candidates"], cls.evidence, cls.policy
        )
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
            "2026-09-07T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            cls.policy,
        )
        cls.detail = next(row for row in details if row["project_id"] == PROJECT)

    def test_identity_counts_and_actual_projection_split(self):
        self.assertEqual(self.fragment["project_id"], PROJECT)
        self.assertEqual(self.model_fragment["project_id"], PROJECT)
        self.assertEqual(len(self.fragment["records"]), 75)
        self.assertEqual(len(self.detail["economic_records"]), 76)
        self.assertEqual(self.detail["economic_record_count"], 76)
        self.assertEqual(self.detail["reported_actual_count"], 69)
        self.assertEqual(self.detail["projection_count"], 7)
        self.assertEqual(self.detail["modeled_synthesis_count"], 42)
        self.assertEqual(self.detail["county_fips"], "01071")

        projections = [
            row for row in self.detail["economic_records"]
            if row["basis"] == "source_projection"
        ]
        self.assertTrue(all(row["period"]["kind"] == "projection_horizon" for row in projections))
        self.assertEqual(
            {row["value"] for row in projections},
            {100_000, 100, 600_000_000, 1_000, 2_000_000, 550_000, 1_500_000_000},
        )

    def test_three_account_2020_2025_fiscal_series_and_exclusions(self):
        records = {row["claim_id"]: row for row in self.detail["economic_records"]}
        expected_tax = {
            2020: (892.32, 109_983.64, 668.08),
            2021: (5_157.62, 766_668.50, 941_694.26),
            2022: (6_299.02, 558_964.64, 963_215.50),
            2023: (7_407.40, 1_162_992.22, 935_007.58),
            2024: (5_259.20, 1_686_550.24, 928_511.92),
            2025: (3_994.82, 1_905_083.88, 839_956.44),
        }
        for year, values in expected_tax.items():
            observed = tuple(
                records[f"clm_study_google_bridgeport_{slug}_tax_paid_{year}"]["value"]
                for slug in ("google", "design", "wiessner")
            )
            self.assertEqual(observed, values)
            for slug in ("google", "design", "wiessner"):
                self.assertIn(
                    "zero balance",
                    records[f"clm_study_google_bridgeport_{slug}_tax_paid_{year}"]["notes"],
                )

        fragment_text = EVIDENCE_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("unpaid 2026 estimate", fragment_text)
        self.assertIn("adp", fragment_text)
        self.assertIn("schenker", fragment_text)
        self.assertFalse(any(
            row.get("period", {}).get("year") == 2026
            for row in self.fragment["records"]
            if row["metric_code"] in {
                "study.property_taxes_paid",
                "study.account_assessed_value",
                "study.appraised_property_value",
            }
        ))

    def test_tax_aggregation_and_break_even_reproduce_exact_arithmetic(self):
        models = {row["estimate_id"]: row for row in self.grouped[PROJECT]}
        expected = {
            2020: 111_544.04,
            2021: 1_713_520.38,
            2022: 1_528_479.16,
            2023: 2_105_407.20,
            2024: 2_620_321.36,
            2025: 2_749_035.14,
        }
        records = {row["claim_id"]: row for row in self.detail["economic_records"]}
        for year, total in expected.items():
            row = models[f"est_study_google_bridgeport_property_tax_total_{year}"]
            inputs = [
                records[f"clm_study_google_bridgeport_{slug}_tax_paid_{year}"]["value"]
                for slug in ("google", "design", "wiessner")
            ]
            self.assertAlmostEqual(math.fsum(inputs), total, places=2)
            self.assertEqual(row["value"], total)
            self.assertEqual(row["derivation"]["method"], "allocation")
            self.assertEqual(row["interval"]["kind"], "point_estimate")

        threshold = models["est_study_google_bridgeport_service_cost_break_even_2025"]
        self.assertEqual(threshold["value"], expected[2025])
        self.assertIn("not actual public cost", " ".join(threshold["limitations"]).lower())
        self.assertFalse(any("net_fiscal" in row["metric_code"] for row in models.values()))

    def test_source_modeled_channels_and_rounding_are_not_direct_actuals(self):
        models = {row["estimate_id"]: row for row in self.grouped[PROJECT]}
        for key, values in {
            "gdp": (42_000_000, 19_000_000, 16_000_000, 77_000_000),
            "jobs": (255, 270, 165, 690),
            "labor_income": (19_000_000, 20_000_000, 8_000_000, 47_000_000),
        }.items():
            rows = [
                models[f"est_study_google_bridgeport_{key}_{channel}_2021_2023"]
                for channel in ("direct", "indirect", "induced", "total")
            ]
            self.assertEqual(tuple(row["value"] for row in rows), values)
            self.assertEqual(rows[-1]["aggregation"]["role"], "total")
            self.assertEqual(len(rows[-1]["aggregation"]["component_estimate_ids"]), 3)
            self.assertTrue(all(row["derivation"]["method"] == "contribution_analysis" for row in rows))
            self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))
            self.assertAlmostEqual(sum(row["value"] for row in rows[:3]), rows[-1]["value"])

        evidence_ids = {row["claim_id"] for row in self.detail["economic_records"]}
        self.assertFalse(any("gdp_contribution" in claim_id for claim_id in evidence_ids))
        self.assertFalse(any("labor_income" in claim_id for claim_id in evidence_ids))

    def test_water_pue_and_cfe_keep_location_scope_and_rounding(self):
        models = {row["estimate_id"]: row for row in self.grouped[PROJECT]}
        withdrawal = next(
            row for row in self.detail["economic_records"]
            if row["claim_id"] == "clm_study_google_bridgeport_water_withdrawal_2024"
        )
        self.assertEqual(withdrawal["value"], 201_600_000)
        self.assertEqual(withdrawal["value_qualifier"], "approximately")
        self.assertEqual(withdrawal["pdf_page"], 110)

        for year, expected in {2021: 1.13, 2022: 1.12, 2023: 1.10, 2024: 1.10}.items():
            row = models[f"est_study_google_bridgeport_pue_{year}"]
            self.assertEqual(row["value"], expected)
            self.assertEqual(row["scope"]["inventory_allocation"], "unallocated")

        consumption = models["est_study_google_bridgeport_water_consumption_2024"]
        discharge = models["est_study_google_bridgeport_water_discharge_2024"]
        self.assertEqual(consumption["value"], 182_800_000)
        self.assertEqual(discharge["value"], 18_800_000)
        self.assertEqual(consumption["interval"]["low"], 182_750_000)
        self.assertEqual(consumption["interval"]["high"], 182_850_000)
        self.assertEqual(
            {models[f"est_study_google_bridgeport_cfe_{kind}_{year}"]["value"]
             for kind in ("site", "grid") for year in (2022, 2023)},
            {52, 53, 63, 65},
        )

    def test_descriptive_county_comparisons_are_not_causal_effects(self):
        models = {row["estimate_id"]: row for row in self.grouped[PROJECT]}
        expected = {
            "employment": (-0.91, -8.90, 7.09),
            "wage": (2.37, -2.63, 7.37),
            "gdp": (-1.41, -7.37, 4.54),
        }
        for key, (value, low, high) in expected.items():
            row = models[f"est_study_google_bridgeport_county_{key}_comparison_2024"]
            self.assertEqual(row["value"], value)
            self.assertEqual((row["interval"]["low"], row["interval"]["high"]), (low, high))
            self.assertEqual(row["derivation"]["method"], "benchmark_application")
            self.assertNotIn("causal_design", row)
            self.assertIn("descriptive", " ".join(row["limitations"]).lower())
            self.assertIn("fit sensitivity", row["interval"]["interpretation"])

    def test_search_trail_description_and_catalog_proposals(self):
        updates = self.fragment["project_updates"]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual(sum(descriptions[0].count(mark) for mark in ".!?"), 3)

        text = " ".join(row["title"] + " " + row["notes"] for row in updates).lower()
        for token in (
            "assessor", "permit", "incentive", "public-cost", "debt", "utility",
            "generation", "water", "workforce", "supplier", "community recipient",
            "gdp", "employment", "wage", "no real-property", "no project-specific",
            "catalog-and-record proposals", "adversarial",
        ):
            self.assertIn(token, text)
        for proposal in (
            "study.planned_data_center_power_capacity",
            "study.project_site_area",
            "study.contracted_regional_generation_capacity",
            "study.community_organizations_supported",
            "study.community_program_participants",
            "study.volunteer_hours",
            "study.recipient_program_expenditure",
        ):
            self.assertIn(proposal, text)

    def test_native_scope_nonadditivity_and_chronology_conflict(self):
        records = self.detail["economic_records"]
        investments = [
            row for row in records
            if row["metric_code"] in {
                "study.campus_investment_projection",
                "study.campus_capital_expenditure",
                "study.cumulative_facility_investment",
            }
        ]
        self.assertEqual({row["value"] for row in investments}, {
            600_000_000, 980_000_000, 2_000_000_000, 1_500_000_000
        })
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in investments))
        text = EVIDENCE_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("2018 location-page opening milestone conflicts", text)
        self.assertIn("operations began in 2019", text)
        self.assertIn("not added", text)
        self.assertNotIn('"inventory_allocation": "allocated"', text)


if __name__ == "__main__":
    unittest.main()
