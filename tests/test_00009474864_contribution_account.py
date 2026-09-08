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
        self.assertEqual(len(self.fragment["sources"]), 32)
        self.assertEqual(len(self.fragment["records"]), 51)
        self.assertEqual(len(self.fragment["project_updates"]), 13)
        self.assertEqual(
            sum(row["basis"] == "reported_actual" for row in self.fragment["records"]), 38
        )
        self.assertEqual(
            sum(row["basis"] == "source_projection" for row in self.fragment["records"]), 13
        )
        self.assertEqual(len(self.synthesis_fragment["estimates"]), 18)
        self.assertEqual(self.project["economic_record_count"], 52)
        self.assertEqual(self.project["reported_actual_count"], 38)
        self.assertEqual(self.project["projection_count"], 14)
        self.assertEqual(self.project["modeled_synthesis_count"], 18)

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
            "no same-scope marginal",
            "sign reversal",
        ):
            self.assertIn(term, text)

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
                2018: 4_616_262,
                2019: 5_619_341,
                2020: 8_449_681,
                2022: 7_269_371,
                2023: 6_670_769,
                2024: 6_500_013,
                2025: 5_702_519,
            },
        )
        self.assertNotIn(2021, abatements)
        self.assertTrue(all(row["metric_code"] == "study.incentive_payments" for row in records.values() if row.get("annual_series_key") == "google_lenoir_city_tax_abatement"))
        self.assertEqual(records["clm_study_google_lenoir_water_reserve_fee_2024"]["value"], 6_880_000)
        self.assertEqual(records["clm_study_google_lenoir_permitted_generators_2025"]["value"], 163)
        self.assertEqual(records["clm_study_google_lenoir_water_withdrawal_2024"]["value"], 351_700_000)

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
        }
        self.assertEqual({year: row["value"] for year, row in assessed.items()}, expected)
        for year, model in assessed.items():
            claim_values = [records[claim_id]["value"] for claim_id in model["derivation"]["input_claim_ids"]]
            self.assertEqual(sum(claim_values), expected[year])
            self.assertEqual(model["value"], model["interval"]["central"])
            self.assertIn("do not", model["notes"].lower())
        payroll = models["est_study_google_lenoir_projected_payroll_2007"]
        self.assertEqual(payroll["value"], 210 * 48_300)
        self.assertIn("not observed payroll", payroll["interval"]["interpretation"].lower())

    def test_water_models_have_rounding_bands_and_no_false_additivity(self):
        water = sorted(
            (row for row in self.synthesis_fragment["estimates"] if row["metric_code"] == "study.modeled_annual_water_consumption"),
            key=lambda row: row["period"]["year"],
        )
        self.assertEqual([(row["period"]["year"], row["value"]) for row in water], [(2022, 320_500_000), (2023, 336_800_000), (2024, 327_800_000)])
        self.assertTrue(all(row["interval"]["high"] - row["interval"]["low"] == 100_000 for row in water))
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in water))
        self.assertTrue(all("not" in " ".join(row["limitations"]).lower() for row in water))

    def _matched(self, metric, k=5):
        treated = self.panels["37027"]
        treated_years = {row["year"]: row for row in treated["years"]}
        pre = list(range(2001, 2008))
        base = 2007
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
                6.203854349987781,
            ),
        }
        for panel_metric, (metric_code, donors, central, low, high) in cases.items():
            actual_donors, actual, actual_low, actual_high, _ = self._matched(panel_metric)
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
