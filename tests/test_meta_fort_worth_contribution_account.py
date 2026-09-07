import json
import math
import statistics
import unittest
from pathlib import Path

from scripts.build_private_sector_study import build_products
from scripts.study_project_fragments import load_evidence, load_synthesis
from scripts.validate_data_contract import ContractValidator


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "prj_study_im3_building_00500820007"
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class MetaFortWorthContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = json.loads(
            (ROOT / "config/v1/private-sector-study-candidates.json").read_text(encoding="utf-8")
        )
        inventory = {
            row["entity_id"]: row
            for row in json.loads(
                (ROOT / "site/public/data/v1/facilities/index.json").read_text(encoding="utf-8")
            )
        }
        panels = {}
        for path in sorted(
            (ROOT / "site/public/data/v1/panels/county-economic-history/by-state").glob("*.json")
        ):
            for row in json.loads(path.read_text(encoding="utf-8")):
                panels[row["county_fips"]] = row
        policy = json.loads(
            (ROOT / "config/v1/study-modeling-policy.json").read_text(encoding="utf-8")
        )
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
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.evidence = load_evidence()
        cls.panels = panels
        cls.study_counties = {row["county_fips"] for row in config["candidates"]}

    def test_fragment_and_merged_evidence_pass_contract_validation(self):
        self.assertEqual(len(self.fragment["sources"]), 37)
        self.assertEqual(len(self.fragment["records"]), 101)
        issues = ContractValidator(ROOT / "schemas/v1").validate_record(
            self.evidence,
            ROOT / "schemas/v1/study-economic-evidence.schema.json",
        )
        self.assertEqual(issues, [])

    def test_provisional_account_counts_and_gate(self):
        project = self.project
        self.assertEqual(
            (
                project["economic_record_count"],
                project["reported_actual_count"],
                project["projection_count"],
            ),
            (102, 97, 5),
        )
        self.assertEqual(project["modeled_synthesis_count"], 0)
        self.assertEqual(project["model_completeness"]["status"], "incomplete")
        self.assertEqual(project["model_completeness"]["missing_categories"], [])
        self.assertEqual(
            project["model_completeness"]["missing_county_outcomes"],
            [
                "study.modeled_county_employment_comparison_gap",
                "study.modeled_county_gdp_comparison_gap",
                "study.modeled_county_wage_comparison_gap",
            ],
        )
        self.assertFalse(MODEL_FRAGMENT.exists())

    def test_corrective_account_inventory_values_exemptions_and_tax_payments(self):
        records = self.fragment["records"]
        series = {}
        for row in records:
            if key := row.get("annual_series_key"):
                series.setdefault(key, []).append(row)

        expected_lengths = {
            "meta_fort_worth_winner_real_42324937_assessed": 8,
            "meta_fort_worth_winner_personal_14401610_assessed": 9,
            "meta_fort_worth_mmi_personal_14628223_assessed": 7,
            "meta_fort_worth_real_42324937_tarrant_taxes_paid": 8,
            "meta_fort_worth_real_42324937_nisd_taxes_paid": 8,
            "meta_fort_worth_personal_14401610_tarrant_taxes_paid": 9,
            "meta_fort_worth_personal_14401610_nisd_taxes_paid": 9,
            "meta_fort_worth_mmi_14628223_tarrant_taxes_paid": 7,
            "meta_fort_worth_mmi_14628223_nisd_taxes_paid": 7,
            "meta_fort_worth_qts_site_meta_personal_assessed": 5,
        }
        self.assertEqual({key: len(series[key]) for key in expected_lengths}, expected_lengths)

        by_claim = {row["claim_id"]: row for row in records}
        self.assertEqual(
            by_claim["clm_study_meta_fort_worth_real_42324937_assessed_2025"]["value"],
            695_181_590,
        )
        self.assertIn(
            "$407,289,948",
            by_claim["clm_study_meta_fort_worth_real_42324937_assessed_2025"]["notes"],
        )
        self.assertEqual(
            by_claim["clm_study_meta_fort_worth_personal_14401610_assessed_2025"]["value"],
            1_675_386_433,
        )
        self.assertIn(
            "$1,005,220,096",
            by_claim["clm_study_meta_fort_worth_personal_14401610_assessed_2025"]["notes"],
        )
        self.assertEqual(
            by_claim["clm_study_meta_fort_worth_real_42324937_tarrant_tax_paid_2024"]["value"],
            6_471_166.03,
        )
        self.assertEqual(
            by_claim["clm_study_meta_fort_worth_real_42324937_nisd_tax_paid_2024"]["value"],
            7_035_237.69,
        )
        self.assertIn(
            "City $4,348,926.69",
            by_claim["clm_study_meta_fort_worth_real_42324937_tarrant_tax_paid_2024"]["notes"],
        )
        self.assertIn(
            "not attributed to Meta",
            by_claim["clm_study_meta_fort_worth_mmi_14628223_assessed_2025"]["scope"]["label"],
        )

    def test_audit_table_was_independently_rechecked(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        for claim_id, expected in {
            "clm_study_meta_fort_worth_audited_construction_2017": 784_208_681,
            "clm_study_meta_fort_worth_local_construction_spend_2017": 74_215_330,
            "clm_study_meta_fort_worth_audited_commercial_area_2017": 466_810,
        }.items():
            self.assertEqual(records[claim_id]["value"], expected)
            self.assertEqual((records[claim_id]["pdf_page"], records[claim_id]["printed_page"]), (7, "5"))
        self.assertIn("second independent", records["clm_study_meta_fort_worth_audited_commercial_area_2017"]["notes"].lower())

    def test_nature_center_gift_is_recipient_confirmed_and_nonadditive(self):
        records = {row["claim_id"]: row for row in self.fragment["records"]}
        gift = records["clm_study_meta_fort_worth_nature_center_boardwalk_gift_2020"]
        self.assertEqual(gift["value"], 300_000)
        self.assertEqual((gift["pdf_page"], gift["printed_page"]), (6, "7"))
        self.assertIn("must not be summed", gift["notes"])
        source = next(row for row in self.fragment["sources"] if row["source_id"] == gift["source_id"])
        self.assertEqual(source["source_type"], "other")
        self.assertIn("largest gift", source["notes"])

    def test_ap_aggregate_is_traced_but_not_misclassified(self):
        source = next(
            row for row in self.fragment["sources"]
            if row["source_id"] == "src_study_fort_worth_ap_audit_winner_2025"
        )
        self.assertIn("$14,415,465.40", source["notes"])
        self.assertIn("voucher", source["notes"])
        self.assertFalse(any(row["metric_code"] == "study.incentive_payments" for row in self.fragment["records"]))
        updates = " ".join(row["notes"] for row in self.fragment["project_updates"])
        self.assertIn("CSC 46728", updates)
        self.assertIn("Akamai Access Denied", updates)

    def _matched_gap(self, event, metric, k=5):
        treated = self.panels["48439"]
        treated_years = {row["year"]: row for row in treated["years"]}
        pre = list(range(event - 8, event))
        base = event - 1
        candidates = []
        for county in self.panels.values():
            if county["county_fips"] in self.study_counties or county["county_fips"] == "48439":
                continue
            years = {row["year"]: row for row in county["years"]}
            if not all(year in years and years[year].get(metric) and years[year].get("population") for year in range(pre[0], 2025)):
                continue
            population_ratio = years[base]["population"] / treated_years[base]["population"]
            if not 0.35 <= population_ratio <= 2.5:
                continue
            treated_path = [math.log(treated_years[year][metric] / treated_years[pre[0]][metric]) for year in pre]
            donor_path = [math.log(years[year][metric] / years[pre[0]][metric]) for year in pre]
            rmse = math.sqrt(statistics.mean((left - right) ** 2 for left, right in zip(treated_path, donor_path)))
            candidates.append((rmse, county))
        selected = [county for _, county in sorted(candidates, key=lambda item: item[0])[:k]]

        def average_gap(years):
            gaps = []
            for year in years:
                treated_change = math.log(treated_years[year][metric] / treated_years[base][metric])
                donor_change = statistics.mean(
                    math.log(
                        {row["year"]: row for row in county["years"]}[year][metric]
                        / {row["year"]: row for row in county["years"]}[base][metric]
                    )
                    for county in selected
                )
                gaps.append(math.exp(treated_change - donor_change) - 1)
            return 100 * statistics.mean(gaps)

        return [county["county_fips"] for county in selected], average_gap(range(event, 2020)), average_gap([2022, 2023, 2024])

    def test_county_model_candidates_were_actually_diagnosed_and_rejected(self):
        donors, pre_pandemic, recovery = self._matched_gap(2015, "annual_avg_covered_employment")
        self.assertEqual(donors, ["36081", "40109", "37183", "25025", "25009"])
        self.assertAlmostEqual(pre_pandemic, -2.16, places=2)
        self.assertAlmostEqual(recovery, 2.94, places=2)
        donors, pre_pandemic, recovery = self._matched_gap(2015, "real_gdp_usd")
        self.assertEqual(donors, ["15003", "36119", "25027", "48201", "39049"])
        self.assertAlmostEqual(pre_pandemic, 1.98, places=2)
        self.assertAlmostEqual(recovery, 10.44, places=2)
        disposition = next(
            row["notes"] for row in self.fragment["project_updates"]
            if row["title"] == "County GDP, employment and wage model dispositions"
        )
        for term in ("2015 groundbreaking", "2017 operation", "Pandemic 2020-2021", "K=3/5/10", "remain missing"):
            self.assertIn(term, disposition)

    def test_direct_records_preserve_boundary_time_and_nonadditivity(self):
        records = {row["claim_id"]: row for row in self.project["economic_records"]}
        self.assertEqual(records["clm_study_meta_fort_worth_audited_construction_2017"]["value"], 784_208_681)
        self.assertEqual(records["clm_study_meta_fort_worth_local_construction_spend_2017"]["value"], 74_215_330)
        self.assertEqual(records["clm_study_meta_fort_worth_assessed_value_2024"]["value"], 2_289_681_525)
        self.assertEqual(records["clm_study_meta_fort_worth_electricity_2024"]["value"], 1_109_004_000)
        self.assertEqual(records["clm_study_meta_fort_worth_water_main_payment_2018"]["value"], 879_851.31)
        self.assertTrue(all(row["scope"]["county_fips"] == "48439" for row in self.fragment["records"]))
        self.assertTrue(
            all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.fragment["records"])
        )
        self.assertIn(
            "must not be summed",
            records["clm_study_meta_fort_worth_investment_2026"]["notes"],
        )

    def test_source_projections_remain_distinct_from_actuals(self):
        projections = [row for row in self.project["economic_records"] if row["basis"] == "source_projection"]
        self.assertEqual(len(projections), 5)
        self.assertTrue(all(row["period"]["kind"] == "projection_horizon" for row in projections))
        self.assertEqual(
            {row["metric_code"] for row in projections},
            {"study.operational_jobs_supported", "study.permitted_construction_value"},
        )
        self.assertEqual(
            sorted(row["value"] for row in projections if row["metric_code"] == "study.permitted_construction_value"),
            [6_000_000, 109_000_000, 300_000_000, 531_000_000],
        )

    def test_all_categories_have_direct_or_source_projected_evidence(self):
        categories = {row["category"] for row in self.project["economic_records"]}
        self.assertEqual(
            categories,
            {
                "investment",
                "construction",
                "suppliers",
                "operations",
                "fiscal",
                "public_costs",
                "resources",
                "community",
            },
        )

    def test_one_description_search_ledger_and_provisional_status(self):
        updates = self.fragment["project_updates"]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.project["project_description"], descriptions[0])
        self.assertIn("634,395-square-foot", descriptions[0])
        self.assertIn("14100 Park Vista", descriptions[0])
        self.assertEqual(len(updates), 30)
        self.assertIn("candidate_pending_adversarial_review", updates[-1]["notes"])
        search_log = " ".join(row["notes"].lower() for row in updates)
        for term in (
            "assessor",
            "permit",
            "utility",
            "water",
            "supplier",
            "court",
            "bond",
            "community",
            "gdp",
            "qcew",
            "catalog",
            "rejected",
        ):
            self.assertIn(term, search_log)


if __name__ == "__main__":
    unittest.main()
