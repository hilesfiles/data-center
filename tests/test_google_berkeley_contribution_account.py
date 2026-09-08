import json
import math
import statistics
import unittest

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT = "prj_study_im3_building_00610827836"


class GoogleBerkeleyContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read(CONFIG)
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.policy = read(MODELING_POLICY)
        validate_evidence(cls.evidence, cls.candidates["candidates"])
        cls.grouped, _ = modeled_products(
            cls.synthesis, cls.candidates["candidates"], cls.evidence, cls.policy
        )
        inventory = {row["entity_id"]: row for row in read(PUBLIC / "facilities/index.json")}
        cls.panels = {
            row["county_fips"]: row
            for path in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json")
            for row in read(path)
        }
        cls.study_counties = {row["county_fips"] for row in cls.candidates["candidates"]}
        _, details, _ = build_products(
            cls.candidates,
            inventory,
            cls.panels,
            "2026-09-08T00:00:00+00:00",
            cls.evidence,
            cls.synthesis,
            cls.policy,
        )
        cls.detail = next(row for row in details if row["project_id"] == PROJECT)

    def test_account_counts_identity_and_full_gate(self):
        self.assertEqual(self.detail["county_fips"], "45015")
        self.assertEqual(self.detail["economic_record_count"], 24)
        self.assertEqual(self.detail["reported_actual_count"], 20)
        self.assertEqual(self.detail["projection_count"], 4)
        self.assertEqual(self.detail["modeled_synthesis_count"], 12)
        gate = self.detail["model_completeness"]
        self.assertEqual(gate["status"], "full_modeled_account")
        self.assertEqual(gate["missing_categories"], [])
        self.assertEqual(gate["missing_county_outcomes"], [])

    def test_direct_records_preserve_scope_time_and_basis(self):
        rows = {row["claim_id"]: row for row in self.detail["economic_records"]}
        self.assertEqual(rows["clm_study_google_berkeley_permit_value_2020"]["value"], 20_749_187)
        self.assertEqual(rows["clm_study_google_berkeley_groundwater_withdrawal_2021"]["value"], 2_740_000)
        self.assertEqual(rows["clm_study_google_berkeley_groundwater_permit_capacity_2025"]["value"], 549_000_000)
        self.assertEqual(rows["clm_study_google_arum_property_taxes_paid_2024"]["value"], 89_631.30)
        self.assertEqual(rows["clm_study_google_arum_property_taxes_paid_2025"]["value"], 90_266.72)
        self.assertEqual(rows["clm_study_google_berkeley_electric_contribution_2025"]["value"], 250_000)
        self.assertEqual(rows["clm_study_google_berkeley_people_working_2018"]["value_qualifier"], "greater_than")
        self.assertNotIn("clm_study_google_berkeley_cumulative_investment_2018", rows)
        self.assertNotIn("clm_study_google_berkeley_cumulative_investment_2021", rows)
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in rows.values()))
        projections = [row for row in rows.values() if row["basis"] == "source_projection"]
        self.assertEqual(len(projections), 4)
        self.assertTrue(all(row["period"]["kind"] == "projection_horizon" for row in projections))

    def test_tax_break_even_and_water_identity_are_exactly_reproducible(self):
        models = {row["metric_code"]: row for row in self.grouped[PROJECT]}
        tax = models["study.modeled_latest_project_linked_local_tax_contribution"]
        threshold = models["study.modeled_annual_local_service_cost_break_even"]
        self.assertEqual(tax["value"], 90_266.72)
        self.assertEqual(threshold["value"], tax["value"])
        self.assertIn("partial", tax["derivation"]["assumptions"][2])
        self.assertIn("not observed cost", threshold["derivation"]["assumptions"][0].lower())

        water = sorted(
            (row["period"]["year"], row["value"])
            for row in self.detail["economic_records"]
            if row["metric_code"] == "study.annual_water_consumption"
        )
        self.assertEqual(water, [(2022, 662_100_000), (2023, 763_400_000)])
        direct = [row for row in self.detail["economic_records"] if row["metric_code"] in {
            "study.annual_water_consumption", "study.data_center_pue",
            "study.hourly_carbon_free_energy_share",
        }]
        self.assertEqual(len(direct), 6)
        self.assertTrue(all(row["scope"]["level"] == "state" for row in direct))
        self.assertTrue(all(row["scope"]["state_abbr"] == "SC" for row in direct))
        self.assertFalse(any(row["metric_code"] == "study.modeled_annual_water_consumption" for row in self.grouped[PROJECT]))

    def test_multiplier_channels_and_source_contribution_outputs_are_protected(self):
        rows = self.grouped[PROJECT]
        construction = [row for row in rows if row["metric_code"].startswith("study.modeled_construction_job_years_")]
        self.assertEqual(
            {row["contribution_channel"]: row["value"] for row in construction},
            {"direct": 128.04, "indirect": 30.71, "induced": 22.71, "total": 181.54},
        )
        total = next(row for row in construction if row["contribution_channel"] == "total")
        self.assertEqual(total["aggregation"]["role"], "total")
        self.assertEqual(len(total["aggregation"]["component_estimate_ids"]), 3)
        self.assertTrue(all(row["derivation"]["method"] == "input_output_multiplier" for row in construction))
        self.assertTrue(all("no berkeley county supplier" in row["multiplier_provenance"]["local_purchase_assumption"].lower() for row in construction))

        impacts = {
            row["metric_code"]: row
            for row in rows
            if row["derivation"]["model_version"] == "google-deloitte-south-carolina-impact-2024"
        }
        self.assertEqual(impacts["study.modeled_annual_data_center_jobs_supported_total"]["value"], 6_430)
        self.assertEqual(impacts["study.modeled_annual_data_center_labor_income_total"]["value"], 411_000_000)
        self.assertEqual(impacts["study.modeled_annual_data_center_gdp_contribution_total"]["value"], 626_000_000)
        self.assertTrue(all(row["scope"]["level"] == "state" for row in impacts.values()))
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in impacts.values()))
        jobs_model = impacts["study.modeled_annual_data_center_jobs_supported_total"]
        self.assertEqual((jobs_model["unit"], jobs_model["measure_type"]), ("jobs", "flow"))
        jobs = {parameter["name"]: parameter["value"] for parameter in jobs_model["parameters"]}
        self.assertEqual(jobs, {"direct_jobs": 985, "indirect_jobs": 3970, "induced_jobs": 1480})
        self.assertNotEqual(sum(jobs.values()), jobs_model["value"])
        self.assertFalse(any("modeled_operating" in row["metric_code"] for row in impacts.values()))

    def test_search_matrix_description_and_schema_proposals_are_complete(self):
        updates = [row for row in self.evidence["project_updates"] if row["project_id"] == PROJECT]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.detail["project_description"], descriptions[0])
        self.assertIn("multi-building", descriptions[0])
        text = " ".join(row["title"] + " " + row["notes"] for row in updates).lower()
        for term in (
            "assessor", "permit", "filot", "supplier", "payroll", "water", "electricity",
            "wastewater", "emissions", "cooling", "community", "gdp", "not a google effect",
            "cloudflare", "no complete annual grant ledger", "candidate_pending_adversarial_review",
            "adversarial_review_complete_reconciled",
        ):
            self.assertIn(term, text)
        proposal = next(row for row in updates if row["title"] == "Corrected environmental catalog, scope, claim, and regression proposal")
        payload = json.loads(proposal["notes"])
        self.assertEqual(payload["proposal_status"], "not_adopted_requires_catalog_and_scope_schema_change")
        self.assertEqual(payload["scope_schema_payload"]["add_level"], "state")
        self.assertEqual(
            [row["metric_code"] for row in payload["catalog_payloads"]],
            ["study.annual_water_consumption", "study.data_center_pue", "study.carbon_free_energy_match"],
        )
        self.assertEqual(len(payload["claim_payloads"]), 6)
        self.assertTrue(all(row["scope"]["level"] == "state" for row in payload["claim_payloads"]))
        self.assertEqual(payload["regression_expectations"]["water_values"], [662_100_000, 763_400_000])
        self.assertEqual(payload["regression_expectations"]["post_adoption_merged_record_count"], 24)

    def _matched(self, metric, k=5):
        treated = self.panels["45015"]
        ty = {row["year"]: row for row in treated["years"]}
        pre, base = list(range(2001, 2007)), 2006
        candidates = []
        for county in self.panels.values():
            if county["county_fips"] in self.study_counties or county["county_fips"] == "45015":
                continue
            years = {row["year"]: row for row in county["years"]}
            if not all(year in years and years[year].get(metric) and years[year].get("population") for year in range(2001, 2025)):
                continue
            ratio = years[base]["population"] / ty[base]["population"]
            if not 0.35 <= ratio <= 2.5:
                continue
            left = [math.log(ty[year][metric] / ty[2001][metric]) for year in pre]
            right = [math.log(years[year][metric] / years[2001][metric]) for year in pre]
            rmse = math.sqrt(statistics.mean((a - b) ** 2 for a, b in zip(left, right)))
            candidates.append((rmse, county))
        candidates.sort(key=lambda item: (item[0], item[1]["county_fips"]))
        selected = [county for _, county in candidates[:k]]

        def gap(donors):
            treated_change = math.log(ty[2024][metric] / ty[base][metric])
            donor_change = statistics.mean(
                math.log(({row["year"]: row for row in county["years"]}[2024][metric]) /
                         ({row["year"]: row for row in county["years"]}[base][metric]))
                for county in donors
            )
            return 100 * (math.exp(treated_change - donor_change) - 1)

        loo = [gap([row for row in selected if row["county_fips"] != omitted["county_fips"]]) for omitted in selected]
        same_state = [county for _, county in candidates if county["county_fips"].startswith("45")][:5]
        sensitivities = [gap([county for _, county in candidates[:3]]), gap([county for _, county in candidates[:10]]), gap(same_state), *loo]
        return [county["county_fips"] for county in selected], gap(selected), min(sensitivities), max(sensitivities)

    def test_county_comparisons_reproduce_donors_central_and_sensitivity(self):
        cases = {
            "annual_avg_covered_employment": (["08077", "17199", "17111", "13113", "45063"], "study.modeled_county_employment_comparison_gap"),
            "annual_avg_weekly_wage_nominal_usd": (["37049", "39013", "46099", "19169", "36071"], "study.modeled_county_wage_comparison_gap"),
            "real_gdp_usd": (["12083", "12055", "12109", "28033", "15001"], "study.modeled_county_gdp_comparison_gap"),
        }
        models = {row["metric_code"]: row for row in self.grouped[PROJECT]}
        for metric, (expected_donors, code) in cases.items():
            donors, central, low, high = self._matched(metric)
            model = models[code]
            self.assertEqual(donors, expected_donors)
            self.assertAlmostEqual(model["value"], central, places=12)
            self.assertAlmostEqual(model["interval"]["low"], low, places=12)
            self.assertAlmostEqual(model["interval"]["high"], high, places=12)
            self.assertIn("not a google effect", " ".join(model["limitations"]).lower())
            self.assertNotIn("causal_design", model)


if __name__ == "__main__":
    unittest.main()
