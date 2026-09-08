import json
import math
import statistics
import subprocess
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products
from scripts.validate_data_contract import ContractValidator


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
        cls.panels = panels
        cls.study_counties = {row["county_fips"] for row in cls.candidates["candidates"]}
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
        self.assertEqual(len(self.fragment["records"]), 169)
        self.assertEqual(len(self.detail["economic_records"]), 170)
        self.assertEqual(self.detail["economic_record_count"], 170)
        self.assertEqual(self.detail["reported_actual_count"], 160)
        self.assertEqual(self.detail["projection_count"], 10)
        self.assertEqual(self.detail["modeled_synthesis_count"], 39)
        self.assertEqual(self.detail["county_fips"], "01071")

        projections = [
            row for row in self.detail["economic_records"]
            if row["basis"] == "source_projection"
        ]
        self.assertTrue(all(row["period"]["kind"] == "projection_horizon" for row in projections))
        self.assertEqual(
            {row["value"] for row in projections},
            {60, 100_000, 100, 350, 93_600_000, 600_000_000, 1_000, 2_000_000, 550_000, 1_500_000_000},
        )

    def test_personal_and_real_account_series_are_payment_verified(self):
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

        real_tax_claims = {
            "48579": 440_505,
            "39706": 2_497.20,
            "3787": 133.30,
            "3732": 174,
            "42409": 120,
            "3742": 15,
            "3733": 450,
            "3716": 3,
        }
        for pin, value in real_tax_claims.items():
            self.assertEqual(
                records[f"clm_study_google_bridgeport_wiessner_pin{pin}_tax_paid_2025"]["value"],
                value,
            )
        self.assertAlmostEqual(math.fsum(real_tax_claims.values()), 443_897.50, places=2)

        real_rollups = {
            2020: (90_489_800, 18_097_960, 542_938.80, 542_938.80),
            2021: (128_262_300, 25_652_460, 386_485, 386_485),
            2022: (137_794_400, 27_558_880, 415_081.30, 415_081.30),
            2023: (137_804_400, 27_560_880, 415_141.30, 415_141.30),
            2024: (137_804_400, 27_560_880, 415_141.30, 415_141.30),
        }
        for year, (appraised, assessed, billed, paid) in real_rollups.items():
            self.assertEqual(
                records[f"clm_study_google_bridgeport_wiessner_real_appraised_{year}"]["value"],
                appraised,
            )
            self.assertEqual(
                records[f"clm_study_google_bridgeport_wiessner_real_assessed_{year}"]["value"],
                assessed,
            )
            self.assertEqual(
                records[f"clm_study_google_bridgeport_wiessner_real_tax_billed_{year}"]["value"],
                billed,
            )
            paid_row = records[f"clm_study_google_bridgeport_wiessner_real_tax_paid_{year}"]
            self.assertEqual(paid_row["value"], paid)
            self.assertIn("billed", paid_row["notes"].lower())
            self.assertIn("add", paid_row["notes"].lower())

        self.assertEqual(
            records["clm_study_google_bridgeport_wiessner_real_assessed_2025"]["value"],
            29_480_020,
        )
        self.assertEqual(
            records["clm_study_google_bridgeport_wiessner_real_tax_billed_2025"]["value"],
            443_897.50,
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
            2020: 654_482.84,
            2021: 2_100_005.38,
            2022: 1_943_560.46,
            2023: 2_520_548.50,
            2024: 3_035_462.66,
            2025: 3_192_932.64,
        }
        records = {row["claim_id"]: row for row in self.detail["economic_records"]}
        for year, total in expected.items():
            row = models[f"est_study_google_bridgeport_property_tax_total_{year}"]
            inputs = [
                records[f"clm_study_google_bridgeport_{slug}_tax_paid_{year}"]["value"]
                for slug in ("google", "design", "wiessner")
            ]
            if year == 2025:
                inputs.extend(
                    row["value"] for claim_id, row in records.items()
                    if claim_id.startswith("clm_study_google_bridgeport_wiessner_pin")
                    and claim_id.endswith("_tax_paid_2025")
                )
            else:
                inputs.append(
                    records[f"clm_study_google_bridgeport_wiessner_real_tax_paid_{year}"]["value"]
                )
            self.assertAlmostEqual(math.fsum(inputs), total, places=2)
            self.assertEqual(row["value"], total)
            self.assertAlmostEqual(
                math.fsum(parameter["value"] for parameter in row["parameters"]),
                total,
                places=2,
            )
            self.assertFalse(any(
                "tax_billed" in parameter.get("provenance", {}).get("reference_id", "")
                for parameter in row["parameters"]
            ))
            self.assertEqual(row["derivation"]["method"], "allocation")
            self.assertEqual(row["interval"]["kind"], "point_estimate")

            threshold = models[f"est_study_google_bridgeport_service_cost_break_even_{year}"]
            self.assertEqual(threshold["value"], total)
            self.assertEqual(threshold["period"], row["period"])
            self.assertEqual(threshold["scope"], row["scope"])
            self.assertAlmostEqual(
                math.fsum(parameter["value"] for parameter in threshold["parameters"]),
                total,
                places=2,
            )
            self.assertEqual(threshold["aggregation"]["role"], "standalone")
            self.assertEqual(
                threshold["aggregation"]["overlap_policy"],
                "do_not_sum_outside_declared_total",
            )
            self.assertNotEqual(
                threshold["aggregation"]["aggregation_id"],
                row["aggregation"]["aggregation_id"],
            )
            self.assertIn("not actual public cost", " ".join(threshold["limitations"]).lower())
            self.assertIn("nonadditive", threshold["notes"].lower())

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

    def test_every_surviving_model_is_independently_reproduced_and_provenanced(self):
        models = {row["estimate_id"]: row for row in self.grouped[PROJECT]}
        claim_ids = {row["claim_id"] for row in self.fragment["records"]}
        source_ids = {
            row["source_id"]
            for fragment in (self.fragment, self.model_fragment)
            for row in fragment["sources"]
        }
        audited = set()

        for estimate_id, row in models.items():
            derivation = row["derivation"]
            self.assertTrue(set(derivation["input_claim_ids"]).issubset(claim_ids))
            self.assertTrue(set(derivation["input_source_ids"]).issubset(source_ids))
            for parameter in row["parameters"]:
                provenance = parameter["provenance"]
                if provenance["kind"] == "claim":
                    self.assertIn(provenance["reference_id"], claim_ids)
                elif "reference_id" in provenance:
                    self.assertIn(provenance["reference_id"], source_ids)

            if estimate_id == "est_study_google_bridgeport_annualized_direct_payroll_projection":
                params = {parameter["name"]: parameter["value"] for parameter in row["parameters"]}
                reproduced = params["projected_direct_wages_floor"] / params["projection_horizon_years"]
            elif estimate_id == "est_study_google_bridgeport_county_wage_comparison_2024":
                params = {parameter["name"]: parameter["value"] for parameter in row["parameters"]}
                reproduced = 100 * (
                    params["host_2024_value"] - params["comparison_2024_value"]
                ) / params["comparison_2024_value"]
            elif row["aggregation"]["role"] == "total" or row["metric_code"] in {
                "study.modeled_annual_project_linked_property_taxes_paid",
                "study.modeled_annual_local_service_cost_break_even",
            }:
                reproduced = math.fsum(parameter["value"] for parameter in row["parameters"])
            elif row["metric_code"] == "study.modeled_assessor_listed_emergency_generator_total_nameplate_capacity":
                params = {parameter["name"]: parameter["value"] for parameter in row["parameters"]}
                reproduced = params["generator_feature_rows"] * params["nameplate_per_feature_row"] / 1000
            elif row["metric_code"] == "study.modeled_aggregate_billable_air_emissions":
                params = {parameter["name"]: parameter["value"] for parameter in row["parameters"]}
                reproduced = round(params["annual_fee_amount"] / params["fee_rate"], 2)
            else:
                self.assertEqual(len(row["parameters"]), 1)
                reproduced = row["parameters"][0]["value"]

            self.assertAlmostEqual(row["value"], reproduced, places=2, msg=estimate_id)
            audited.add(estimate_id)

        self.assertEqual(audited, set(models))
        self.assertEqual(len(audited), 39)

    def test_water_pue_and_cfe_keep_location_scope_and_rounding(self):
        records = {row["claim_id"]: row for row in self.detail["economic_records"]}
        withdrawal = next(
            row for row in self.detail["economic_records"]
            if row["claim_id"] == "clm_study_google_bridgeport_water_withdrawal_2024"
        )
        self.assertEqual(withdrawal["value"], 201_600_000)
        self.assertEqual(withdrawal["value_qualifier"], "approximately")
        self.assertEqual(withdrawal["pdf_page"], 110)

        for year, expected in {2021: 1.13, 2022: 1.12, 2023: 1.10, 2024: 1.10}.items():
            row = records[f"clm_study_google_bridgeport_pue_{year}"]
            self.assertEqual(row["value"], expected)
            self.assertEqual(row["scope"]["inventory_allocation"], "unallocated")

        consumption = records["clm_study_google_bridgeport_water_consumption_2024"]
        discharge = records["clm_study_google_bridgeport_water_discharge_2024"]
        self.assertEqual(consumption["value"], 182_800_000)
        self.assertEqual(discharge["value"], 18_800_000)
        self.assertEqual(consumption["value_qualifier"], "approximately")
        self.assertEqual(consumption["pdf_page"], 110)
        self.assertEqual(
            {records[f"clm_study_google_bridgeport_cfe_{kind}_{year}"]["value"]
             for kind in ("site", "grid") for year in (2022, 2023)},
            {52, 53, 63, 65},
        )
        self.assertFalse(any(
            any(token in row["estimate_id"] for token in ("_pue_", "_cfe_site_", "_cfe_grid_", "_water_consumption_", "_water_discharge_"))
            for row in self.grouped[PROJECT]
        ))

    def _county_specification(self, metric, treatment, universe="national", k=20, omit=None):
        years = list(range(treatment - 8, treatment))
        treated = {row["year"]: row for row in self.panels["01071"]["years"]}
        southeast = {"01", "05", "12", "13", "21", "22", "28", "37", "45", "47", "51", "54"}

        def features(series):
            values = [series[year][metric] for year in years]
            growth = [math.log(values[index] / values[index - 1]) for index in range(1, len(values))]
            return (
                math.log(values[-1]),
                math.log(values[-1] / values[0]) / (len(values) - 1),
                statistics.pstdev(growth),
            )

        target = features(treated)
        candidates = []
        for fips, county in self.panels.items():
            if fips in self.study_counties or (universe == "southeast" and fips[:2] not in southeast):
                continue
            series = {row["year"]: row for row in county["years"]}
            if not all(
                year in series and series[year].get(metric) and series[year][metric] > 0
                for year in years + [2024]
            ):
                continue
            candidate = features(series)
            distance = (
                (candidate[0] - target[0]) ** 2
                + ((candidate[1] - target[1]) / 0.03) ** 2
                + ((candidate[2] - target[2]) / 0.03) ** 2
            )
            candidates.append((distance, fips, series))
        selected = sorted(candidates, key=lambda row: (row[0], row[1]))[:k]
        if omit:
            selected = [row for row in selected if row[1] != omit]
        weights = [1 / (math.sqrt(row[0]) + 0.05) for row in selected]

        def prediction(year):
            return sum(
                weight * row[2][year][metric] for weight, row in zip(weights, selected)
            ) / sum(weights)

        comparison = prediction(2024)
        gap = 100 * (treated[2024][metric] - comparison) / comparison
        pre_errors = [
            100 * (treated[year][metric] - prediction(year)) / prediction(year)
            for year in years
        ]
        return gap, math.sqrt(statistics.mean(error * error for error in pre_errors)), [
            row[1] for row in selected
        ]

    def test_county_sensitivity_gate_reproduces_retention_and_retirement(self):
        models = {row["estimate_id"]: row for row in self.grouped[PROJECT]}
        for retired in ("employment", "gdp"):
            self.assertNotIn(
                f"est_study_google_bridgeport_county_{retired}_comparison_2024",
                models,
            )

        diagnostics = {}
        for metric in (
            "annual_avg_covered_employment",
            "annual_avg_weekly_wage_nominal_usd",
            "real_gdp_usd",
        ):
            results = []
            for treatment in (2018, 2019):
                for universe in ("national", "southeast"):
                    for k in (3, 5, 10, 20):
                        results.append(self._county_specification(metric, treatment, universe, k)[:2])
                _, _, donors = self._county_specification(metric, treatment)
                results.extend(
                    self._county_specification(metric, treatment, omit=donor)[:2]
                    for donor in donors
                )
            diagnostics[metric] = {
                "low": min(gap for gap, _ in results),
                "high": max(gap for gap, _ in results),
                "rmse": max(rmse for _, rmse in results),
                "stable": all(gap > 0 for gap, _ in results) or all(gap < 0 for gap, _ in results),
            }

        self.assertFalse(diagnostics["annual_avg_covered_employment"]["stable"])
        self.assertFalse(diagnostics["real_gdp_usd"]["stable"])
        wage_diagnostic = diagnostics["annual_avg_weekly_wage_nominal_usd"]
        self.assertTrue(wage_diagnostic["stable"])
        self.assertLess(wage_diagnostic["rmse"], 5)

        wage = models["est_study_google_bridgeport_county_wage_comparison_2024"]
        baseline_gap, baseline_rmse, _ = self._county_specification(
            "annual_avg_weekly_wage_nominal_usd", 2018
        )
        self.assertAlmostEqual(wage["value"], baseline_gap, places=2)
        self.assertAlmostEqual(wage["parameters"][2]["value"], baseline_rmse, places=12)
        self.assertAlmostEqual(wage["interval"]["low"], wage_diagnostic["low"], places=12)
        self.assertAlmostEqual(wage["interval"]["high"], wage_diagnostic["high"], places=12)
        self.assertAlmostEqual(wage["parameters"][3]["value"], wage_diagnostic["rmse"], places=12)
        self.assertEqual(wage["derivation"]["method"], "benchmark_application")
        self.assertNotIn("causal_design", wage)
        self.assertIn("descriptive", " ".join(wage["limitations"]).lower())

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
            "gdp", "employment", "wage", "eight wiessner real parcels", "facility 705-0057",
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
            "study.direct_payroll_projection",
            "study.projected_economic_impact",
            "study.household_income_equivalents",
            "study.pue_overhead_reduction_vs_industry",
        ):
            self.assertIn(proposal, text)

    def test_adopted_environmental_records_are_complete_and_reproducible(self):
        catalog = {row["metric_code"]: row for row in self.evidence["metrics"]}
        claims = {row["claim_id"]: row for row in self.fragment["records"]}
        estimates = {row["estimate_id"]: row for row in self.model_fragment["estimates"]}
        source_ids = {row["source_id"] for row in self.fragment["sources"]}
        adopted_metric_codes = {
            "study.assessor_listed_emergency_generator_count",
            "study.assessor_listed_emergency_generator_unit_nameplate_capacity",
            "study.permitted_potential_nox_emissions",
            "study.permitted_potential_sox_emissions",
            "study.permitted_potential_carbon_monoxide_emissions",
            "study.permitted_potential_voc_emissions",
            "study.permitted_potential_pm_emissions",
            "study.permitted_potential_pm10_emissions",
            "study.permitted_potential_pm25_emissions",
            "study.permitted_potential_formaldehyde_emissions",
            "study.permitted_potential_total_hap_emissions",
            "study.permitted_potential_co2e_emissions",
            "study.permit_group_annual_runtime_ceiling",
            "study.annual_air_emissions_fee_rate",
            "study.annual_air_emissions_fee_amount",
        }
        adopted_claims = {
            key: row for key, row in claims.items() if row["metric_code"] in adopted_metric_codes
        }
        adopted_estimates = {
            key: row for key, row in estimates.items()
            if row["metric_code"] in {
                "study.modeled_assessor_listed_emergency_generator_total_nameplate_capacity",
                "study.modeled_aggregate_billable_air_emissions",
            }
        }
        self.assertEqual(len(adopted_claims), 35)
        self.assertEqual(len(adopted_estimates), 6)

        for row in adopted_claims.values():
            self.assertEqual(row["project_id"], PROJECT)
            self.assertIn(row["metric_code"], catalog)
            self.assertTrue(catalog[row["metric_code"]]["unit"])
            self.assertIn(row["source_id"], source_ids)
            self.assertEqual(row["scope"]["county_fips"], "01071")
            self.assertEqual(row["scope"]["inventory_allocation"], "unallocated")
            self.assertTrue(row["source_locator"])
            self.assertTrue(set(row).issubset({
                "claim_id", "project_id", "metric_code", "value", "value_qualifier", "basis",
                "period", "scope", "source_id", "pdf_page", "printed_page", "source_locator",
                "notes", "review_status", "reviewed_on", "annual_series_key",
            }))

        generator_count = adopted_claims["clm_proposed_google_bridgeport_assessor_generator_count_2026"]
        generator_rating = adopted_claims[
            "clm_google_bridgeport_generator_unit_kw_2026"
        ]
        self.assertEqual(generator_count["value"], 55)
        self.assertEqual(catalog[generator_count["metric_code"]]["unit"], "generators")
        self.assertEqual(generator_rating["value"], 1000)
        self.assertEqual(catalog[generator_rating["metric_code"]]["unit"], "kW_per_generator")
        self.assertIn("assessor", generator_count["notes"].lower())
        self.assertIn("not permit-listed", generator_count["notes"].lower())
        generator_total = adopted_estimates[
            "est_google_bridgeport_generator_nameplate_2026"
        ]
        generator_params = {row["name"]: row["value"] for row in generator_total["parameters"]}
        self.assertEqual(
            generator_params["generator_feature_rows"]
            * generator_params["nameplate_per_feature_row"] / 1000,
            generator_total["value"],
        )
        self.assertEqual((generator_total["value"], generator_total["unit"]), (55, "MW"))
        self.assertIn("not operating output", " ".join(generator_total["limitations"]).lower())

        potential_expected = {
            2018: {"nox": 245.92, "carbon_monoxide": 45.27, "voc": 5.08},
            2019: {"nox": 248.51, "carbon_monoxide": 47.15, "voc": 5.82},
            2020: {"nox": 249.20, "carbon_monoxide": 47.33, "voc": 5.95},
            2022: {
                "nox": 249, "sox": 0.23, "carbon_monoxide": 48.12, "voc": 5.95,
                "pm": 0.67, "pm10": 0.67, "pm25": 0.67, "formaldehyde": 0.013,
                "total_hap": 0.28, "co2e": 24_693,
            },
        }
        for year, pollutants in potential_expected.items():
            for pollutant, value in pollutants.items():
                claim_id = (
                    f"clm_google_bridgeport_pte_co_{year}"
                    if pollutant == "carbon_monoxide"
                    else f"clm_proposed_google_bridgeport_permitted_potential_{pollutant}_{year}"
                )
                row = adopted_claims[claim_id]
                self.assertEqual(row["value"], value)
                self.assertEqual(catalog[row["metric_code"]]["unit"], "tons_per_year")
                self.assertEqual(row["period"]["year"], year)
                self.assertIn("permitting maximum", row["notes"].lower())
                self.assertIn("never actual emissions", row["notes"].lower())

        runtime_expected = {"X001": 8320, "X002": 1600, "X003": 500, "X004": 160}
        for group, value in runtime_expected.items():
            row = adopted_claims[f"clm_proposed_google_bridgeport_{group.lower()}_runtime_ceiling_2023"]
            self.assertEqual(row["value"], value)
            self.assertEqual(catalog[row["metric_code"]]["unit"], "hours_per_year")
            self.assertIn(f"permit group {group}", row["scope"]["label"])
            self.assertIn("non-equivalent", row["notes"].lower())
            self.assertIn("55 assessor", row["notes"].lower())

        fee_expected = {
            2020: (77.50, 2052.21),
            2021: (95, 915.80),
            2022: (90, 1033.20),
            2023: (92, 244.72),
            2024: (98.50, 256.11),
        }
        for year, (rate, amount) in fee_expected.items():
            rate_row = adopted_claims[f"clm_proposed_google_bridgeport_air_fee_rate_{year}"]
            amount_row = adopted_claims[f"clm_proposed_google_bridgeport_air_fee_amount_{year}"]
            self.assertEqual(rate_row["value"], rate)
            self.assertEqual(catalog[rate_row["metric_code"]]["unit"], "USD_per_ton")
            self.assertEqual(amount_row["value"], amount)
            self.assertEqual(catalog[amount_row["metric_code"]]["unit"], "USD")
            estimate = adopted_estimates[f"est_proposed_google_bridgeport_aggregate_billable_air_emissions_{year}"]
            self.assertEqual(estimate["value"], round(amount / rate, 2))
            self.assertEqual(estimate["unit"], "tons_per_year")
            self.assertEqual(estimate["period"]["year"], year)
            self.assertIn(str(amount), estimate["derivation"]["formula"])
            self.assertIn("aeeers", estimate["notes"].lower())
            self.assertIn("nonadditive", " ".join(estimate["limitations"]).lower())

        adoption_updates = [
            row for row in self.fragment["project_updates"]
            if row.get("title") == "Root adoption of Bridgeport governed environmental and generator quantities"
        ]
        self.assertEqual(len(adoption_updates), 1)
        self.assertIn("adopted 17 metric definitions", adoption_updates[0]["notes"].lower())

    def test_adversarial_correction_is_schema_valid_and_repairs_provenance(self):
        validator = ContractValidator(ROOT / "schemas/v1")
        self.assertEqual(
            validator.validate_record(
                self.evidence, ROOT / "schemas/v1/study-economic-evidence.schema.json"
            ),
            [],
        )
        self.assertEqual(
            validator.validate_record(
                self.synthesis, ROOT / "schemas/v1/study-modeled-synthesis.schema.json"
            ),
            [],
        )

        models = {row["estimate_id"]: row for row in self.grouped[PROJECT]}
        self.assertNotIn("est_study_google_bridgeport_households_2021_2023", models)
        payroll = models["est_study_google_bridgeport_annualized_direct_payroll_projection"]
        self.assertEqual(payroll["value"], 4_680_000)
        self.assertEqual(payroll["period"]["horizon_years"], 20)
        self.assertIn("lower-bound", payroll["interval"]["interpretation"])
        self.assertFalse(any("gap" in row for row in models.values()))

        threshold = models["est_study_google_bridgeport_service_cost_break_even_2025"]
        params = {row["provenance"]["reference_id"]: row["value"] for row in threshold["parameters"]}
        self.assertEqual(params, {
            "clm_study_google_bridgeport_google_tax_paid_2025": 3_994.82,
            "clm_study_google_bridgeport_design_tax_paid_2025": 1_905_083.88,
            "clm_study_google_bridgeport_wiessner_tax_paid_2025": 839_956.44,
            "src_study_jackson_property_wiessner_real_98353": 443_897.50,
        })

        sources = {row["source_id"] for row in self.fragment["sources"]}
        self.assertTrue({
            "src_study_alabama_commerce_project_spike_2016",
            "src_study_naec_google_expansion_2026",
            "src_study_jackson_county_minutes_wiessner_mpa_2015",
            "src_study_jackson_property_wiessner_real_98353",
            "src_study_adem_wiessner_title_v_2023",
            "src_study_adem_wiessner_air_applications_2018_2022",
            "src_study_epa_echo_bridgeport_facilities_2026",
            "src_study_epa_echo_wiessner_dfr_2026",
            "src_study_adem_bridgeport_cwsrf_2025",
        }.issubset(sources))
        updates = " ".join(row["notes"] for row in self.fragment["project_updates"]).lower()
        self.assertIn("contract 3.1.0", updates)
        self.assertIn("e3a0b32ae0954ed38c9875674d3c1238144b6a6a", updates)
        self.assertIn("epa/echo", updates)
        self.assertIn("ferc", updates)
        self.assertIn("candidate_pending_adversarial_review", updates)
        self.assertIn("f66c3073fb679b7f3fe34012a5cb4926cac54534", updates)
        self.assertIn("corrective_handoff_ready", updates)

    def test_corrective_direct_facts_and_rejected_inferences(self):
        records = {row["claim_id"]: row for row in self.detail["economic_records"]}
        self.assertEqual(records["clm_study_google_bridgeport_poured_pad_area_2017"]["value"], 100)
        self.assertEqual(
            {
                records["clm_study_google_bridgeport_wiessner_building_a_floor_area_2026"]["value"],
                records["clm_study_google_bridgeport_wiessner_building_b_floor_area_2026"]["value"],
                records["clm_study_google_bridgeport_wiessner_office_floor_area_2026"]["value"],
            },
            {318_096, 319_600, 67_200},
        )
        text = EVIDENCE_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("55 diesel", text)
        self.assertIn("potential-to-emit", text)
        self.assertIn("aggregate billable actual tons", text)
        self.assertIn("aeeers", text)
        self.assertIn("full $7 million is not cataloged", text)
        self.assertIn("$129 million", text)
        self.assertIn("no worksheet defining", text)
        self.assertNotIn("clm_study_google_bridgeport_permitted_generators", text)

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
