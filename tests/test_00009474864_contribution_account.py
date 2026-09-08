import json
import math
import statistics
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis
from scripts.validate_data_contract import ContractValidator


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_campus_00009474864"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class GoogleLenoirContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.synthesis_fragment = json.loads(MODEL_FRAGMENT.read_text(encoding="utf-8"))
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        config = json.loads(
            (ROOT / "config/v1/private-sector-study-candidates.json").read_text(encoding="utf-8")
        )
        inventory = {
            row["entity_id"]: row
            for row in json.loads(
                (ROOT / "site/public/data/v1/facilities/index.json").read_text(encoding="utf-8")
            )
        }
        cls.panels = {}
        for path in sorted(
            (ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")
        ):
            for row in json.loads(path.read_text(encoding="utf-8")):
                cls.panels[row["county_fips"]] = row
        cls.study_counties = {row["county_fips"] for row in config["candidates"]}
        policy = json.loads(
            (ROOT / "config/v1/study-modeling-policy.json").read_text(encoding="utf-8")
        )
        _, details, _ = build_products(
            config,
            inventory,
            cls.panels,
            "2026-09-07T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            policy,
        )
        cls.project = next(row for row in details if row["project_id"] == PROJECT_ID)

    def test_fragments_validate_and_have_expected_basis_split(self):
        issues = ContractValidator(ROOT / "schemas/v1").validate_record(
            self.evidence, ROOT / "schemas/v1/study-economic-evidence.schema.json"
        )
        self.assertEqual(issues, [])
        issues = ContractValidator(ROOT / "schemas/v1").validate_record(
            self.synthesis, ROOT / "schemas/v1/study-modeled-synthesis.schema.json"
        )
        self.assertEqual(issues, [])
        self.assertEqual(len(self.fragment["sources"]), 53)
        self.assertEqual(len(self.fragment["records"]), 161)
        self.assertEqual(len(self.fragment["project_updates"]), 33)
        self.assertEqual(
            sum(row["basis"] == "reported_actual" for row in self.fragment["records"]), 145
        )
        self.assertEqual(
            sum(row["basis"] == "source_projection" for row in self.fragment["records"]), 16
        )
        self.assertEqual(len(self.synthesis_fragment["estimates"]), 17)
        self.assertEqual(self.project["economic_record_count"], 162)
        self.assertEqual(self.project["reported_actual_count"], 145)
        self.assertEqual(self.project["projection_count"], 17)
        self.assertEqual(self.project["modeled_synthesis_count"], 17)
        self.assertEqual(
            self.fragment["project_updates"][-1]["title"],
            "Second corrective handoff ready for independent re-audit",
        )
        self.assertIn(
            "corrective_handoff_ready",
            self.fragment["project_updates"][-1]["notes"],
        )
        self.assertIn(
            "status=gap_closure_in_progress",
            self.fragment["project_updates"][-1]["notes"],
        )
        self.assertIn(
            "9ae8fbd8dfd55b435f340f58c03eab23b48bb782",
            self.fragment["project_updates"][-1]["notes"],
        )
        self.assertIn("does not claim project completion", self.fragment["project_updates"][-1]["notes"])

    def test_one_project_description_and_auditable_search_matrix(self):
        descriptions = [
            row["project_description"]
            for row in self.fragment["project_updates"]
            if "project_description" in row
        ]
        self.assertEqual(len(descriptions), 1)
        self.assertIn("708 Lynhaven Drive", descriptions[0])
        self.assertIn("May 2008", descriptions[0])
        self.assertIn("Project Cardinal", descriptions[0])
        text = " ".join(
            row["title"] + " " + row["notes"] for row in self.fragment["project_updates"]
        ).lower()
        for term in (
            "contract 3.1.0",
            "assessor",
            "tax-bill",
            "abatement",
            "permit",
            "planning",
            "water",
            "electricity",
            "workforce",
            "payroll",
            "procurement",
            "supplier",
            "community-recipient",
            "bond",
            "sec/corporate",
            "public-cost",
            "county-outcome",
            "1400204.24a",
            "09733t10",
            "2748394394",
            "2748287853",
            "lnr4a",
            "taxviewpublic",
            "account 132226",
            "shoulder tap",
            "e-7 sub 989",
            "ncg01",
            "laserfiche",
            "no same-scope marginal",
            "sign reversal",
        ):
            self.assertIn(term, text)

    def test_corrective_matrix_and_metric_ledger_are_structured_and_complete(self):
        updates = {row["title"]: row for row in self.fragment["project_updates"]}
        matrix = json.loads(updates["Corrective reopening direct-evidence family matrix"]["notes"])
        self.assertEqual(matrix["contract"], "3.1.0")
        self.assertIn("gap_closure_in_progress", matrix["status"])
        self.assertEqual(len(matrix["families"]), 8)
        self.assertIn("Shoulder Tap LLC", matrix["boundary"]["entities_identifiers"])
        for family in matrix["families"]:
            self.assertTrue(family["portals_collections"])
            self.assertTrue(family["queries_entities_dates"])
            self.assertTrue(family["records_opened"])
            self.assertIn("outcome_alternates_negative_limit", family)

        ledger = json.loads(updates["Corrective reopening metric disposition ledger"]["notes"])
        self.assertIn("gap_closure_in_progress", ledger["status"])
        self.assertEqual(len(ledger["dispositions"]), 26)
        self.assertEqual(
            {row["metric"] for row in ledger["dispositions"]},
            {
                "campus investment",
                "construction cost",
                "construction workers and payroll",
                "LNR4A floor area and design capacity",
                "annual-average operating FTE",
                "operating payroll and benefits",
                "supplier payments",
                "supplier geography/local share",
                "assessed value",
                "local tax receipts/payments",
                "City abatements",
                "County and Project Cardinal incentives",
                "JDIG",
                "same-scope marginal public-service cost",
                "net fiscal contribution",
                "electricity consumption and peak load",
                "electric utility bill",
                "water withdrawal/consumption/discharge",
                "water/sewer utility bill",
                "PUE and carbon-free-energy share",
                "air emissions",
                "brownfield/remediation cost",
                "community transfers",
                "county employment comparison",
                "county wage comparison",
                "county GDP comparison",
            },
        )
        for disposition in ledger["dispositions"]:
            self.assertTrue(disposition["repositories_identifiers_years"])
            self.assertTrue(disposition["model"])
            self.assertTrue(disposition["gap_or_rejection"])
        city_abatements = next(
            row for row in ledger["dispositions"] if row["metric"] == "City abatements"
        )
        self.assertIn("nine Technology Business", city_abatements["retained"])
        self.assertIn("$52,896,864", city_abatements["model"])
        self.assertIn("No annual gap remains", city_abatements["gap_or_rejection"])

        source_ids = {row["source_id"] for row in self.fragment["sources"]}
        self.assertTrue(
            {
                "src_study_caldwell_taxview_arcgis_2026",
                "src_study_lenoir_acfr_2017",
                "src_study_lenoir_acfr_2021",
                "src_study_ncdeq_tapaha_air_review_2017",
                "src_study_ncdeq_tapaha_air_review_2021",
                "src_study_ncdeq_singer_emp_2014",
                "src_study_ncuc_duke_rate_order_2012",
                "src_study_caldwell_department_list_2017",
                "src_study_nc_labor_google_elevator_26169",
                "src_study_caldwell_appraisal_2749515252_2027",
                "src_study_caldwell_appraisal_2748394394_2027",
                "src_study_ncdeq_construction_cocs_2026",
                "src_study_cccti_connect_grant_2021",
            }
            <= source_ids
        )
        prior = next(
            row
            for row in self.fragment["project_updates"]
            if row["title"] == "Superseded prior acceptance audit after adversarial continuation"
        )
        self.assertIn("superseded_acceptance", prior["notes"])

    def test_second_corrective_sources_preserve_archive_and_fixed_width_urls(self):
        sources = {row["source_id"]: row for row in self.fragment["sources"]}
        fy2021 = sources["src_study_lenoir_acfr_2021"]
        self.assertEqual(
            fy2021["url"],
            "https://cityoflenoir.com/Archive/ViewFile/Item/109",
        )
        self.assertEqual(
            fy2021["artifact_sha256"],
            "7374854c8ac10ed236727e6f5821f82b1aad9d1aed26ce9768b7593040d6cac7",
        )
        expected_urls = {
            "2748674403": "06121%20%201%20%207",
            "2748675303": "06121%20%201%20%208",
            "2749515252": "06161%20%201%20%201",
            "2749407243": "06161%20%201%20%201C",
            "2748588021": "06161%20%201%20%201B",
            "2748673488": "06121%20%201%2010A",
            "2748394394": "06162%20%201%20%201A",
            "2748492502": "06162%20%201%20%203",
            "2748287853": "06162%20%201%20%201C",
        }
        for ncpin, encoded_pid in expected_urls.items():
            source = sources[f"src_study_caldwell_appraisal_{ncpin}_2027"]
            self.assertEqual(
                source["url"],
                "https://gis.caldwellcountync.org/itspublic/"
                f"AppraisalCard.aspx?id={encoded_pid}",
            )
            self.assertEqual(len(source["artifact_sha256"]), 64)
            self.assertIn("fixed-width PID", source["notes"])
            self.assertIn("tax year 2027", source["notes"].lower())
        challenge = next(
            row
            for row in self.fragment["project_updates"]
            if row["title"].startswith("Adversarial challenge 01")
        )
        self.assertIn("approximately 647-byte HTML wrappers", challenge["notes"])
        replay = next(
            row
            for row in self.fragment["project_updates"]
            if row["title"] == "Second corrective City Finance archive and tax-schedule replay"
        )
        self.assertIn("$8,068,908", replay["notes"])
        self.assertIn("$5,702,923", replay["notes"])
        self.assertIn("city-wide", replay["notes"].lower())

    def test_adversarial_challenge_reports_are_complete_and_dispositive(self):
        reports = [
            row
            for row in self.fragment["project_updates"]
            if row["title"].startswith("Adversarial challenge ")
        ]
        self.assertEqual(len(reports), 11)
        self.assertEqual(
            {int(row["title"].split()[2]) for row in reports}, set(range(1, 12))
        )
        for report in reports:
            for label in (
                "Repositories:",
                "Query terms/date range:",
                "Material records:",
                "Alternate routes:",
                "Resulting claim/model/rejection:",
            ):
                self.assertIn(label, report["notes"])
        corpus = " ".join(row["notes"] for row in reports).lower()
        for term in (
            "tax year 2027",
            "department 6574",
            "december 19 2006",
            "ncc242598",
            "annual-average fte",
            "supplier-payment",
            "sawmill 100kv",
            "meter volumes",
            "fiscal break-even threshold",
            "$100,000 2020",
            "treatment-anchor",
        ):
            self.assertIn(term, corpus)

    def test_air_emissions_history_is_direct_and_facility_unallocated(self):
        emission_records = [
            row
            for row in self.fragment["records"]
            if row["metric_code"].startswith("study.actual_")
            and row["metric_code"].endswith("_emissions")
        ]
        expected_years = {2010, *range(2013, 2024)}
        self.assertEqual({row["period"]["year"] for row in emission_records}, expected_years)
        self.assertEqual(len(emission_records), 7 * len(expected_years))
        self.assertTrue(all(row["basis"] == "reported_actual" for row in emission_records))
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in emission_records)
        )
        nox = {
            row["period"]["year"]: row["value"]
            for row in emission_records
            if row["metric_code"] == "study.actual_nox_emissions"
        }
        self.assertEqual(nox[2010], 2.49)
        self.assertEqual(nox[2015], 37.71)
        self.assertEqual(nox[2016], 30.48)
        self.assertEqual(nox[2018], 11.07)
        self.assertEqual(nox[2023], 20.51)

    def test_direct_series_preserve_property_and_incentive_meaning(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        google = {
            row["period"]["year"]: row["value"]
            for row in records.values()
            if row.get("annual_series_key") == "google_lenoir_google_assessed_value"
        }
        tapaha = {
            row["period"]["year"]: row["value"]
            for row in records.values()
            if row.get("annual_series_key") == "google_lenoir_tapaha_assessed_value"
        }
        self.assertEqual(set(google), {2011, 2013, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2023, 2024, 2025})
        self.assertEqual(set(tapaha), set(google))
        self.assertEqual(google[2020], 1_173_397_868)
        self.assertEqual(tapaha[2025], 403_808_000)
        abatements = {
            row["period"]["year"]: row["value"]
            for row in records.values()
            if row.get("annual_series_key") == "google_lenoir_city_tax_abatement"
        }
        self.assertEqual(
            abatements,
            {
                2017: 3_978_500,
                2018: 4_616_262,
                2019: 5_619_341,
                2020: 8_449_681,
                2021: 8_068_908,
                2022: 7_269_371,
                2023: 6_670_769,
                2024: 6_500_013,
                2025: 5_702_519,
            },
        )
        self.assertTrue(all(row["metric_code"] == "study.incentive_payments" for row in records.values() if row.get("annual_series_key") == "google_lenoir_city_tax_abatement"))
        fy2021 = records["clm_study_google_lenoir_city_abatement_2021"]
        self.assertEqual((fy2021["pdf_page"], fy2021["printed_page"]), (79, "67"))
        self.assertEqual(records["clm_study_google_lenoir_water_reserve_fee_2024"]["value"], 6_880_000)
        deferred = records["clm_study_google_lenoir_deferred_water_contract_balance_2025"]
        self.assertEqual(deferred["value"], 6_880_000)
        self.assertEqual(deferred["metric_code"], "study.infrastructure_company_payments")
        self.assertIn("must not be added", deferred["notes"].lower())
        city_taxpayer = records["clm_study_google_lenoir_city_principal_taxpayer_assessed_2024"]
        self.assertEqual(city_taxpayer["value"], 1_758_599_206)
        self.assertEqual(city_taxpayer["period"]["kind"], "source_year")
        self.assertIn("not substituted for or added", city_taxpayer["notes"].lower())
        self.assertEqual(records["clm_study_google_lenoir_permitted_generators_2025"]["value"], 163)
        self.assertEqual(records["clm_study_google_lenoir_water_withdrawal_2024"]["value"], 351_700_000)
        workforce = records["clm_study_google_lenoir_operating_employees_2008"]
        self.assertEqual(workforce["value"], 50)
        self.assertEqual(workforce["value_qualifier"], "approximately")
        self.assertEqual(workforce["period"]["kind"], "source_year")
        self.assertNotIn("annual_series_key", workforce)
        parcel_rows = [
            row
            for row in records.values()
            if row["claim_id"].startswith("clm_study_tapaha_parcel_")
            and row["claim_id"].endswith("_assessed_2027")
        ]
        self.assertEqual(len(parcel_rows), 9)
        self.assertTrue(all(row["period"] == {"kind": "tax_year", "year": 2027, "label": "Tax year 2027"} for row in parcel_rows))
        self.assertEqual(sum(row["value"] for row in parcel_rows), 533_883_600)
        self.assertTrue(all("not google business-personal property" in row["notes"].lower() for row in parcel_rows))
        connect = records["clm_study_google_lenoir_cccti_connect_grant_2020"]
        self.assertEqual(connect["value"], 100_000)
        self.assertIn("must not be added", connect["notes"].lower())

    def test_exact_assessed_aggregations_and_projection_payroll(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        models = {row["estimate_id"]: row for row in self.synthesis_fragment["estimates"]}
        expected = {
            2011: 154_896_592,
            2013: 283_716_383,
            2015: 754_989_369,
            2016: 859_287_910,
            2017: 890_916_390,
            2018: 867_028_558,
            2019: 1_041_015_522,
            2020: 1_529_005_368,
            2021: 1_463_354_889,
            2023: 1_251_076_686,
            2024: 1_221_114_836,
            2025: 1_081_203_603,
        }
        assessed = {
            row["period"]["year"]: row
            for row in models.values()
            if row["metric_code"] == "study.modeled_combined_assessed_value"
            and row["period"]["kind"] == "fiscal_year"
        }
        self.assertEqual({year: row["value"] for year, row in assessed.items()}, expected)
        for year, model in assessed.items():
            claim_values = [records[claim_id]["value"] for claim_id in model["derivation"]["input_claim_ids"]]
            self.assertEqual(sum(claim_values), expected[year])
            self.assertEqual(model["value"], model["interval"]["central"])
            self.assertIn("not a tax", model["notes"].lower())
        payroll = models["est_study_google_lenoir_projected_payroll_2007"]
        self.assertEqual(payroll["value"], 210 * 48_300)
        self.assertIn("not observed payroll", payroll["interval"]["interpretation"].lower())
        self.assertIn(
            "clm_study_google_lenoir_operating_employees_2008",
            payroll["derivation"]["input_claim_ids"],
        )
        self.assertIn("not realized", " ".join(payroll["limitations"]).lower())
        parcel_model = models["est_study_tapaha_lenoir_real_property_assessed_2027"]
        self.assertEqual(parcel_model["value"], 533_883_600)
        self.assertEqual(parcel_model["period"]["kind"], "tax_year")
        self.assertEqual(
            sum(records[claim_id]["value"] for claim_id in parcel_model["derivation"]["input_claim_ids"]),
            parcel_model["value"],
        )
        self.assertIn("not a tax", parcel_model["interval"]["interpretation"].lower())
        cumulative = models[
            "est_study_google_lenoir_cumulative_city_abatement_2018_2025"
        ]
        self.assertEqual(cumulative["value"], 52_896_864)
        self.assertEqual(cumulative["period"]["kind"], "cumulative")
        self.assertEqual(
            sum(
                records[claim_id]["value"]
                for claim_id in cumulative["derivation"]["input_claim_ids"]
            ),
            cumulative["value"],
        )
        self.assertNotIn(
            "clm_study_google_lenoir_city_abatement_2017",
            cumulative["derivation"]["input_claim_ids"],
        )
        self.assertEqual(
            cumulative["aggregation"]["overlap_policy"],
            "do_not_sum_outside_declared_total",
        )
        self.assertIn("do not add", " ".join(cumulative["limitations"]).lower())

    def test_source_reported_water_is_direct_and_not_duplicated_as_modeled(self):
        water = sorted(
            (row for row in self.fragment["records"] if row["metric_code"] == "study.annual_water_consumption"),
            key=lambda row: row["period"]["year"],
        )
        self.assertEqual([(row["period"]["year"], row["value"]) for row in water], [(2022, 320_500_000), (2023, 336_800_000), (2024, 327_800_000)])
        self.assertTrue(all(row["value_qualifier"] == "approximately" for row in water))
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in water))
        self.assertTrue(all("not withdrawal or discharge" in row["notes"].lower() for row in water))
        self.assertFalse(any(row["metric_code"] == "study.modeled_annual_water_consumption" for row in self.synthesis_fragment["estimates"]))

    def _matched(self, metric, k=5, base=2007):
        treated = self.panels["37027"]
        treated_years = {row["year"]: row for row in treated["years"]}
        pre = list(range(2001, base + 1))
        candidates = []
        for county in self.panels.values():
            if county["county_fips"] in self.study_counties or county["county_fips"] == "37027":
                continue
            years = {row["year"]: row for row in county["years"]}
            if not all(year in years and years[year].get(metric) and years[year].get("population") for year in range(2001, 2025)):
                continue
            ratio = years[base]["population"] / treated_years[base]["population"]
            if not 0.35 <= ratio <= 2.5:
                continue
            treated_path = [math.log(treated_years[year][metric] / treated_years[2001][metric]) for year in pre]
            donor_path = [math.log(years[year][metric] / years[2001][metric]) for year in pre]
            rmse = math.sqrt(statistics.mean((left - right) ** 2 for left, right in zip(treated_path, donor_path)))
            candidates.append((rmse, county))
        candidates.sort(key=lambda item: (item[0], item[1]["county_fips"]))
        selected = [county for _, county in candidates[:k]]

        def gap(donors):
            treated_change = math.log(treated_years[2024][metric] / treated_years[base][metric])
            donor_change = statistics.mean(
                math.log(
                    {row["year"]: row for row in county["years"]}[2024][metric]
                    / {row["year"]: row for row in county["years"]}[base][metric]
                )
                for county in donors
            )
            return 100 * (math.exp(treated_change - donor_change) - 1)

        leave_one_out = [gap([row for row in selected if row != omitted]) for omitted in selected]
        nc = [county for _, county in candidates if county["county_fips"].startswith("37")][:5]
        sensitivity = [gap([county for _, county in candidates[:3]]), gap([county for _, county in candidates[:10]]), gap(nc), *leave_one_out]
        return [row["county_fips"] for row in selected], gap(selected), min(sensitivity), max(sensitivity), gap(nc)

    def test_county_comparisons_reproduce_and_gdp_is_rejected(self):
        models = {row["metric_code"]: row for row in self.synthesis_fragment["estimates"]}
        cases = {
            "annual_avg_covered_employment": (
                "study.modeled_county_employment_comparison_gap",
                ["01017", "45067", "37165", "26059", "39119"],
                3.0603180297358534,
                -2.5236087500496773,
                13.211765751397131,
            ),
            "annual_avg_weekly_wage_nominal_usd": (
                "study.modeled_county_wage_comparison_gap",
                ["36053", "26059", "47099", "28081", "23013"],
                3.7300979826653924,
                0.6408050745801308,
                9.600412546339765,
            ),
        }
        for panel_metric, (metric_code, donors, central, low, high) in cases.items():
            actual_donors, actual, actual_low, actual_high, _ = self._matched(panel_metric)
            anchor_2006 = self._matched(panel_metric, base=2006)[1]
            anchor_2008 = self._matched(panel_metric, base=2008)[1]
            actual_low = min(actual_low, anchor_2006, anchor_2008)
            actual_high = max(actual_high, anchor_2006, anchor_2008)
            self.assertEqual(actual_donors, donors)
            self.assertAlmostEqual(actual, central, places=12)
            self.assertAlmostEqual(actual_low, low, places=12)
            self.assertAlmostEqual(actual_high, high, places=12)
            model = models[metric_code]
            self.assertAlmostEqual(model["value"], actual, places=12)
            self.assertAlmostEqual(model["interval"]["low"], actual_low, places=12)
            self.assertAlmostEqual(model["interval"]["high"], actual_high, places=12)
            self.assertIn("descriptive", json.dumps(model).lower())
            self.assertIn("not a causal effect", json.dumps(model).lower())
            parameters = {row["name"]: row["value"] for row in model["parameters"]}
            self.assertAlmostEqual(parameters["treatment_anchor_2006_gap_percent"], anchor_2006, places=12)
            self.assertAlmostEqual(parameters["treatment_anchor_2008_gap_percent"], anchor_2008, places=12)
        _, gdp, _, _, gdp_nc = self._matched("real_gdp_usd")
        self.assertAlmostEqual(gdp, -21.579899825908132, places=12)
        self.assertAlmostEqual(gdp_nc, 4.7195124775265995, places=12)
        self.assertNotIn("study.modeled_county_gdp_comparison_gap", models)

    def test_proposal_payload_and_model_governance(self):
        update = next(row for row in self.fragment["project_updates"] if row["title"] == "Structured proposals for noncatalog public metrics")
        proposal = json.loads(update["notes"])
        self.assertEqual(proposal["proposal_status"], "catalog_and_claim_proposal_only")
        self.assertEqual(len(proposal["catalog_payloads"]), 7)
        self.assertEqual(proposal["air_emissions_tpy"]["2023"]["nox"], 20.51)
        self.assertEqual(proposal["air_emissions_tpy"]["2019"]["total_hap"], 0.0108)
        jdig_update = next(
            row
            for row in self.fragment["project_updates"]
            if row["title"] == "Proposed withdrawn JDIG performance condition"
        )
        jdig = json.loads(jdig_update["notes"])
        self.assertEqual(jdig["claim_payload"]["value"], 200)
        self.assertEqual(jdig["claim_payload"]["period"]["horizon_years"], 4)
        self.assertIn("withdrawn", jdig["outcome"].lower())
        direct_claims = {row["claim_id"] for row in self.fragment["records"]}
        source_ids = {row["source_id"] for row in self.evidence["sources"]} | {
            row["source_id"] for row in self.synthesis["sources"]
        }
        for model in self.synthesis_fragment["estimates"]:
            self.assertEqual(model["value"], model["interval"]["central"])
            self.assertTrue(set(model["derivation"]["input_claim_ids"]) <= direct_claims)
            self.assertTrue(set(model["derivation"]["input_source_ids"]) <= source_ids)
            self.assertEqual(model["presentation"], "modeled_not_observed_or_audited")
            self.assertEqual(model["aggregation"]["role"], "standalone")
            self.assertEqual(model["aggregation"]["overlap_policy"], "do_not_sum_outside_declared_total")


if __name__ == "__main__":
    unittest.main()
