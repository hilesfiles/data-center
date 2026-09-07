import json
import unittest
from collections import Counter
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


PROJECT_ID = "prj_study_im3_building_00397914434"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class ApplePrinevilleContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.model_fragment = json.loads(MODEL_FRAGMENT.read_text(encoding="utf-8"))
        cls.config = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        _, details, _ = build_products(
            cls.config,
            inventory,
            panels,
            "2026-09-07T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            read(MODELING_POLICY),
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_fragments_are_project_scoped_and_boundary_safe(self):
        self.assertEqual(self.fragment["project_id"], PROJECT_ID)
        self.assertEqual(self.model_fragment["project_id"], PROJECT_ID)
        for key in ("records", "project_updates"):
            self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment[key]))
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.model_fragment["estimates"]))
        for marker in ("9,228", "1600 SW Baldwin", "15 current Apple", "DC No. 1", "unallocated"):
            self.assertIn(marker, self.fragment["scope_note"])
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.fragment["records"]))

    def test_direct_records_validate_and_extend_the_baseline(self):
        validate_evidence(self.evidence, self.config["candidates"])
        self.assertEqual(len(self.fragment["sources"]), 28)
        self.assertEqual(len(self.fragment["records"]), 44)
        self.assertEqual(Counter(row["basis"] for row in self.fragment["records"]), {"reported_actual": 40, "source_projection": 4})
        self.assertEqual(self.project["economic_record_count"], 45)
        self.assertEqual((self.project["reported_actual_count"], self.project["projection_count"]), (41, 4))
        self.assertEqual(self.project["modeled_synthesis_count"], 5)
        self.assertEqual(self.project["model_completeness"]["missing_categories"], ["community", "construction", "suppliers"])

    def test_electricity_and_abatement_series_preserve_source_years(self):
        records = self.fragment["records"]
        electricity = sorted(
            (row for row in records if row.get("annual_series_key") == "apple_prineville_annual_electricity"),
            key=lambda row: row["period"]["year"],
        )
        abatements = [row for row in records if row["metric_code"] == "study.local_property_tax_credits"]
        normalized_abatements = sorted(
            (row for row in abatements if row.get("annual_series_key") == "apple_prineville_lrz_potential_additional_tax"),
            key=lambda row: row["period"]["year"],
        )
        self.assertEqual([row["period"]["year"] for row in electricity], list(range(2012, 2026)))
        self.assertEqual(
            [row["value"] for row in electricity],
            [2_000_000, 18_000_000, 27_000_000, 54_000_000, 115_000_000, 195_000_000,
             252_000_000, 254_000_000, 279_000_000, 279_000_000, 275_000_000, 269_000_000,
             255_000_000, 267_000_000],
        )
        self.assertEqual(len(abatements), 10)
        self.assertEqual(
            [row["period"]["year"] for row in normalized_abatements],
            [2015, 2016, 2017, 2018, 2019, 2020, 2022, 2023, 2024],
        )
        ambiguous = next(row for row in abatements if row["claim_id"].endswith("2020_report"))
        self.assertNotIn("annual_series_key", ambiguous)
        self.assertIn("again labels", ambiguous["notes"])

    def test_fiscal_and_facility_boundaries_are_explicit(self):
        added = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(added["clm_study_apple_prineville_property_tax_billed_2024"]["value"], 167_888.68)
        self.assertIn("not proof of payment", added["clm_study_apple_prineville_property_tax_billed_2024"]["notes"])
        self.assertEqual(added["clm_study_apple_prineville_asr_sdc_2020"]["value"], 8_740_000)
        self.assertIn("must not be added", added["clm_study_apple_prineville_asr_sdc_2020"]["notes"])
        self.assertEqual(added["clm_study_apple_prineville_lrz_dc1_investment_projection"]["value"], 250_000_000)
        self.assertIn("not verified expenditure", added["clm_study_apple_prineville_lrz_dc1_investment_projection"]["notes"])
        self.assertEqual(added["clm_study_apple_prineville_jobs_2018"]["value"], 100)
        self.assertIn("direct versus contractor", added["clm_study_apple_prineville_jobs_2018"]["notes"])

        paid = sorted(
            (row for row in self.fragment["records"] if row.get("annual_series_key") == "apple_prineville_account_19494_property_tax_payments"),
            key=lambda row: row["period"]["year"],
        )
        self.assertEqual([row["period"]["year"] for row in paid], list(range(2016, 2026)))
        self.assertEqual(
            [row["value"] for row in paid],
            [23_669.77, 25_290.68, 26_020.69, 26_714.99, 27_660.23,
             29_465.89, 28_623.03, 29_531.74, 30_550.99, 31_334.07],
        )
        self.assertTrue(all("account 19494" in row["scope"]["label"] for row in paid))
        self.assertTrue(all("not the selected building" in row["notes"] for row in paid))

    def test_pdf_sources_have_auditable_page_locators(self):
        sources = {row["source_id"]: row for row in self.fragment["sources"]}
        for record in self.fragment["records"]:
            is_pdf = sources[record["source_id"]]["review_method"] in ("web_pdf_text", "pdf_text_and_page_image")
            self.assertEqual(is_pdf, "pdf_page" in record and "printed_page" in record)

    def test_description_and_two_pass_evidence_matrix(self):
        descriptions = [row["project_description"] for row in self.fragment["project_updates"] if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        for marker in ("1600 SW Baldwin Road", "9,228-square-foot", "May 2012", "DC No. 2"):
            self.assertIn(marker, descriptions[0])

        updates = self.fragment["project_updates"]
        self.assertEqual(len(updates), 12)
        self.assertEqual(
            {row["title"].split(" audit", 1)[0] for row in updates[:8]},
            {"Investment", "Construction", "Supplier", "Operations", "Fiscal", "Public-cost", "Resource", "Community"},
        )
        self.assertTrue(all(row["as_of"] == "2026-09-07" for row in updates))
        self.assertTrue(all("Source families checked:" in row["notes"] for row in updates[:8]))

    def test_directed_search_uses_exact_identifiers_and_alternate_sources(self):
        source_ids = {row["source_id"] for row in self.fragment["sources"]}
        self.assertTrue(
            {
                "src_study_crook_apple_assessor_19371_2026",
                "src_study_crook_apple_assessor_19494_2026",
                "src_study_business_oregon_lrz_apple_2025",
                "src_study_oregon_epermitting_apple_2026",
                "src_study_oregon_energy_apple_direct_access_2018",
                "src_study_owrd_prineville_asr_apple_context_2019",
                "src_study_oregon_deq_data_center_permit_2026",
                "src_study_cocc_apple_prineville_internship_2026",
                "src_study_apple_prineville_jobs_2026",
            }.issubset(source_ids)
        )
        trail = json.dumps(self.fragment["sources"] + self.fragment["project_updates"])
        for identifier in (
            "44.2894155", "151500-00-00312", "19371", "19494/R", "receipts 238920 through 444833", "217-26-000747-STR", "CCB 69988",
            "AL-26", "re77-krua", "Ordinances 1195/1219", "Resolutions 1571/1573",
        ):
            self.assertIn(identifier, trail)

    def test_corrective_modeling_gate_retains_five_narrow_syntheses(self):
        self.assertEqual(len(self.model_fragment["sources"]), 7)
        self.assertEqual(len(self.model_fragment["estimates"]), 5)
        rows = {row["estimate_id"]: row for row in self.model_fragment["estimates"]}

        threshold = rows["est_study_apple_prineville_acct19494_service_break_even_2025"]
        self.assertEqual(threshold["value"], 31_334.07)
        self.assertIn("not an estimate of actual public-service cost", threshold["interval"]["interpretation"])

        payroll = rows["est_study_apple_prineville_operating_payroll_sensitivity_2018"]
        self.assertEqual(
            (payroll["interval"]["low"], payroll["value"], payroll["interval"]["high"]),
            (4_372_000, 7_730_000, 11_800_000),
        )
        self.assertEqual(payroll["derivation"]["method"], "sensitivity_analysis")
        self.assertIn("not observed payroll", payroll["interval"]["interpretation"])

        electricity_cost = rows["est_study_apple_prineville_electricity_cost_sensitivity_fy2025"]
        self.assertEqual(
            (electricity_cost["interval"]["low"], electricity_cost["value"], electricity_cost["interval"]["high"]),
            (21_493_500, 22_107_600, 28_195_200),
        )
        self.assertIn("not Apple's tariff calculation", electricity_cost["interval"]["interpretation"])
        self.assertTrue(any("Schedule 748 cannot be calculated" in item for item in electricity_cost["limitations"]))

        average_load = rows["est_study_apple_prineville_average_electric_load_fy2025"]
        self.assertAlmostEqual(average_load["value"], 267_000_000 / 8_760 / 1_000)
        self.assertIn("not peak demand", average_load["interval"]["interpretation"])

        emissions = rows["est_study_apple_prineville_location_electric_emissions_fy2025"]
        self.assertAlmostEqual(emissions["interval"]["low"], 267_000 * 365 / 2_204.62262185)
        self.assertAlmostEqual(emissions["value"], 267_000 * 635.267 / 2_204.62262185)
        self.assertIn("100 percent renewable", json.dumps(emissions))

        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in rows.values()))
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows.values()))

        decisions = self.fragment["project_updates"][-1]["notes"]
        for candidate in (
            "Investment: rejected", "Construction: rejected", "Suppliers: rejected", "Operations: retained",
            "Fiscal: net result rejected", "Public costs: retained", "Resources: retained", "Community: rejected",
            "County employment: rejected", "County wages: rejected", "County GDP: rejected",
        ):
            self.assertIn(candidate, decisions)
        self.assertIn("Modeled additions: five", decisions)
        self.assertIn("direct forecasts remain four", decisions)


if __name__ == "__main__":
    unittest.main()
