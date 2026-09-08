import json
import math
import statistics
import unittest

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis, modeled_products


PROJECT = "prj_study_im3_building_00610827836"
SOUTHEAST = {"01", "12", "13", "28", "37", "45", "47", "51"}


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
            cls.candidates, inventory, cls.panels, "2026-09-08T00:00:00+00:00",
            cls.evidence, cls.synthesis, cls.policy,
        )
        cls.detail = next(row for row in details if row["project_id"] == PROJECT)
        cls.fragment = json.loads(
            (CONFIG.parent / "study-economic-evidence.projects" / f"{PROJECT}.json")
            .read_text(encoding="utf-8")
        )
        cls.model_fragment = json.loads(
            (CONFIG.parent / "study-modeled-synthesis.projects" / f"{PROJECT}.json")
            .read_text(encoding="utf-8")
        )

    def _matched(self, metric, anchor, universe, k):
        ty = {row["year"]: row for row in self.panels["45015"]["years"]}
        pre, base = list(range(anchor - 6, anchor)), anchor - 1
        left = [math.log(ty[y][metric] / ty[pre[0]][metric]) for y in pre]
        candidates = []
        for county in self.panels.values():
            fips = county["county_fips"]
            if fips in self.study_counties or fips == "45015":
                continue
            if universe == "same_state" and not fips.startswith("45"):
                continue
            if universe == "southeast" and fips[:2] not in SOUTHEAST:
                continue
            years = {row["year"]: row for row in county["years"]}
            if not all(y in years and years[y].get(metric) and years[y].get("population") for y in range(pre[0], 2025)):
                continue
            if not 0.35 <= years[base]["population"] / ty[base]["population"] <= 2.5:
                continue
            right = [math.log(years[y][metric] / years[pre[0]][metric]) for y in pre]
            rmse = math.sqrt(statistics.mean((a - b) ** 2 for a, b in zip(left, right)))
            candidates.append((rmse, county, right))
        candidates.sort(key=lambda item: (item[0], item[1]["county_fips"]))
        selected = candidates[:k]

        def gap(donors):
            treated_change = math.log(ty[2024][metric] / ty[base][metric])
            donor_change = statistics.mean(
                math.log(
                    {row["year"]: row for row in county["years"]}[2024][metric]
                    / {row["year"]: row for row in county["years"]}[base][metric]
                ) for _, county, _ in donors
            )
            return 100 * (math.exp(treated_change - donor_change) - 1)

        group_path = [statistics.mean(item[2][i] for item in selected) for i in range(len(pre))]
        group_rmse = 100 * math.sqrt(
            statistics.mean((a - b) ** 2 for a, b in zip(left, group_path))
        )
        loo = [
            {
                "omitted_fips": omitted[1]["county_fips"],
                "gap_percent": gap([item for item in selected if item[1]["county_fips"] != omitted[1]["county_fips"]]),
            }
            for omitted in selected
        ]
        return {
            "donor_fips": [item[1]["county_fips"] for item in selected],
            "donor_match_rmse_percent": [
                {"county_fips": item[1]["county_fips"], "rmse_percent": 100 * item[0]}
                for item in selected
            ],
            "group_pretrend_rmse_percent": group_rmse,
            "central_gap_percent": gap(selected),
            "leave_one_out": loo,
        }

    def test_corrective_handoff_counts_and_incomplete_gate(self):
        self.assertEqual(len(self.fragment["sources"]), 34)
        self.assertEqual(len(self.fragment["records"]), 163)
        self.assertEqual(
            {basis: sum(row["basis"] == basis for row in self.fragment["records"])
             for basis in ("reported_actual", "source_projection")},
            {"reported_actual": 159, "source_projection": 4},
        )
        self.assertEqual(self.detail["economic_record_count"], 164)
        self.assertEqual(self.detail["reported_actual_count"], 159)
        self.assertEqual(self.detail["projection_count"], 5)
        self.assertEqual(self.detail["modeled_synthesis_count"], 27)
        self.assertNotEqual(self.detail["model_completeness"]["status"], "full_modeled_account")

    def test_new_direct_design_construction_water_and_grid_records(self):
        rows = {row["claim_id"]: row for row in self.detail["economic_records"]}
        expected = {
            "clm_study_google_berkeley_design_capacity_2020": 80,
            "clm_study_google_berkeley_permitted_floor_area_2024": 280_000,
            "clm_study_google_berkeley_permitted_floor_area_2026": 380_000,
            "clm_study_google_berkeley_operating_parcel_floor_area_2026": 1_521_302,
            "clm_study_google_berkeley_groundwater_withdrawal_2015": 0,
            "clm_study_google_berkeley_groundwater_permit_capacity_2015": 182_500_000,
            "clm_study_google_mnk_infrastructure_contribution_projection_2025": 35_200_000,
        }
        self.assertEqual({claim: rows[claim]["value"] for claim in expected}, expected)
        self.assertTrue(all(rows[claim]["scope"]["inventory_allocation"] == "unallocated" for claim in expected))
        self.assertIn("not measured load", rows["clm_study_google_berkeley_design_capacity_2020"]["notes"].lower())
        self.assertIn("not a paid contribution", rows["clm_study_google_mnk_infrastructure_contribution_projection_2025"]["notes"].lower())

    def test_gis_owner_universe_and_exact_taxable_value_arithmetic(self):
        taxable = [row for row in self.fragment["records"] if row["metric_code"] == "study.taxable_assessed_value" and row["source_id"] == "src_study_berkeley_gis_cad_api_google_2026"]
        maguro = [row for row in taxable if "maguro" in row["claim_id"]]
        arum = [row for row in taxable if "arum" in row["claim_id"]]
        self.assertEqual((len(maguro), len(arum)), (4, 11))
        self.assertEqual(sum(row["value"] for row in maguro), 8_601_401)
        self.assertEqual(sum(row["value"] for row in arum), 25_457_800)
        self.assertEqual(sum(row["value"] for row in taxable), 34_059_201)
        self.assertTrue(all("not a tax bill" in row["notes"].lower() for row in taxable))
        models = [
            row for row in self.grouped[PROJECT]
            if row["metric_code"] == "study.modeled_current_taxable_assessed_value_total"
        ]
        self.assertEqual(len(models), 3)
        by_suffix = {row["estimate_id"].split("_")[-2]: row for row in models}
        self.assertEqual(
            {key: by_suffix[key]["value"] for key in ("maguro", "arum", "combined")},
            {"maguro": 8_601_401, "arum": 25_457_800, "combined": 34_059_201},
        )
        self.assertEqual(
            {key: len(by_suffix[key]["derivation"]["input_claim_ids"]) for key in by_suffix},
            {"maguro": 4, "arum": 11, "combined": 15},
        )
        self.assertTrue(all("strictly nonadditive" in " ".join(row["limitations"]).lower() for row in models))
        self.assertIn("6,272,600", by_suffix["arum"]["derivation"]["assumptions"][-1])

    def test_property_card_series_respects_acquisition_receipts_credits_and_splits(self):
        payment_rows = [
            row for row in self.fragment["records"]
            if row["metric_code"] == "study.property_taxes_paid"
            and row["source_id"] in {
                "src_study_berkeley_assessor_mnk_property_cards_2026",
                "src_study_berkeley_assessor_arum_2110002092",
            }
        ]
        value_rows = [
            row for row in self.fragment["records"]
            if row["metric_code"] == "study.taxable_property_value"
            and row["source_id"] in {
                "src_study_berkeley_assessor_mnk_property_cards_2026",
                "src_study_berkeley_assessor_arum_2110002092",
            }
        ]
        self.assertEqual((len(payment_rows), len(value_rows)), (61, 61))
        receipts = [row["source_locator"].split("receipt ")[1].split(",")[0] for row in payment_rows]
        self.assertEqual(len(receipts), len(set(receipts)))

        def years_for(tms, rows):
            return sorted(row["period"]["year"] for row in rows if tms in row["scope"]["label"])

        for tms in ("211-00-02-071", "211-00-02-078", "211-00-02-079", "211-00-02-082"):
            self.assertEqual(years_for(tms, payment_rows), list(range(2016, 2026)))
        for tms in ("210-00-00-215", "211-00-02-080", "211-00-02-081", "211-00-02-083",
                    "211-00-02-084", "211-00-02-086", "211-00-02-089", "211-00-02-090",
                    "211-00-02-091", "211-00-02-092"):
            self.assertEqual(years_for(tms, payment_rows), [2024, 2025])
        self.assertEqual(years_for("210-00-00-170", payment_rows), [2025])
        self.assertTrue(all("partial" in row["notes"].lower() for row in payment_rows))
        self.assertTrue(all("t08" in row["source_locator"].lower() or "tax history" in row["source_locator"].lower() for row in payment_rows))
        arum_2025 = [row for row in payment_rows if "Arum" in row["scope"]["label"] and row["period"]["year"] == 2025 and "092" not in row["scope"]["label"]]
        self.assertTrue(all("sales tax credit" in row["notes"].lower() for row in arum_2025))
        v089 = next(row for row in value_rows if "211-00-02-089" in row["scope"]["label"] and row["period"]["year"] == 2025)
        self.assertEqual(v089["value"], 6_735_600)
        self.assertIn("current residual", v089["notes"].lower())

    def test_annual_real_property_partials_and_equal_cost_pairs(self):
        totals = sorted(
            (row["period"]["year"], row["value"], row)
            for row in self.grouped[PROJECT]
            if row["metric_code"] == "study.modeled_annual_project_linked_property_taxes_paid"
        )
        thresholds = sorted(
            (row["period"]["year"], row["value"], row)
            for row in self.grouped[PROJECT]
            if row["metric_code"] == "study.modeled_annual_local_service_cost_break_even"
        )
        expected = [
            (2016, 21_254), (2017, 16_814), (2018, 87_525), (2019, 93_410),
            (2020, 94_638), (2021, 91_758), (2022, 99_198), (2023, 108_934.50),
            (2024, 471_101.35), (2025, 475_883.98),
        ]
        self.assertEqual([(year, value) for year, value, _ in totals], expected)
        self.assertEqual([(year, value) for year, value, _ in thresholds], expected)
        self.assertTrue(all("real-property-only partial" in row["notes"].lower() for _, _, row in totals))
        self.assertTrue(all("not an estimate of actual public-service cost" in row["interval"]["interpretation"].lower() for _, _, row in thresholds))
        self.assertTrue(all("strictly nonadditive" in row["notes"].lower() for _, _, row in thresholds))
        by_year = {year: row for year, _, row in totals}
        self.assertEqual(len(by_year[2024]["derivation"]["input_claim_ids"]), 14)
        self.assertEqual(len(by_year[2025]["derivation"]["input_claim_ids"]), 15)
        self.assertFalse(any("2100000170" in claim for claim in by_year[2024]["derivation"]["input_claim_ids"]))
        self.assertTrue(any("2100000170" in claim for claim in by_year[2025]["derivation"]["input_claim_ids"]))

    def test_direct_sources_name_instruments_queries_and_boundaries(self):
        sources = {row["source_id"]: row for row in self.fragment["sources"]}
        expected = {
            "src_study_berkeley_gis_cad_api_google_2026", "src_study_berkeley_rod_google_notice_2020",
            "src_study_berkeley_rod_google_notice_2024", "src_study_berkeley_rod_maguro_notice_2026",
            "src_study_berkeley_rod_google_renovation_2026", "src_study_berkeley_rod_arum_stormwater_2024",
            "src_study_berkeley_rod_mnk_encroachment_2025", "src_study_scdes_trident_groundwater_2017",
            "src_study_scpsc_project_mnk_ware_corrected_2025",
            "src_study_berkeley_assessor_mnk_property_cards_2026",
        }
        self.assertTrue(expected.issubset(sources))
        text = " ".join(sources[source_id]["notes"] for source_id in expected).lower()
        for term in ("four current parcels", "eleven", "80 mw", "280,000", "380,000", "plsp-646981-2024", "together as mnk", "182.50-million", "financially responsible", "not network cost", "acquisition 2006-12-15", "acquisition 2024-10-11", "sales tax credit", "every included receipt is unique"):
            self.assertIn(term, text)

    def test_numbered_adversarial_dispositions_are_auditable(self):
        updates = [row for row in self.fragment["project_updates"] if row["project_id"] == PROJECT]
        descriptions = [row["project_description"] for row in updates if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertEqual(self.detail["project_description"], descriptions[0])
        row = next(item for item in updates if item["title"] == "Numbered adversarial correction dispositions")
        challenges = json.loads(row["notes"])["challenges"]
        self.assertEqual([item["number"] for item in challenges], list(range(1, 11)))
        required = {"number", "challenge", "repositories", "queries", "date_range", "records_opened", "alternate_routes", "disposition", "irreducible_inputs"}
        self.assertTrue(all(required.issubset(item) for item in challenges))
        text = json.dumps(challenges).lower()
        for term in ("41 maguro", "26 arum", "11 google", "zero project eagle/linden/mnk", "http 500", "all 51 linked bcws", "mallard llc", "36 central specifications", "34/36", "26/36", "3.2654%-86.8802%", "jobs 6,430", "auditor/treasurer"):
            self.assertIn(term, text)

    def test_only_sign_stable_descriptive_county_model_is_reinstated(self):
        models = self.grouped[PROJECT]
        self.assertEqual(len(models), 27)
        self.assertFalse(any(row["metric_code"] == "study.modeled_county_employment_comparison_gap" for row in models))
        self.assertFalse(any(row["metric_code"] == "study.modeled_county_wage_comparison_gap" for row in models))
        model = next(row for row in models if row["metric_code"] == "study.modeled_county_gdp_comparison_gap")
        manifest = model["reproducibility_manifest"]
        specs = manifest["specifications"]
        self.assertEqual(len(specs), 36)
        values = []
        for spec in specs:
            rerun = self._matched("real_gdp_usd", spec["anchor"], spec["universe"], spec["k"])
            self.assertEqual(rerun["donor_fips"], spec["donor_fips"])
            self.assertEqual(
                [item["county_fips"] for item in rerun["donor_match_rmse_percent"]],
                [item["county_fips"] for item in spec["donor_match_rmse_percent"]],
            )
            for actual, stored in zip(rerun["donor_match_rmse_percent"], spec["donor_match_rmse_percent"]):
                self.assertAlmostEqual(actual["rmse_percent"], stored["rmse_percent"], places=12)
            self.assertAlmostEqual(rerun["group_pretrend_rmse_percent"], spec["group_pretrend_rmse_percent"], places=12)
            self.assertAlmostEqual(rerun["central_gap_percent"], spec["central_gap_percent"], places=12)
            self.assertEqual(
                [item["omitted_fips"] for item in rerun["leave_one_out"]],
                [item["omitted_fips"] for item in spec["leave_one_out"]],
            )
            for actual, stored in zip(rerun["leave_one_out"], spec["leave_one_out"]):
                self.assertAlmostEqual(actual["gap_percent"], stored["gap_percent"], places=12)
            values.append(rerun["central_gap_percent"])
            values.extend(item["gap_percent"] for item in rerun["leave_one_out"])
        self.assertEqual(len(values), 252)
        self.assertTrue(all(value > 0 for value in values))
        central = self._matched("real_gdp_usd", 2007, "national", 5)
        self.assertEqual(central["donor_fips"], ["12083", "12055", "12109", "28033", "15001"])
        self.assertAlmostEqual(model["value"], central["central_gap_percent"], places=12)
        self.assertAlmostEqual(model["interval"]["low"], min(values), places=12)
        self.assertAlmostEqual(model["interval"]["high"], max(values), places=12)
        self.assertEqual(manifest["summary"]["central_specification_count"], 36)
        self.assertEqual(manifest["summary"]["all_leave_one_out_result_count"], 216)
        self.assertEqual(manifest["summary"]["k5_leave_one_out_result_count"], 60)
        self.assertTrue(manifest["summary"]["all_central_and_leave_one_out_positive"])
        self.assertIn("not a google effect", " ".join(model["limitations"]).lower())
        self.assertNotIn("causal_design", model)

    def test_employment_and_wage_reruns_cross_zero(self):
        for metric in ("annual_avg_covered_employment", "annual_avg_weekly_wage_nominal_usd"):
            values = []
            for anchor in (2007, 2013, 2018, 2021):
                for universe in ("national", "same_state", "southeast"):
                    for k in (3, 5, 10):
                        rerun = self._matched(metric, anchor, universe, k)
                        values.append(rerun["central_gap_percent"])
                        values.extend(item["gap_percent"] for item in rerun["leave_one_out"])
            self.assertLess(min(values), 0)
            self.assertGreater(max(values), 0)

    def test_commissioned_models_remain_source_attributed_and_nonadditive(self):
        rows = [row for row in self.grouped[PROJECT] if row["derivation"]["method"] == "contribution_analysis"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["scope"]["level"] == "state" and row["confidence"] == "low" for row in rows))
        jobs = next(row for row in rows if row["unit"] == "jobs")
        self.assertEqual(jobs["value"], 6_430)
        self.assertEqual({p["name"]: p["value"] for p in jobs["parameters"]}, {"direct_jobs": 985, "indirect_jobs": 3_970, "induced_jobs": 1_480})
        self.assertEqual(sum(p["value"] for p in jobs["parameters"]), 6_435)

    def test_final_ledger_and_handoff_are_corrective_not_accepted(self):
        updates = [row for row in self.fragment["project_updates"] if row["project_id"] == PROJECT]
        ledger = json.loads(next(row for row in updates if row["title"] == "Adversarial corrective metric disposition ledger")["notes"])["metrics"]
        self.assertEqual(len(ledger), 10)
        ledger_text = json.dumps(ledger).lower()
        for term in ("no multiplier transfer", "no portfolio tax", "no subsidy", "employment and wage remain retired"):
            self.assertIn(term, ledger_text)
        handoff = next(row for row in updates if row["title"] == "Second corrective property-card fiscal reconstruction")
        handoff_text = handoff["notes"].lower()
        for term in ("gap_closure_in_progress", "corrective_handoff_ready", "34 sources", "163 records", "modeled count: 27", "not accepted evidence or project completion"):
            self.assertIn(term, handoff_text)


if __name__ == "__main__":
    unittest.main()
