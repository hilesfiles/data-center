import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00438078069"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class MetaAltoonaContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
        config = read_json(ROOT / "config/v1/private-sector-study-candidates.json")
        inventory = {row["entity_id"]: row for row in read_json(ROOT / "site/public/data/v1/facilities/index.json")}
        panels = {}
        for path in sorted((ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")):
            for row in read_json(path):
                panels[row["county_fips"]] = row
        policy = read_json(ROOT / "config/v1/study-modeling-policy.json")
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
        cls.fragment = read_json(EVIDENCE_FRAGMENT)
        cls.model_fragment = read_json(MODEL_FRAGMENT)

    def test_direct_account_counts_and_bounded_gaps(self):
        project = self.project
        self.assertEqual(
            (project["economic_record_count"], project["reported_actual_count"], project["projection_count"]),
            (101, 92, 9),
        )
        self.assertEqual(project["modeled_synthesis_count"], 17)
        self.assertTrue(MODEL_FRAGMENT.exists())
        self.assertTrue(
            all(
                row["aggregation"]["role"] == "standalone"
                and row["aggregation"]["overlap_policy"] == "do_not_sum_outside_declared_total"
                and row["presentation"] == "modeled_not_observed_or_audited"
                and row["scope"]["inventory_allocation"] in {"unallocated", "not_applicable"}
                for row in self.model_fragment["estimates"]
            )
        )
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], ["suppliers"])
        self.assertEqual(project["model_completeness"]["missing_county_outcomes"], [])

    def test_direct_records_preserve_award_phase_and_resource_boundaries(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(records["clm_study_meta_altoona_ieda_actual_investment_13"]["value"], 4_372_163_473)
        self.assertEqual(records["clm_study_meta_altoona_ieda_actual_investment_19"]["value"], 817_900_000)
        self.assertEqual(records["clm_study_meta_altoona_temporary_building_pilot_projection_2024"]["basis"], "source_projection")
        self.assertEqual(records["clm_study_meta_altoona_electricity_2024"]["value"], 1_585_392_000)
        self.assertEqual(records["clm_study_meta_altoona_permitted_generators_2024"]["value"], 112)
        self.assertEqual(records["clm_study_meta_altoona_ieda_qualifying_wage_13"]["value"], 23.12)
        self.assertEqual(records["clm_study_meta_altoona_ieda_qualifying_wage_19"]["value"], 53.87)
        self.assertTrue(
            all(
                records[claim_id]["basis"] == "source_projection"
                for claim_id in (
                    "clm_study_meta_altoona_ieda_qualifying_wage_13",
                    "clm_study_meta_altoona_ieda_qualifying_wage_19",
                )
            )
        )
        self.assertEqual(records["clm_study_meta_altoona_assessor_atn1_floor_area_2026"]["value"], 312_131)
        self.assertIn("candidate crosswalk", records["clm_study_meta_altoona_assessor_atn1_floor_area_2026"]["notes"])
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.fragment["records"]))
        self.assertIn("must not be summed", records["clm_study_meta_altoona_community_grants_2015"]["notes"])

    def test_all_active_real_estate_accounts_remain_separate(self):
        active_pins = {
            "792303400004",
            "792310100002",
            "792310200008",
            "792310300006",
            "792310377001",
            "792303400006",
            "792310100004",
            "792310200006",
            "792310200007",
            "792310401005",
        }
        added = self.fragment["records"]
        payments = [row for row in added if row["metric_code"] == "study.property_taxes_paid"]
        taxable = [row for row in added if row["metric_code"] == "study.taxable_assessed_value"]
        appraised = [row for row in added if row["metric_code"] == "study.appraised_property_value"]
        self.assertEqual((len(payments), len(taxable), len(appraised)), (50, 10, 10))
        self.assertEqual({row["scope"]["label"].split("PIN ")[1].split(";")[0] for row in payments}, active_pins)
        self.assertEqual({row["period"]["year"] for row in payments}, set(range(2020, 2025)))
        self.assertFalse(any(row["metric_code"] == "study.property_tax_billed" for row in added))

    def test_tax_aggregations_and_break_even_use_each_active_pin_once(self):
        estimates = self.model_fragment["estimates"]
        tax_rows = [row for row in estimates if row["metric_code"] == "study.modeled_combined_property_tax_paid"]
        expected = {
            2020: 1_321_478,
            2021: 1_834_994,
            2022: 1_846_260,
            2023: 2_219_356,
            2024: 2_249_854,
        }
        self.assertEqual({row["period"]["year"]: row["value"] for row in tax_rows}, expected)
        retired_pins = {
            "792303400001", "792303400003", "792310100001", "792310100003",
            "792310200001", "792310200002", "792310300001", "792310401002",
            "792310401003", "792310401004", "292310300006", "792303400002",
        }
        for row in tax_rows:
            year = row["period"]["year"]
            claim_ids = row["derivation"]["input_claim_ids"]
            self.assertEqual(len(claim_ids), 10)
            self.assertEqual(len(set(claim_ids)), 10)
            self.assertEqual(sum(parameter["value"] for parameter in row["parameters"]), expected[year])
            self.assertTrue(all(str(year) in claim_id for claim_id in claim_ids))
            self.assertFalse(any(pin in claim_id for pin in retired_pins for claim_id in claim_ids))
            self.assertIn("Do not add", row["limitations"][0])

        row_2024 = next(row for row in tax_rows if row["period"]["year"] == 2024)
        threshold = next(
            row for row in estimates
            if row["metric_code"] == "study.modeled_annual_local_service_cost_break_even"
        )
        self.assertEqual(threshold["value"], row_2024["value"])
        self.assertEqual(
            set(threshold["derivation"]["input_claim_ids"]),
            set(row_2024["derivation"]["input_claim_ids"]),
        )
        self.assertIn("not observed or estimated public cost", threshold["interval"]["interpretation"])
        self.assertIn("Do not sum", threshold["notes"])
        self.assertNotEqual(threshold["aggregation"]["aggregation_id"], row_2024["aggregation"]["aggregation_id"])

    def test_load_and_labor_models_reproduce_formulas_without_relabeling(self):
        estimates = self.model_fragment["estimates"]
        loads = [row for row in estimates if row["metric_code"] == "study.modeled_average_electric_load"]
        self.assertEqual(len(loads), 5)
        for row in loads:
            parameters = {parameter["name"]: parameter["value"] for parameter in row["parameters"]}
            expected = parameters["annual_electricity_use"] / parameters["calendar_hours"] / 1_000
            self.assertAlmostEqual(row["value"], expected, places=12)
            self.assertIn("not peak", row["limitations"][0].lower())
        load_2024 = next(row for row in loads if row["period"]["year"] == 2024)
        self.assertEqual(
            {parameter["name"]: parameter["value"] for parameter in load_2024["parameters"]}["calendar_hours"],
            8_784,
        )

        job_years = next(
            row for row in estimates
            if row["metric_code"] == "study.modeled_construction_job_years_direct"
        )
        self.assertAlmostEqual(job_years["value"], 8_700_000 / 2_080, places=12)
        self.assertIn("not unique workers", job_years["limitations"][0].lower())

        construction_payroll = next(
            row for row in estimates if row["metric_code"] == "study.modeled_construction_payroll"
        )
        self.assertEqual(
            (construction_payroll["interval"]["low"], construction_payroll["value"], construction_payroll["interval"]["high"]),
            (201_144_000, 334_906_500, 468_669_000),
        )
        self.assertEqual(
            set(construction_payroll["derivation"]["input_claim_ids"]),
            {
                "clm_study_meta_altoona_ieda_qualifying_wage_13",
                "clm_study_meta_altoona_ieda_qualifying_wage_19",
            },
        )
        self.assertIn("not observed", construction_payroll["limitations"][0].lower())

        operating_payroll = next(
            row for row in estimates
            if row["metric_code"] == "study.modeled_operating_payroll_sensitivity"
        )
        self.assertEqual(
            (operating_payroll["interval"]["low"], operating_payroll["value"], operating_payroll["interval"]["high"]),
            (19_235_840, 32_027_840, 44_819_840),
        )
        self.assertIn("clm_study_meta_altoona_operating_workers_2021", operating_payroll["derivation"]["input_claim_ids"])
        self.assertIn("employees and contractors", operating_payroll["scope"]["label"])

    def test_county_gaps_keep_both_treatments_and_noncausal_limits(self):
        rows = [row for row in self.model_fragment["estimates"] if "comparison_gap" in row["metric_code"]]
        self.assertEqual(len(rows), 3)
        expected = {
            "study.modeled_county_employment_comparison_gap": (2.8236400231913095, 1.9799545193307067, 4.260418471616201),
            "study.modeled_county_wage_comparison_gap": (-0.39497957882470014, -0.833173880311433, 0.1112883499460704),
            "study.modeled_county_gdp_comparison_gap": (8.81020817695295, 4.8605943661724105, 13.547587076477496),
        }
        for row in rows:
            central, low, high = expected[row["metric_code"]]
            self.assertEqual((row["value"], row["interval"]["low"], row["interval"]["high"]), (central, low, high))
            parameters = {parameter["name"] for parameter in row["parameters"]}
            self.assertIn("construction_start_treatment_gap", parameters)
            self.assertIn("first_operation_treatment_gap", parameters)
            self.assertIn("preperiod_log_index_rmse", parameters)
            self.assertEqual(row["confidence"], "low")
            self.assertNotIn("causal_design", row)
            self.assertIn("Must not be interpreted", row["limitations"][0])

    def test_water_catalog_handoff_is_approximate_and_machine_readable(self):
        update = next(
            row for row in self.fragment["project_updates"]
            if row["title"] == "Policy-authorized synthesis and water-catalog reconciliation payload"
        )
        notes = update["notes"]
        metric_text = notes.split("WATER_METRIC_PROPOSAL_JSON=", 1)[1].split("; WATER_RECORDS_PROPOSAL_JSON=", 1)[0]
        records_and_expectation = notes.split("; WATER_RECORDS_PROPOSAL_JSON=", 1)[1]
        records_text, expectation_tail = records_and_expectation.split("; WATER_REGRESSION_EXPECTATION_JSON=", 1)
        expectation_text = expectation_tail.split(". Until that catalog change", 1)[0]
        metric = json.loads(metric_text)
        records = json.loads(records_text)
        expectation = json.loads(expectation_text)["after_catalog_addition"]
        self.assertEqual(metric["metric_code"], "study.annual_water_withdrawal")
        self.assertEqual(metric["unit"], "gallons_per_year")
        self.assertEqual(metric["aggregation"], "none")
        self.assertEqual([row["period"]["year"] for row in records], list(range(2020, 2025)))
        source_values_megaliters = [151, 140, 199, 173, 242]
        series_values_gallons = [
            39889979.906080,
            36984087.330141,
            52570238.419272,
            45701765.057960,
            63929636.670672,
        ]
        conversion_factor = 264172.0523581484
        self.assertEqual([row["value"] for row in records], series_values_gallons)
        self.assertTrue(all(row["value_qualifier"] == "approximately" for row in records))
        self.assertTrue(all(row["annual_series_key"] == "meta_altoona_water_withdrawal" for row in records))
        for source_value, record in zip(source_values_megaliters, records, strict=True):
            self.assertIn("Section 3.1, Water Withdrawal by Facility table", record["source_locator"])
            self.assertIn("PDF page 8 (printed page I)", record["source_locator"])
            self.assertIn(f"reported {source_value} ML", record["source_locator"])
            self.assertIn("rounded to the nearest whole digit", record["source_locator"])
            self.assertIn("1,000,000 L / 3.785411784 L per US gallon", record["source_locator"])
            self.assertIn(f"Source reports approximately {source_value} megaliters", record["notes"])
            self.assertIn("PDF page 8 (printed page I)", record["notes"])
            self.assertIn("rounded to the nearest whole digit", record["notes"])
            self.assertIn("264,172.0523581484 US gallons per ML", record["notes"])
            self.assertIn("inherits the source whole-ML rounding", record["notes"])
            self.assertLess(abs(record["value"] - source_value * conversion_factor), 0.000001)
        self.assertEqual(expectation["unit"], "gallons_per_year")
        self.assertEqual(expectation["aggregation"], "none")
        self.assertEqual(expectation["conversion_factor_gallons_per_megaliter"], conversion_factor)
        self.assertEqual(expectation["source_values_megaliters"], source_values_megaliters)
        self.assertEqual(expectation["series_values_gallons"], series_values_gallons)
        self.assertEqual(
            (expectation["fragment_record_count"], expectation["merged_economic_record_count"], expectation["modeled_synthesis_count"]),
            (105, 106, 17),
        )

    def test_description_search_matrix_and_candidate_status_are_explicit(self):
        updates = self.fragment["project_updates"]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertGreaterEqual(len(updates), 14)
        search_log = " ".join(row["notes"].lower() for row in updates)
        for family in (
            "assessor",
            "permit",
            "utility",
            "incentive",
            "supplier",
            "workforce",
            "community",
            "recipient",
            "qcew",
            "gdp",
        ):
            self.assertIn(family, search_log)
        self.assertIn("all 34 results", search_log)
        self.assertIn("observed public costs", updates[-1]["notes"].lower())
        self.assertIn("candidate_corrected_round2_pending_adversarial_review", updates[-1]["notes"])
        self.assertIn("17 estimates", updates[-1]["notes"])


if __name__ == "__main__":
    unittest.main()
