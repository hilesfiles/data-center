import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00499403180"
FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
SYNTHESIS_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class MicrosoftQuincyContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
        cls.synthesis_fragment = json.loads(SYNTHESIS_FRAGMENT.read_text(encoding="utf-8"))
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

    def test_fragment_is_valid_scoped_and_provisional(self):
        self.assertEqual(self.fragment["project_id"], PROJECT_ID)
        self.assertEqual((len(self.fragment["sources"]), len(self.fragment["records"]), len(self.fragment["project_updates"])), (29, 46, 31))
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment["records"]))
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment["project_updates"]))
        self.assertEqual(
            (
                sum(row["basis"] == "reported_actual" for row in self.fragment["records"]),
                sum(row["basis"] == "source_projection" for row in self.fragment["records"]),
            ),
            (45, 1),
        )
        validate_evidence(self.evidence, self.config["candidates"])
        self.assertEqual(len(self.synthesis_fragment["estimates"]), 41)
        self.assertEqual(
            (
                self.project["economic_record_count"],
                self.project["reported_actual_count"],
                self.project["projection_count"],
                self.project["modeled_synthesis_count"],
            ),
            (47, 46, 1, 41),
        )
        self.assertIn("candidate_pending_adversarial_review", self.fragment["project_updates"][-1]["notes"])
        self.assertIn("all unaccepted pending adversarial review", self.fragment["project_updates"][-1]["notes"])

    def test_boundary_correction_is_explicit_and_description_is_singular(self):
        descriptions = [row["project_description"] for row in self.fragment["project_updates"] if row.get("project_description")]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        for text in ("143,439-square-foot", "MWH", "1515 Port Industrial Way", "Columbia", "501 Port Industrial Parkway"):
            self.assertIn(text, descriptions[0])
        boundary = self.fragment["project_updates"][0]["notes"]
        self.assertIn("2007 is rejected as selected-building treatment timing", boundary)
        self.assertIn("2014/2015 through 2022", boundary)
        self.assertIn("No source crosswalks this polygon", boundary)
        self.assertEqual(self.project["project_description"], descriptions[0])

    def test_assessor_series_are_separate_complete_and_unallocated(self):
        rows = self.fragment["records"]
        assessed = [row for row in rows if row["metric_code"] == "study.account_assessed_value"]
        taxes = [
            row for row in rows
            if row["metric_code"] == "study.property_taxes_paid"
            and row.get("annual_series_key", "").startswith("msft_mwh_")
        ]
        self.assertEqual(len(assessed), 16)
        self.assertEqual(len(taxes), 9)
        by_series = {}
        for row in assessed + taxes:
            by_series.setdefault(row["annual_series_key"], {})[row["period"]["year"]] = row["value"]
            self.assertEqual(row["scope"]["inventory_allocation"], "unallocated")
        self.assertEqual(set(by_series["msft_mwh_real_account_assessed_value"]), set(range(2018, 2026)))
        self.assertEqual(set(by_series["msft_mwh_personal_account_assessed_value"]), set(range(2018, 2026)))
        self.assertEqual(by_series["msft_mwh_real_account_assessed_value"][2025], 917_786_694)
        self.assertEqual(by_series["msft_mwh_personal_account_assessed_value"][2025], 644_559_000)
        self.assertEqual(by_series["msft_mwh_real_property_tax_paid"][2026], 7_493_919.07)
        self.assertEqual(by_series["msft_mwh_personal_property_tax_paid"][2025], 9_106_834.90)
        self.assertNotIn(2026, by_series["msft_mwh_personal_property_tax_paid"])
        locators = " ".join(row["source_locator"] for row in taxes)
        for statement_id in ("727932021", "727932022", "57704", "57524", "57298", "841392021", "841392022", "61710", "61472"):
            self.assertIn(statement_id, locators)
        personal_2025 = next(row for row in taxes if row["period"]["year"] == 2025 and "personal" in row["scope"]["label"])
        self.assertIn("$2,631,463.16 was paid and $2,631,463.07 remained due", personal_2025["notes"])

    def test_combined_tax_models_are_exact_complete_year_aggregations(self):
        estimates = self.synthesis_fragment["estimates"]
        combined = [row for row in estimates if row["metric_code"] == "study.modeled_combined_property_tax_paid"]
        self.assertEqual(
            {row["period"]["year"]: row["value"] for row in combined},
            {2022: 13_779_602.28, 2023: 14_896_170.10, 2024: 14_797_546.41, 2025: 13_834_882.15},
        )
        self.assertTrue(all(row["scope"]["level"] == "campus" and row["scope"]["inventory_allocation"] == "unallocated" for row in combined))
        self.assertFalse(any(row["period"].get("year") == 2026 for row in combined))
        for row in combined:
            self.assertAlmostEqual(row["value"], sum(parameter["value"] for parameter in row["parameters"]), places=2)
            self.assertTrue(any("not an audited government-wide receipt or net benefit" in text.lower() for text in row["limitations"]))
        thresholds = [row for row in estimates if row["metric_code"] == "study.modeled_annual_local_service_cost_break_even"]
        self.assertEqual(
            {row["period"]["year"]: row["value"] for row in thresholds},
            {2022: 13_779_602.28, 2023: 14_896_170.10, 2024: 14_797_546.41, 2025: 13_834_882.15},
        )
        self.assertTrue(all(row["scope"]["level"] == "campus" for row in thresholds))
        self.assertTrue(all(any("not an actual public cost" in text.lower() or "not an estimate of actual public-service cost" in text.lower() for text in row["limitations"]) for row in thresholds))

    def test_nonfiscal_records_preserve_measure_and_scope_boundaries(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        generators = records["clm_study_msft_mwh_permitted_generator_count_2022"]
        self.assertEqual(generators["value"], 117)
        self.assertEqual(generators["scope"]["level"], "campus")
        self.assertIn("not a selected-building count", generators["notes"])
        gift = records["clm_study_msft_bbcc_scholarship_gift_2021"]
        self.assertEqual(gift["value"], 25_000)
        self.assertEqual(gift["scope"]["level"], "company_county")
        self.assertIn("may be nested", gift["notes"])
        power = records["clm_study_msft_grantpud_lpfa_award_2021"]
        self.assertEqual((power["value"], power["basis"]), (4_807_473, "source_projection"))
        self.assertEqual(power["scope"]["level"], "multi_campus_county")
        self.assertIn("does not establish a cash payment", power["notes"])
        baseline = next(
            row for row in self.evidence["records"]
            if row["claim_id"] == "clm_study_quincy_water_reuse_cost"
        )
        self.assertEqual((baseline["value"], baseline["metric_code"]), (31_000_000, "study.infrastructure_project_cost"))
        outlays = [row for row in self.fragment["records"] if row["metric_code"] == "study.infrastructure_fund_expenditure"]
        self.assertEqual([row["value"] for row in outlays], [15_583_730, 237_368.53, 816_693])
        self.assertEqual([row["period"]["kind"] for row in outlays], ["calendar_year", "calendar_year", "reported_snapshot"])
        self.assertTrue(all("overlap" in row["notes"] or "nested" in row["notes"] for row in outlays))

    def test_regional_actuals_and_community_nesting_are_retained_at_true_scope(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        direct = records["clm_study_msft_central_wa_direct_jobs_2024"]
        contractors = records["clm_study_msft_central_wa_onsite_contractors_2024"]
        self.assertEqual((direct["value"], contractors["value"]), (377, 287))
        self.assertEqual((direct["basis"], contractors["basis"]), ("reported_actual", "reported_actual"))
        self.assertTrue(all(row["scope"]["level"] == "company_county" for row in (direct, contractors)))
        self.assertIn("not MWH campus headcount", direct["notes"])
        self.assertIn("already included", contractors["notes"])

        regional_tax = records["clm_study_msft_central_wa_property_taxes_2024"]
        cumulative_tax = records["clm_study_msft_central_wa_property_taxes_fy2019_fy2024"]
        community = records["clm_study_msft_central_wa_community_funding_fy2019_fy2024"]
        self.assertEqual((regional_tax["value"], cumulative_tax["value"], community["value"]), (26_400_000, 123_100_000, 2_000_000))
        self.assertIn("overlaps", regional_tax["notes"])
        self.assertIn("Recipient awards", community["notes"])

        nested = {
            claim_id: records[claim_id]["value"]
            for claim_id in (
                "clm_study_msft_pay_forward_rebate_total_2019",
                "clm_study_msft_pay_forward_cbf_component_2019",
                "clm_study_msft_pay_forward_bbcc_wec_2019",
                "clm_study_msft_pay_forward_healthy_food_2019",
                "clm_study_msft_pay_forward_school_environment_2019",
                "clm_study_msft_pay_forward_share_warmth_2019",
            )
        }
        self.assertEqual(nested["clm_study_msft_pay_forward_rebate_total_2019"], 480_000)
        self.assertEqual(nested["clm_study_msft_pay_forward_cbf_component_2019"] + nested["clm_study_msft_pay_forward_share_warmth_2019"], 480_000)
        self.assertEqual(nested["clm_study_msft_pay_forward_bbcc_wec_2019"] + nested["clm_study_msft_pay_forward_healthy_food_2019"] + nested["clm_study_msft_pay_forward_school_environment_2019"], 470_000)
        self.assertTrue(all("nested" in records[claim_id]["notes"].lower() for claim_id in nested))

    def test_regional_source_models_payroll_resources_and_supplier_scope(self):
        estimates = {row["metric_code"]: row for row in self.synthesis_fragment["estimates"]}
        expected = {
            "study.modeled_direct_labor_compensation": 35_061_000,
            "study.modeled_additional_operational_jobs_supported": 855,
            "study.modeled_operating_regional_gdp_contribution": 269_000_000,
            "study.modeled_construction_job_years_total": 8_821,
            "study.modeled_construction_labor_income_total": 805_900_000,
            "study.modeled_construction_regional_economic_activity_total": 1_200_000_000,
            "study.modeled_annual_construction_jobs_supported": 1_400,
            "study.modeled_annual_direct_construction_jobs": 698,
            "study.modeled_annual_construction_labor_income": 134_000_000,
            "study.modeled_annual_construction_regional_economic_activity": 200_000_000,
            "study.modeled_local_sales_taxes_supported": 4_600_000,
            "study.modeled_regional_property_tax_share": 14.8,
            "study.modeled_pay_it_forward_awards": 58_000,
            "study.modeled_average_load_equivalent_of_efficiency_savings": 3.8128,
            "study.modeled_qwru_annual_potable_water_availability": 396_258_078,
        }
        self.assertEqual({metric: estimates[metric]["value"] for metric in expected}, expected)
        payroll = estimates["study.modeled_direct_labor_compensation"]
        self.assertEqual((payroll["interval"]["low"], payroll["interval"]["high"]), (34_872_500, 35_249_500))
        self.assertIn("includes benefits", json.dumps(payroll).lower())
        self.assertFalse(any(row["category"] == "suppliers" for row in self.synthesis_fragment["estimates"]))
        contractor_claim = next(row for row in self.fragment["records"] if row["claim_id"] == "clm_study_msft_central_wa_onsite_contractors_2024")
        self.assertEqual(contractor_claim["value"], 287)
        self.assertIn("not a supplier-firm count", contractor_claim["notes"])
        load = estimates["study.modeled_average_load_equivalent_of_efficiency_savings"]
        self.assertIn("not actual load", " ".join(load["limitations"]).lower())
        efficiency_update = next(row for row in self.fragment["project_updates"] if row["title"].endswith("efficiency savings and average-load test"))
        for token in ("310 MW", "650 MW", "$163 million", "2028", "none is a Microsoft or MWH allocation"):
            self.assertIn(token, efficiency_update["notes"])
        water = estimates["study.modeled_qwru_annual_potable_water_availability"]
        self.assertIn("not actual facility consumption", " ".join(water["limitations"]).lower())

    def test_actual_water_orchestration_payload_and_generator_ceilings_are_tested(self):
        water_update = next(row for row in self.fragment["project_updates"] if row["title"].endswith("water payload, reuse effects and regulatory ceilings"))
        for token in (
            '"metric_code":"study.annual_water_use"',
            '"unit":"gallons_per_year"',
            '"annual_series_key":"msft_mwh_annual_water_use"',
            "1,657,088 gallons/year",
            "438,815 gallons/day",
            "PM10 24/25",
            "NOx 53/64",
            "1,034 pounds",
        ):
            self.assertIn(token, water_update["notes"])
        self.assertFalse(any(row["metric_code"] == "study.annual_water_use" for row in self.fragment["records"]))
        self.assertFalse(any(row["metric_code"] == "study.annual_water_use" for row in self.synthesis_fragment["estimates"]))

    def test_county_gap_models_are_descriptive_and_diagnosed(self):
        comparisons = [row for row in self.synthesis_fragment["estimates"] if row["category"] == "county_outcome"]
        self.assertEqual(len(comparisons), 6)
        self.assertEqual({row["metric_code"] for row in comparisons}, {
            "study.modeled_county_gdp_comparison_gap",
            "study.modeled_county_employment_comparison_gap",
            "study.modeled_county_wage_comparison_gap",
        })
        self.assertTrue(all(row["derivation"]["method"] == "benchmark_application" for row in comparisons))
        self.assertTrue(all("causal_design" not in row for row in comparisons))
        self.assertTrue(all(row["confidence"] == "low" for row in comparisons))
        self.assertTrue(all(len(row["notes"].split("Donors: ")[1].rstrip(".").split(",")) == 20 for row in comparisons))
        self.assertEqual(
            sorted(row["value"] for row in comparisons),
            sorted([39.5137, 18.4644, 22.1521, 18.6355, -6.9430, 21.0250]),
        )
        audit = self.fragment["project_updates"][-1]["notes"]
        for token in ("exactly six pre-periods", "leave-one-out", "zero selected donor FIPS", "Causal interpretation fails"):
            self.assertIn(token, audit)

    def test_each_industry_chart_output_is_individually_retained_and_nonadditive(self):
        rows = [
            row for row in self.synthesis_fragment["estimates"]
            if row["metric_code"].startswith("study.modeled_additional_jobs_industry_")
        ]
        expected = {
            "security": 200,
            "power_generation_transmission": 167,
            "employment_other_services": 114,
            "maintenance_repair": 99,
            "retail": 62,
            "healthcare_other": 56,
            "restaurants": 47,
            "other_real_estate": 46,
            "support_services": 42,
            "professional_technical": 31,
            "transportation_warehousing": 17,
            "manufacturing": 3,
        }
        self.assertEqual(len(rows), 12)
        self.assertEqual(
            {row["metric_code"].removeprefix("study.modeled_additional_jobs_industry_"): row["value"] for row in rows},
            expected,
        )
        self.assertEqual(sum(row["value"] for row in rows), 884)
        headline = next(row for row in self.synthesis_fragment["estimates"] if row["metric_code"] == "study.modeled_additional_operational_jobs_supported")
        self.assertEqual(headline["value"], 855)
        self.assertTrue(all(row["scope"]["level"] == "multi_county" for row in rows))
        self.assertTrue(all(row["category"] == "operations" for row in rows))
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in rows))
        self.assertTrue(all(row["derivation"]["method"] == "benchmark_application" for row in rows))
        for row in rows:
            text = " ".join(row["limitations"] + [row["notes"]])
            for token in ("non-additive", "855", "287", "every other chart category", "884-versus-855"):
                self.assertIn(token, text)

        audit = " ".join(row["notes"] for row in self.fragment["project_updates"])
        for token in (
            "study.modeled_community_people_impacted",
            "structurally unsuitable",
            "unique-person deduplication",
            "catalog's missing people unit is secondary",
            "explicitly rejected as a separate metric/model",
            "855 / 377 = 2.2679",
            "2 × 377 = 754",
        ):
            self.assertIn(token, audit)

    def test_search_audit_and_metric_model_dispositions_are_complete(self):
        updates = self.fragment["project_updates"]
        titles = [row["title"] for row in updates]
        self.assertEqual(sum(title.startswith("Direct discovery") for title in titles), 8)
        self.assertEqual(sum(title.startswith("Gap closure") for title in titles), 5)
        self.assertEqual(sum(title.startswith("Adversarial continuation") for title in titles), 1)
        self.assertEqual(sum(title.startswith("Corrective audit") for title in titles), 8)
        self.assertEqual(sum(title.startswith("Corrective adversarial continuation") for title in titles), 1)
        self.assertEqual(sum(title.startswith("Third corrective audit") for title in titles), 7)
        self.assertEqual(sum(title.startswith("Third corrective adversarial continuation") for title in titles), 1)
        audit = " ".join(row["notes"] for row in updates)
        for token in (
            "Source families checked:",
            "Queries/identifiers:",
            "account 72793",
            "account 84139",
            "22AQ-E035",
            "201805050",
            "140-10532",
            "WAR313961",
            "A0250310",
            "202403581",
            "QB 206(D)",
            "No records requests were made",
        ):
            self.assertIn(token, audit)
        decisions = updates[-1]["notes"]
        for metric_family in (
            "Investment",
            "Construction",
            "Operations",
            "Suppliers",
            "Fiscal",
            "Community",
            "Electric/water/wastewater/reuse",
            "Generators/emissions",
            "County employment",
            "wages and GDP",
        ):
            self.assertIn(metric_family, decisions)
        for rejected_model in (
            "assessor-to-investment",
            "footprint tax allocation",
            "generator energy/emissions",
            "construction job-year/payroll",
            "supplier/local-spend",
            "causal county-effect",
        ):
            self.assertIn(rejected_model, decisions)
        self.assertIn("Model tally: 41 estimates total", decisions)
        self.assertIn("four 2022-2025 equal-cost identities", decisions)
        self.assertEqual(
            self.project["model_completeness"]["missing_categories"],
            ["suppliers"],
        )


if __name__ == "__main__":
    unittest.main()
