import copy
import unittest

from scripts.build_private_sector_study import CONFIG, PUBLIC, ROOT, build_products, read
from scripts.validate_data_contract import ContractValidator
from scripts.study_economic_evidence import EVIDENCE, economic_products, validate_evidence
from scripts.study_modeled_synthesis import MODELING_POLICY, SYNTHESIS, modeled_products

GENERAL_SYNTHESIS_FIXTURE = ROOT / "tests/fixtures/study-modeled-synthesis-general-cases.json"


class PrivateSectorStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.inventory = {r["entity_id"]: r for r in read(PUBLIC / "facilities/index.json")}
        cls.panels = {r["county_fips"]: r for p in (PUBLIC / "panels/county-economic-history/by-state").glob("*.json") for r in read(p)}
        cls.validator = ContractValidator(ROOT / "schemas/v1")

    def build(self, config=None):
        return build_products(config or self.config, self.inventory, self.panels, "2026-09-03T00:00:00+00:00")

    def test_rejected_first_entry_remains_a_candidate(self):
        _, details, entities = self.build()
        altoona = next(r for r in details if r["name"] == "Meta Altoona")
        self.assertIn("cannot be the county's first entry", altoona["legacy_first_entry_note"])
        self.assertEqual(altoona["membership_status"], "research_candidate")
        self.assertEqual(altoona["analysis_readiness"]["causal"], "not_assessed")
        self.assertEqual(next(e for e in entities if e["project_id"] == altoona["project_id"])["current_status"], "unknown")

    def test_campus_with_unknown_commissioning_is_preserved(self):
        _, details, _ = self.build()
        campus = next(r for r in details if r["name"] == "Google Lenoir")
        self.assertEqual(campus["inventory_entity_type"], "campus")
        self.assertIsNone(campus["history"]["anchor"])
        self.assertEqual(campus["history_status"], "needs_research")

    def test_operating_by_is_not_an_opening_date(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["name"] == "Meta Fort Worth")
        self.assertEqual(project["history"]["description"], "Operating by 2017-12-11")
        self.assertNotIn("operational_date", project)

    def test_duplicate_target_is_rejected(self):
        config = copy.deepcopy(self.config)
        duplicate = copy.deepcopy(config["candidates"][0])
        duplicate["project_id"] += "_duplicate"
        config["candidates"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.build(config)

    def test_wrong_host_county_is_rejected(self):
        config = copy.deepcopy(self.config)
        next(r for r in config["candidates"] if r["study_label"] == "Quicken Loans Technology Center, Corktown")["county_fips"] = "00000"
        with self.assertRaisesRegex(ValueError, "County does not match|Economic evidence host county mismatch"):
            self.build(config)

    def test_missing_evidence_link_is_rejected(self):
        config = copy.deepcopy(self.config)
        config["candidates"][0]["evidence_sources"][0]["url"] = ""
        with self.assertRaisesRegex(ValueError, "evidence URL"):
            self.build(config)

    def test_unsupported_financial_readiness_fails_schema(self):
        _, details, _ = self.build()
        detail = details[0]
        detail["analysis_readiness"]["fiscal"] = "ready"
        detail["evidence_gaps"][0]["status"] = "observed"
        issues = self.validator.validate_record(detail, ROOT / "schemas/v1/public-study-project.schema.json")
        self.assertTrue(any("fiscal" in i.path for i in issues))
        self.assertTrue(any("evidence_gaps" in i.path for i in issues))

    def test_economic_coverage_keeps_all_candidates_and_readiness(self):
        index, details, _ = self.build()
        self.assertEqual(index["counts"]["projects"], 36)
        self.assertEqual(index["counts"]["projects_with_economic_evidence"], 36)
        self.assertEqual(index["counts"]["economic_records"], 584)
        self.assertEqual(index["counts"]["reported_actual_records"], 532)
        self.assertEqual(index["counts"]["projection_records"], 52)
        self.assertEqual(index["counts"]["modeled_synthesis_records"], 13)
        self.assertTrue(all(r["analysis_readiness"]["causal"] == "not_assessed" for r in details))
        washoe = next(r for r in details if r["name"] == "Apple Washoe County campus")
        coverage = {g["code"]: g["status"] for g in washoe["evidence_gaps"]}
        self.assertEqual(coverage["operations"], "partial")
        self.assertEqual(coverage["investment"], "projections_only")
        self.assertEqual(coverage["resources"], "not_yet_collected")

    def test_source_years_do_not_fill_gaps_or_become_cash_receipts(self):
        _, details, _ = self.build()
        apple = next(r for r in details if r["name"] == "Apple Maiden")
        rows = apple["economic_records"]
        self.assertEqual([r["period"]["year"] for r in rows], [2013, 2014, 2015, 2016, 2022, 2023, 2024, 2025])
        self.assertTrue(all(r["measure_type"] == "stock" and r["aggregation"] == "none" for r in rows))
        self.assertTrue(all(r["scope"]["level"] == "company_county" for r in rows))
        self.assertEqual(rows[-1]["value"], 1476648949)

    def test_chaska_preserves_municipal_payer_and_payable_year_values(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00052227492")
        rebates = [r for r in project["economic_records"] if r["metric_code"] == "study.incentive_payments"]
        values = [r for r in project["economic_records"] if r["metric_code"] == "study.estimated_actual_property_value"]
        self.assertEqual([r["value"] for r in rebates], [20589, 23943, 26248, 35132, 39257, 49305])
        self.assertTrue(all(r["period"]["kind"] == "fiscal_year" and "City of Chaska payments" in r["scope"]["label"] for r in rebates))
        self.assertEqual([r["value"] for r in values], [17978400, 18976500, 19775100])
        self.assertTrue(all(r["period"]["kind"] == "tax_year" and r["measure_type"] == "stock" for r in values))
        self.assertNotEqual(rebates[0]["scope"], values[0]["scope"])
        self.assertFalse(any(r["metric_code"] == "study.property_tax_receipts" for r in project["economic_records"]))

    def test_expedient_adaptive_reuse_keeps_assessments_permits_and_job_plan_separate(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00664938835")
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        permits = [r for r in project["economic_records"] if r["metric_code"] == "study.permitted_construction_value"]
        jobs = [r for r in project["economic_records"] if r["metric_code"] == "study.operating_jobs_projection"]
        self.assertEqual(project["economic_record_count"], 7)
        self.assertEqual([r["period"]["year"] for r in assessed], [2024, 2025, 2026])
        self.assertEqual([r["value"] for r in assessed], [3856900, 3856900, 3856900])
        self.assertTrue(all(r["measure_type"] == "stock" and r["annual_series_key"] == "expedient_franklin_real_assessed_value" for r in assessed))
        self.assertEqual([r["value"] for r in permits], [27000, 580190, 250132])
        self.assertTrue(all(r["basis"] == "reported_actual" and r["measure_type"] == "flow" for r in permits))
        self.assertEqual([(r["value"], r["basis"]) for r in jobs], [(12, "source_projection")])
        self.assertFalse(any(r["metric_code"] in {"study.property_taxes_billed", "study.property_taxes_paid", "study.property_tax_receipts"} for r in project["economic_records"]))

    def test_quicken_keeps_whole_parcel_values_unallocated(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00903236619")
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        taxable = [r for r in project["economic_records"] if r["metric_code"] == "study.taxable_property_value"]
        self.assertEqual(project["economic_record_count"], 4)
        self.assertEqual([r["value"] for r in assessed], [3298400, 3643800])
        self.assertEqual([r["value"] for r in taxable], [2679332, 2813298])
        self.assertTrue(all("Whole mixed-use real-property parcel" in r["scope"]["label"] for r in project["economic_records"]))
        self.assertTrue(all(r["scope"]["inventory_allocation"] == "unallocated" for r in project["economic_records"]))
        self.assertFalse(any(r["metric_code"] in {"study.property_taxes_billed", "study.property_taxes_paid", "study.property_tax_receipts"} for r in project["economic_records"]))
        self.assertEqual(len(project["research_updates"]), 3)
        self.assertIn("zero-water cooling claim remains unmetered", project["research_updates"][2]["title"])

    def test_switch_las_vegas_keeps_parcel_and_campus_capex_scopes_separate(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00172739953")
        taxable = [r for r in project["economic_records"] if r["metric_code"] == "study.taxable_property_value"]
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        capex = [r for r in project["economic_records"] if r["metric_code"] == "study.campus_capital_expenditure"]
        self.assertEqual(project["economic_record_count"], 10)
        self.assertEqual([r["value"] for r in taxable], [87755603, 88942140])
        self.assertEqual([r["value"] for r in assessed], [30714461, 31129749])
        self.assertTrue(all(r["period"]["kind"] == "fiscal_year" for r in taxable + assessed))
        self.assertEqual([r["value"] for r in capex],
                         [200500000, 134200000, 23400000, 22400000, 50900000, 49500000])
        self.assertEqual([r["period"]["kind"] for r in capex],
                         ["calendar_year", "calendar_year"] + ["reported_snapshot"] * 4)
        self.assertTrue(all("no allocation to NAP7" in r["scope"]["label"] for r in capex))
        self.assertFalse(any(r["source_id"] == "src_study_nevada_switch_combined_audit_2021"
                             for r in project["economic_records"]))
        self.assertEqual(len(project["research_updates"]), 2)
        self.assertIn("combine multiple Switch", project["research_updates"][0]["title"])
        self.assertIn("resolves the mapped NAP7", project["research_updates"][1]["title"])

    def test_tierpoint_cl4_preserves_owner_parcel_bills_and_payments(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00838817907")
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        billed = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_billed"]
        paid = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_paid"]
        self.assertEqual(project["economic_record_count"], 42)
        self.assertEqual([len(assessed), len(billed), len(paid)], [14, 14, 14])
        self.assertEqual([r["period"]["year"] for r in assessed], list(range(2013, 2027)))
        self.assertEqual([r["value"] for r in paid], [r["value"] for r in billed])
        self.assertEqual((assessed[0]["value"], assessed[-1]["value"]), (1735800, 12003100))
        self.assertEqual((paid[0]["value"], paid[-1]["value"]), (22294.61, 94308.35))
        self.assertTrue(all("building owner" in r["notes"] or "does not establish TierPoint as the payer" in r["notes"]
                            for r in assessed + paid))
        self.assertTrue(all(r["scope"] == assessed[0]["scope"] for r in assessed + billed + paid))
        self.assertIn("building-level fiscal history", project["research_updates"][0]["title"])
        self.assertIn("building predates", project["research_updates"][0]["notes"])

    def test_tierpoint_little_rock_preserves_assessment_gaps_and_unpaid_charge(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00388148510")
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        taxable = [r for r in project["economic_records"] if r["metric_code"] == "study.taxable_property_value"]
        appraised = [r for r in project["economic_records"] if r["metric_code"] == "study.appraised_property_value"]
        billed = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_billed"]
        paid = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_paid"]
        self.assertEqual(project["economic_record_count"], 24)
        self.assertEqual([len(assessed), len(taxable), len(appraised), len(billed), len(paid)], [11, 11, 1, 1, 0])
        self.assertEqual([r["period"]["year"] for r in assessed],
                         [2011, 2012, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026])
        self.assertEqual((assessed[0]["value"], assessed[-1]["value"]), (492480, 1396547))
        self.assertEqual((taxable[2]["value"], taxable[-1]["value"]), (484390, 1396547))
        self.assertEqual(appraised[0]["value"], 6982735)
        self.assertEqual((billed[0]["period"]["year"], billed[0]["value"]), (2025, 82440.85))
        self.assertIn("outstanding account charge", billed[0]["notes"])
        self.assertIn("computer center", project["research_updates"][0]["notes"])

    def test_stream_houston_keeps_real_and_personal_property_accounts_separate(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_point_09190480200")
        appraised = [r for r in project["economic_records"] if r["metric_code"] == "study.appraised_property_value"]
        paid = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_paid"]
        real_values = [r for r in appraised if "Real-property parcel" in r["scope"]["label"]]
        personal_values = [r for r in appraised if "business-personal-property" in r["scope"]["label"]]
        real_paid = [r for r in paid if "Real-property parcel" in r["scope"]["label"]]
        personal_paid = [r for r in paid if "business-personal-property" in r["scope"]["label"]]
        self.assertEqual(project["economic_record_count"], 46)
        self.assertEqual([len(real_values), len(personal_values), len(real_paid), len(personal_paid)], [12, 11, 12, 11])
        self.assertEqual([r["period"]["year"] for r in real_values], list(range(2014, 2026)))
        self.assertEqual([r["period"]["year"] for r in personal_values], list(range(2015, 2026)))
        self.assertEqual((real_values[0]["value"], real_values[-1]["value"]), (8500000, 15200000))
        self.assertEqual((real_paid[0]["value"], real_paid[-1]["value"]), (216520.50, 290684.50))
        self.assertEqual((personal_values[0]["value"], personal_values[-1]["value"]), (400000, 550000))
        self.assertEqual((personal_paid[0]["value"], personal_paid[-1]["value"]), (9942.40, 9357.15))
        self.assertNotEqual(real_values[0]["scope"], personal_values[0]["scope"])
        self.assertTrue(all(r["basis"] == "reported_actual" for r in appraised + paid))
        self.assertFalse(any(r["period"]["year"] in {2012, 2013, 2026, 2027} for r in appraised + paid))
        self.assertIn("older legal description", project["research_updates"][0]["notes"])

    def test_edgeconnex_det01_preserves_ift_transition_and_forecasts(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00377585075")
        actual = [r for r in project["economic_records"] if r["basis"] == "reported_actual"]
        plans = [r for r in project["economic_records"] if r["basis"] == "source_projection"]
        taxable = [r for r in actual if r["metric_code"] == "study.taxable_property_value"]
        billed = [r for r in actual if r["metric_code"] == "study.property_taxes_billed"]
        paid = [r for r in actual if r["metric_code"] == "study.property_taxes_paid"]
        self.assertEqual(project["economic_record_count"], 48)
        self.assertEqual([len(actual), len(plans), len(taxable), len(billed), len(paid)], [44, 4, 6, 19, 19])
        self.assertEqual([r["value"] for r in taxable if "real-property" in r["scope"]["label"]],
                         [1910905, 1965650, 2004700])
        self.assertEqual([r["value"] for r in taxable if "commercial-personal" in r["scope"]["label"]],
                         [2107780, 1690840, 1856400])
        self.assertEqual([r["value"] for r in paid], [r["value"] for r in billed])
        self.assertEqual(len({r["scope"]["label"] for r in billed}), 3)
        self.assertEqual({(r["metric_code"], r["value"]) for r in plans}, {
            ("study.campus_investment_projection", 16251600),
            ("study.equipment_investment_projection", 18935500),
            ("study.operating_jobs_projection", 27),
            ("study.average_annual_salary_projection", 67000),
        })
        self.assertTrue(all(r["basis"] == "source_projection" for r in plans))
        self.assertIn("post-expiration", project["research_updates"][0]["notes"])

    def test_switch_citadel_preserves_account_history_and_adds_scoped_audit_results(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_point_06685432442")
        by_metric = {
            code: [r for r in project["economic_records"] if r["metric_code"] == code]
            for code in ["study.reported_asset_cost", "study.taxable_property_value",
                         "study.account_assessed_value", "study.property_taxes_billed",
                         "study.property_taxes_paid", "study.campus_investment_projection",
                         "study.operating_employees", "study.existing_hourly_wage",
                         "study.audited_capital_expenditure", "study.operating_jobs_projection",
                         "study.average_hourly_wage_projection", "study.sales_tax_abatement_projection",
                         "study.personal_property_tax_abatement_projection",
                         "study.direct_community_contribution",
                         "study.public_safety_equipment_cost_projection"]
        }
        self.assertEqual((project["economic_record_count"], project["reported_actual_count"],
                          project["projection_count"]), (78, 71, 7))
        self.assertEqual([len(by_metric[c]) for c in ["study.reported_asset_cost", "study.taxable_property_value",
                                                       "study.account_assessed_value", "study.property_taxes_billed"]],
                         [11, 14, 14, 14])
        self.assertEqual(len(by_metric["study.property_taxes_paid"]), 13)
        zero_bill = next(r for r in by_metric["study.property_taxes_billed"] if r["period"]["year"] == 2019)
        self.assertEqual(zero_bill["value"], 0)
        self.assertFalse(any(r["period"].get("year") == 2019 for r in by_metric["study.property_taxes_paid"]))
        personal_paid = [r for r in by_metric["study.property_taxes_paid"] if "CM001611" in r["scope"]["label"]]
        positive_personal_bills = [r["value"] for r in by_metric["study.property_taxes_billed"]
                                   if "CM001611" in r["scope"]["label"] and r["value"] > 0]
        self.assertEqual([r["value"] for r in personal_paid], positive_personal_bills)
        real_taxable = [r for r in by_metric["study.taxable_property_value"] if "005-012-23" in r["scope"]["label"]]
        real_assessed = [r for r in by_metric["study.account_assessed_value"] if "005-012-23" in r["scope"]["label"]]
        real_billed = [r for r in by_metric["study.property_taxes_billed"] if "005-012-23" in r["scope"]["label"]]
        real_paid = [r for r in by_metric["study.property_taxes_paid"] if "005-012-23" in r["scope"]["label"]]
        self.assertEqual([r["value"] for r in real_taxable], [197360800, 195608630, 196624007])
        self.assertEqual([r["value"] for r in real_assessed], [69076280, 68463021, 68818403])
        self.assertEqual([r["value"] for r in real_billed], [2239229.35, 2369299.77, 2381598.47])
        self.assertEqual([r["value"] for r in real_paid], [2239229.35, 2369299.77, 595399.61])
        self.assertEqual(real_paid[-1]["period"]["kind"], "reported_snapshot")
        self.assertNotIn("annual_series_key", real_paid[-1])
        plan = by_metric["study.campus_investment_projection"][0]
        self.assertEqual((plan["value"], plan["value_qualifier"], plan["basis"]),
                         (1000000000, "approximately", "source_projection"))
        audit = {
            "jobs": by_metric["study.operating_employees"][0],
            "wage": by_metric["study.existing_hourly_wage"][0],
            "capex": by_metric["study.audited_capital_expenditure"][0],
        }
        self.assertEqual([audit[k]["value"] for k in ["jobs", "wage", "capex"]],
                         [111, 50.97, 179943184])
        self.assertTrue(all(r["basis"] == "reported_actual" for r in audit.values()))
        self.assertTrue(all(r["scope"]["level"] == "company_county" for r in audit.values()))
        self.assertTrue(all(r["scope"]["inventory_allocation"] == "unallocated" for r in audit.values()))
        self.assertEqual(by_metric["study.operating_jobs_projection"][0]["value"], 50)
        self.assertEqual(by_metric["study.average_hourly_wage_projection"][0]["value"], 28.98)
        self.assertEqual(by_metric["study.sales_tax_abatement_projection"][0]["value"], 75720025)
        self.assertEqual(by_metric["study.personal_property_tax_abatement_projection"][0]["value"], 32095728)
        self.assertEqual(len(by_metric["study.campus_investment_projection"]), 2)
        self.assertEqual(by_metric["study.campus_investment_projection"][1]["value"], 1386677024)
        donations = by_metric["study.direct_community_contribution"]
        self.assertEqual([(r["value"], r["value_qualifier"]) for r in donations],
                         [(356000, "exact"), (2000000, "greater_than")])
        self.assertEqual(by_metric["study.public_safety_equipment_cost_projection"][0]["value"], 100000)
        self.assertEqual(by_metric["study.public_safety_equipment_cost_projection"][0]["basis"], "source_projection")
        coverage = {gap["code"]: gap["status"] for gap in project["evidence_gaps"]}
        self.assertEqual((coverage["community"], coverage["public_costs"]), ("partial", "projections_only"))
        self.assertEqual(len(project["research_updates"]), 7)
        self.assertFalse(any(r["source_id"] == "src_study_nevada_switch_combined_audit_2021"
                             for r in project["economic_records"]))
        self.assertTrue(all(r["source_id"] == "src_study_nevada_goed_switch_abatement_audit_2023"
                            for r in list(audit.values()) + [by_metric["study.operating_jobs_projection"][0]]))

    def test_council_bluffs_keeps_taxpayer_accounts_and_award_plans_separate(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_01073720208")
        actual = [r for r in project["economic_records"] if r["basis"] == "reported_actual"]
        plans = [r for r in project["economic_records"] if r["basis"] == "source_projection"]
        self.assertEqual([r["value"] for r in actual], [96600000, 61300000, 23900000])
        self.assertTrue(all(r["period"]["kind"] == "reported_snapshot" and r["value_qualifier"] == "approximately" for r in actual))
        self.assertEqual(len({r["scope"]["label"] for r in actual}), 3)
        self.assertFalse(any("annual_series_key" in r for r in actual))
        self.assertEqual({(r["metric_code"], r["value"]) for r in plans}, {
            ("study.campus_investment_projection", 600000000),
            ("study.operating_jobs_projection", 31),
        })
        self.assertTrue(all(r["scope"]["level"] == "multi_campus_county" for r in plans))

    def test_nyse_mahwah_keeps_assessments_and_tax_charges_distinct(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00472761713")
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        billed = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_billed"]
        self.assertEqual([(r["period"]["year"], r["value"]) for r in assessed], [
            (2022, 102000000), (2023, 102000000), (2024, 102000000), (2025, 102000000)])
        self.assertEqual([(r["period"]["year"], r["value"]) for r in billed], [
            (2022, 2011440), (2023, 2077740), (2024, 2105280)])
        self.assertTrue(all(r["period"]["kind"] == "tax_year" and r["scope"] == assessed[0]["scope"] for r in assessed + billed))
        self.assertFalse(any(r["period"]["year"] == 2025 for r in billed))
        self.assertTrue(all(s["review_method"] == "structured_data" for s in project["economic_sources"] if "MOD-IV" in s["title"]))
        self.assertIn("Township record links NYSE", project["research_updates"][0]["title"])

    def test_state_farm_olathe_separates_value_bills_payments_and_capex(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00598261190")
        appraised = [r for r in project["economic_records"] if r["metric_code"] == "study.appraised_property_value"]
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        billed = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_billed"]
        paid = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_paid"]
        capex = next(r for r in project["economic_records"] if r["metric_code"] == "study.estimated_cumulative_capex")
        self.assertEqual([r["value"] for r in appraised], [64326400, 63441740, 80414910, 91415000, 79979860])
        self.assertEqual([r["value"] for r in assessed], [16081601, 15860436, 20103728, 22853751, 19994965])
        self.assertEqual([r["value"] for r in billed], [1908562.84, 1945571.17, 2010360.94, 1908311.80, 2352477.94, 2661273.60, 2298781.14])
        self.assertEqual([r["value"] for r in paid], [r["value"] for r in billed])
        self.assertTrue(all("zero balance" in r["notes"] for r in paid))
        self.assertEqual((capex["value"], capex["value_qualifier"], capex["period"]["kind"]), (169778850, "approximately", "cumulative"))
        self.assertEqual(project["economic_record_count"], 25)
        self.assertIn("HMC ownership", project["research_updates"][0]["title"])

    def test_apple_mesa_keeps_real_and_personal_property_accounts_separate(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00300974499")
        fcv = [r for r in project["economic_records"] if r["metric_code"] == "study.full_cash_property_value"]
        assessed = [r for r in project["economic_records"] if r["metric_code"] == "study.account_assessed_value"]
        billed = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_billed"]
        paid = [r for r in project["economic_records"] if r["metric_code"] == "study.property_taxes_paid"]
        actual = [r for r in project["economic_records"] if r["basis"] == "reported_actual"]
        plans = [r for r in project["economic_records"] if r["basis"] == "source_projection"]
        electricity = [r for r in actual if r["metric_code"] == "study.annual_electricity_use"]
        permits = [r for r in actual if r["metric_code"] == "study.permitted_construction_value"]
        solar = [r for r in actual if r["metric_code"] == "study.renewable_generation_capacity"]
        self.assertEqual((project["economic_record_count"], len(actual), len(plans)), (80, 76, 4))
        self.assertEqual(len({r["scope"]["label"] for r in fcv}), 2)
        self.assertEqual([r["value"] for r in fcv if "business personal" in r["scope"]["label"]],
                         [287444961, 235963681, 165788022, 300733702])
        self.assertEqual([r["value"] for r in assessed if "real-property" in r["scope"]["label"]],
                         [9169182, 9627641, 10109024, 10614475])
        self.assertEqual(len(billed), 20)
        self.assertEqual([r["value"] for r in paid], [r["value"] for r in billed])
        self.assertEqual(len({r["scope"]["label"] for r in billed}), 2)
        self.assertTrue(all("zero total due" in r["period"]["label"] for r in paid))
        self.assertEqual([r["value"] for r in electricity],
                         [45000000, 104000000, 163000000, 227000000, 332000000,
                          379000000, 488000000, 530000000, 563000000])
        self.assertTrue(all(r["unit"] == "kWh_per_year" and r["period"]["kind"] == "fiscal_year" for r in electricity))
        self.assertEqual([r["value"] for r in permits],
                         [22000000, 32991875.28, 28000000, 1000000, 2000000, 3000000, 2000000, 4918751.6])
        self.assertEqual([r["value"] for r in solar], [50, 4.67])
        self.assertEqual({(r["metric_code"], r["value"], r["value_qualifier"]) for r in plans}, {
            ("study.campus_investment_projection", 2000000000, "exact"),
            ("study.operating_jobs_projection", 150, "exact"),
            ("study.construction_workers_projection", 500, "up_to"),
            ("study.state_tax_credit_projection", 25000000, "exact"),
        })
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.cumulative_facility_investment")["value_qualifier"], "approximately")
        self.assertTrue(any("separate Apple equipment" in u["title"] for u in project["research_updates"]))
        modeled = project["modeled_syntheses"]
        self.assertEqual(project["modeled_synthesis_count"], 13)
        self.assertEqual({r["basis"] for r in modeled}, {"modeled_synthesis"})
        self.assertEqual(len(project["economic_records"]), 80)
        water = next(r for r in modeled if r["metric_code"] == "study.modeled_onsite_water_use")
        self.assertEqual(water["interval"], {
            "kind": "sensitivity_envelope", "low": 69915278.64, "central": 109322072.06, "high": 148728865.48,
            "interpretation": "Low applies state-of-the-art WUE/PUE; high applies a 2.0 L/kWh WUE and 2.0 PUE reference; central is the endpoint midpoint.",
        })
        payroll = next(r for r in modeled if r["metric_code"] == "study.modeled_ftz_area_payroll")
        self.assertEqual((payroll["interval"]["low"], payroll["value"], payroll["interval"]["high"]),
                         (9579040.27, 11902668.85, 14226297.43))
        property_rows = [r for r in modeled if r["metric_code"] == "study.modeled_ftz_property_tax_reduction"]
        self.assertEqual([r["value"] for r in property_rows], [5358646.75, 4429801.10, 4121427.02])
        apple_employment = next(r for r in modeled if r["metric_code"] == "study.modeled_apple_allocated_employment")
        self.assertEqual((apple_employment["interval"]["low"], apple_employment["value"], apple_employment["interval"]["high"]),
                         (98.05, 121.84, 145.62))
        apple_payroll = next(r for r in modeled if r["metric_code"] == "study.modeled_apple_allocated_payroll")
        self.assertEqual((apple_payroll["interval"]["low"], apple_payroll["value"], apple_payroll["interval"]["high"]),
                         (9299507.17, 11555328.21, 13811149.26))
        electricity_cost = next(r for r in modeled if r["metric_code"] == "study.modeled_electricity_cost")
        self.assertEqual((electricity_cost["interval"]["low"], electricity_cost["value"], electricity_cost["interval"]["high"]),
                         (44477000, 56665950, 68854900))
        emissions = next(r for r in modeled if r["metric_code"] == "study.modeled_location_based_gross_emissions")
        self.assertEqual((emissions["interval"]["kind"], emissions["value"]), ("point_estimate", 180341.25))
        cooling = next(r for r in modeled if r["metric_code"] == "study.modeled_cooling_water_savings_potential")
        self.assertEqual((cooling["interval"]["low"], cooling["value"], cooling["interval"]["high"]),
                         (0, 16398310.81, 32796621.62))
        self.assertTrue(all(r["derivation"]["formula"] and r["derivation"]["assumptions"] for r in modeled))

    def test_modeled_synthesis_rejects_invalid_ranges_and_unknown_inputs(self):
        payload = read(SYNTHESIS)
        evidence = read(EVIDENCE)
        bad_range = copy.deepcopy(payload)
        bad_range["estimates"][0]["interval"]["low"] = bad_range["estimates"][0]["value"] + 1
        with self.assertRaisesRegex(ValueError, "interval ordering"):
            modeled_products(bad_range, self.config["candidates"], evidence)
        bad_source = copy.deepcopy(payload)
        bad_source["estimates"][0]["derivation"]["input_source_ids"].append("src_missing")
        with self.assertRaisesRegex(ValueError, "Unknown modeled inputs"):
            modeled_products(bad_source, self.config["candidates"], evidence)

    def test_modeled_synthesis_schema_and_source_claim_separation(self):
        payload = read(SYNTHESIS)
        issues = self.validator.validate_record(payload, ROOT / "schemas/v1/study-modeled-synthesis.schema.json")
        self.assertEqual(issues, [])
        _, claims, _ = economic_products(read(EVIDENCE), self.config["candidates"], "2026-09-05T00:00:00+00:00")
        self.assertFalse(any(row.get("basis") == "modeled_synthesis" for row in claims))
        self.assertTrue({row["estimate_id"] for row in payload["estimates"]}.isdisjoint({row["claim_id"] for row in claims}))

    def test_study_wide_modeled_contract_general_cases(self):
        payload = read(GENERAL_SYNTHESIS_FIXTURE)
        candidates = [{"project_id": project_id} for project_id in {
            "prj_study_fixture_construction", "prj_study_fixture_engineering",
            "prj_study_fixture_fiscal", "prj_study_fixture_causal",
        }]
        evidence = {"records": [], "sources": []}
        self.assertEqual(self.validator.validate_record(payload, ROOT / "schemas/v1/study-modeled-synthesis.schema.json"), [])
        self.assertEqual(self.validator.validate_record(read(MODELING_POLICY), ROOT / "schemas/v1/study-modeling-policy.schema.json"), [])
        grouped, _ = modeled_products(payload, candidates, evidence)
        self.assertEqual(sum(len(rows) for rows in grouped.values()), 4)
        construction = grouped["prj_study_fixture_construction"][0]
        self.assertEqual((construction["unit"], construction["period"]["kind"]), ("USD", "construction_period"))
        self.assertEqual([p["name"] for p in construction["parameters"]][:2], ["direct_job_years", "payroll_per_job_year"])
        engineering = grouped["prj_study_fixture_engineering"][0]
        self.assertEqual((engineering["derivation"]["method"], engineering["scope"]["level"]), ("engineering_estimate", "facility"))
        fiscal = grouped["prj_study_fixture_fiscal"][0]
        self.assertEqual({p["name"] for p in fiscal["parameters"]}, {"gross_taxes", "tax_credits", "infrastructure_cost", "service_cost"})
        causal = grouped["prj_study_fixture_causal"][0]
        self.assertEqual((causal["derivation"]["method"], causal["interval"]["kind"]), ("event_study", "confidence_interval"))

    def test_modeled_contract_rejects_unsupported_units_methods_and_periods(self):
        payload = read(GENERAL_SYNTHESIS_FIXTURE)
        for mutate in [
            lambda row: row.__setitem__("unit", "bananas"),
            lambda row: row["derivation"].__setitem__("method", "unsupported_model"),
            lambda row: row["period"].pop("year"),
        ]:
            invalid = copy.deepcopy(payload)
            mutate(invalid["estimates"][1])
            issues = self.validator.validate_record(invalid, ROOT / "schemas/v1/study-modeled-synthesis.schema.json")
            self.assertTrue(issues)

    def test_modeled_contract_rejects_missing_causal_and_multiplier_metadata(self):
        payload = read(GENERAL_SYNTHESIS_FIXTURE)
        candidates = [{"project_id": row["project_id"]} for row in payload["estimates"]]
        evidence = {"records": [], "sources": []}
        no_causal = copy.deepcopy(payload)
        no_causal["estimates"][3].pop("causal_design")
        self.assertTrue(self.validator.validate_record(no_causal, ROOT / "schemas/v1/study-modeled-synthesis.schema.json"))
        with self.assertRaisesRegex(ValueError, "Missing causal-design"):
            modeled_products(no_causal, candidates, evidence)
        no_multiplier = copy.deepcopy(payload)
        no_multiplier["estimates"][0]["derivation"]["method"] = "input_output_multiplier"
        self.assertTrue(self.validator.validate_record(no_multiplier, ROOT / "schemas/v1/study-modeled-synthesis.schema.json"))
        with self.assertRaisesRegex(ValueError, "Incomplete multiplier provenance"):
            modeled_products(no_multiplier, candidates, evidence)

    def test_modeled_contract_rejects_overlapping_aggregation(self):
        payload = read(GENERAL_SYNTHESIS_FIXTURE)
        component = payload["estimates"][0]
        component["aggregation"] = {"aggregation_id": "fixture_overlap", "role": "component", "overlap_policy": "do_not_sum_outside_declared_total"}
        for suffix, metric in [("one", "study.modeled_construction_total_one"), ("two", "study.modeled_construction_total_two")]:
            total = copy.deepcopy(component)
            total["estimate_id"] = f"est_fixture_total_{suffix}"
            total["metric_code"] = metric
            total["contribution_channel"] = "total"
            total["aggregation"] = {"aggregation_id": "fixture_overlap", "role": "total", "component_estimate_ids": [component["estimate_id"]], "overlap_policy": "do_not_sum_outside_declared_total"}
            payload["estimates"].append(total)
        candidates = [{"project_id": row["project_id"]} for row in payload["estimates"]]
        with self.assertRaisesRegex(ValueError, "Overlapping aggregation component"):
            modeled_products(payload, candidates, {"records": [], "sources": []})

    def test_modeled_values_cannot_be_mixed_into_canonical_evidence(self):
        payload = read(GENERAL_SYNTHESIS_FIXTURE)
        evidence = read(EVIDENCE)
        mixed = copy.deepcopy(evidence)
        mixed["records"][0]["basis"] = "modeled_synthesis"
        candidates = [{"project_id": row["project_id"]} for row in payload["estimates"]]
        with self.assertRaisesRegex(ValueError, "cannot enter canonical source evidence"):
            modeled_products(payload, candidates, mixed)

    def test_digital_crossroad_separates_assessment_liability_credits_and_payment(self):
        _, details, _ = self.build()
        project = next(r for r in details if r["project_id"] == "prj_study_im3_building_00978934687")
        actual = [r for r in project["economic_records"] if r["basis"] == "reported_actual"]
        plans = [r for r in project["economic_records"] if r["basis"] == "source_projection"]
        assessed = [r for r in actual if r["metric_code"] == "study.account_assessed_value"]
        billed = [r for r in actual if r["metric_code"] == "study.property_taxes_billed"]
        paid = [r for r in actual if r["metric_code"] == "study.property_taxes_paid"]
        distributions = [r for r in actual if r["metric_code"] == "study.gross_property_tax_distribution"]
        leasehold_assessed = [r for r in assessed if "leasehold parcel" in r["scope"]["label"]]
        personal_assessed = [r for r in assessed if "personal property" in r["scope"]["label"]]
        self.assertEqual([r["value"] for r in leasehold_assessed], [13043900, 14478500, 15658100, 19987700, 20014600])
        self.assertEqual([r["value"] for r in personal_assessed], [30328680])
        self.assertEqual([r["value"] for r in billed], [641685.14, 640867.48])
        self.assertEqual([r["value"] for r in paid], [641685.14])
        self.assertEqual(len(distributions), 6)
        self.assertAlmostEqual(sum(r["value"] for r in distributions), 751127.92, places=2)
        self.assertEqual({(r["metric_code"], r["value"]) for r in actual if "credits" in r["metric_code"] or "cap_savings" in r["metric_code"]}, {
            ("study.local_property_tax_credits", 95115.62),
            ("study.property_tax_cap_savings", 15144.82),
        })
        self.assertEqual([r["value"] for r in plans if r["metric_code"] == "study.campus_investment_projection"],
                         [40000000, 200000000, 88656629])
        self.assertEqual(next(r for r in plans if r["metric_code"] == "study.operating_jobs_projection")["value"], 40)
        self.assertEqual([r["value"] for r in plans if r["metric_code"] == "study.operating_jobs_projection"], [40, 45])
        self.assertEqual([r["value"] for r in plans if r["metric_code"] == "study.state_tax_credit_contract_amount"],
                         [750000, 9045773.82])
        paid_certified = [r for r in actual if r["metric_code"] == "study.state_incentive_paid_certified_to_date"]
        edge_series = sorted(
            (r for r in paid_certified if "_edge_paid_certified_" in r["claim_id"]),
            key=lambda r: r["period"]["report_date"],
        )
        irtc_series = sorted(
            (r for r in paid_certified if "_irtc_certified_" in r["claim_id"]),
            key=lambda r: r["period"]["report_date"],
        )
        data_series = sorted(
            (r for r in paid_certified if "_data_exemption_certified_" in r["claim_id"]),
            key=lambda r: r["period"]["report_date"],
        )
        self.assertEqual([r["value"] for r in edge_series], [0, 11763, 11763, 11763, 11763])
        self.assertEqual([r["value"] for r in irtc_series], [9045773.82] * 6)
        self.assertEqual([r["value"] for r in data_series], [0, 28369398.27, 28369398.27])
        self.assertTrue(all(r["period"]["kind"] == "cumulative" for r in paid_certified))
        qualified_investment = sorted(
            (r for r in actual if r["metric_code"] == "study.actual_qualified_investment"),
            key=lambda r: r["period"]["report_date"],
        )
        self.assertEqual([r["value"] for r in qualified_investment], [0, 0, 186954143, 186954143])
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.state_incentive_adjustment")["value"], 5209)
        cbp_establishments = [r for r in actual if r["metric_code"] == "study.county_industry_establishments"]
        cbp_employment = [r for r in actual if r["metric_code"] == "study.county_industry_employment"]
        cbp_payroll = [r for r in actual if r["metric_code"] == "study.county_industry_annual_payroll"]
        self.assertEqual([r["value"] for r in cbp_establishments], [7, 13, 15, 15, 16, 11, 12, 11])
        self.assertEqual([r["value"] for r in cbp_employment], [67, 323, 378, 398, 392, 429, 131, 44])
        self.assertEqual([r["value"] for r in cbp_payroll], [7295000, 13434000, 14110000, 14548000, 14559000, 18443000, 5840000, 4047000])
        self.assertTrue(all(r["scope"]["level"] == "county_context" for r in cbp_establishments + cbp_employment + cbp_payroll))
        self.assertTrue(all("not Digital Crossroad" in r["scope"]["label"] for r in cbp_employment))
        self.assertTrue(all(r["period"]["kind"] == "source_year" for r in cbp_establishments + cbp_employment))
        self.assertTrue(all(r["period"]["kind"] == "calendar_year" for r in cbp_payroll))
        self.assertIn("high noise", cbp_employment[1]["notes"])
        self.assertIn("no change is attributed", cbp_employment[-1]["notes"])
        self.assertEqual(next(r for r in plans if r["metric_code"] == "study.expected_qualified_investment")["value"], 239530500)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.public_infrastructure_grant")["value"], 8000)
        assessment_caps = [r for r in plans if r["metric_code"] == "study.maximum_annual_eid_special_assessment"]
        self.assertEqual([r["value"] for r in assessment_caps], [3415000, 3415000])
        self.assertTrue(all(r["value_qualifier"] == "up_to" for r in assessment_caps))
        self.assertTrue(all(r["period"]["horizon_years"] == 25 for r in assessment_caps))
        self.assertEqual(next(r for r in plans if r["value"] == 88656629)["pdf_page"], 131)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.cumulative_facility_investment")["value"], 50000000)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.cumulative_facility_investment")["value_qualifier"], "greater_than")
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.real_estate_investment_cost_basis"], [211110564, 220812911])
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.real_estate_investment_fair_value"], [240300000, 249400000])
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.commissioned_critical_power_capacity")["value"], 15)
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.private_equipment_financing_balance"], [7745144, 7263439])
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.operating_property_floor_area")["value"], 115652)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.commissioned_capacity_occupied_share")["value"], 89.3)
        local_spend = next(r for r in actual if r["metric_code"] == "study.cumulative_local_contractor_spend")
        self.assertEqual(local_spend["value"], 80000000)
        self.assertEqual(local_spend["value_qualifier"], "greater_than")
        self.assertEqual(local_spend["category"], "suppliers")
        self.assertEqual(local_spend["pdf_page"], 10)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.operating_power_capacity")["value"], 20)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.permitted_emergency_generator_count")["value"], 8)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.operating_employees")["value"], 17)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.tif_development_loan_principal")["value"], 8040000)
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_revenue_loan_repayment"],
                         [160800, 225800, 258200, 264100])
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.permitted_water_withdrawal_capacity")["value"], 910.85)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.permitted_water_consumptive_capacity")["value"], 18.202)
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_bond_proceeds_drawn"], [5000000, 3040000])
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_bond_outstanding_principal"], [8040000, 7975000, 7810000])
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_bond_principal_retired"], [0, 65000, 165000])
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_bond_interest_and_fees"], [321600, 321600, 317700])
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_bond_pledged_revenue"], [260800, 522816, 522816])
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_debt_service_fund_transfer_in"], [160800, 349574, 320987])
        self.assertEqual([r["value"] for r in actual if r["metric_code"] == "study.tif_bond_remaining_principal_interest"], [12074400, 11687800, 11205100])
        self.assertEqual({g["code"]: g["status"] for g in project["evidence_gaps"]}["resources"], "partial")
        self.assertEqual((project["economic_record_count"], len(actual), len(plans)), (113, 103, 10))
        self.assertEqual(len(project["research_updates"]), 30)
        self.assertTrue(any("construction-supply-chain" in r["title"] for r in project["research_updates"]))
        debt_screen = next(r for r in project["research_updates"] if r["source_id"] == "src_study_indiana_gateway_hammond_outstanding_debt_2026")
        self.assertIn("no separate EID debt", debt_screen["title"])
        afr_gap = next(r for r in project["research_updates"] if r["source_id"] == "src_study_indiana_gateway_hammond_2025_afr_status")
        self.assertIn("blocks the debt-series extension", afr_gap["title"])

    def test_projection_cannot_enter_actual_annual_series(self):
        evidence = read(EVIDENCE)
        row = next(r for r in evidence["records"] if r["basis"] == "source_projection")
        row["annual_series_key"] = "invalid_forecast"
        with self.assertRaisesRegex(ValueError, "Annual series requires"):
            validate_evidence(evidence, self.config["candidates"])
        del row["annual_series_key"]
        row["basis"] = "reported_actual"
        with self.assertRaisesRegex(ValueError, "Projection basis"):
            validate_evidence(evidence, self.config["candidates"])

    def test_duplicate_campus_fact_cannot_be_counted_twice(self):
        evidence = read(EVIDENCE)
        duplicate = copy.deepcopy(evidence["records"][0])
        duplicate["claim_id"] += "_duplicate"
        evidence["records"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Duplicate scoped source fact"):
            validate_evidence(evidence, self.config["candidates"])

    def test_series_requires_one_scope_and_one_record_per_year(self):
        evidence = read(EVIDENCE)
        evidence["records"][1]["scope"]["label"] = "Different taxpayer account"
        with self.assertRaisesRegex(ValueError, "mixes metrics or subject scopes"):
            validate_evidence(evidence, self.config["candidates"])
        evidence = read(EVIDENCE)
        evidence["records"][1]["period"] = copy.deepcopy(evidence["records"][0]["period"])
        with self.assertRaisesRegex(ValueError, "repeats a year"):
            validate_evidence(evidence, self.config["candidates"])

    def test_evidence_rejects_unknown_source_and_wrong_county(self):
        evidence = read(EVIDENCE)
        evidence["records"][0]["source_id"] = "src_missing_source"
        with self.assertRaisesRegex(ValueError, "Unknown economic"):
            validate_evidence(evidence, self.config["candidates"])
        evidence = read(EVIDENCE)
        evidence["records"][0]["scope"]["county_fips"] = "00000"
        with self.assertRaisesRegex(ValueError, "host county mismatch"):
            validate_evidence(evidence, self.config["candidates"])

    def test_source_claims_preserve_wider_subject_and_unknown_snapshot_date(self):
        _, claims, sources = economic_products(read(EVIDENCE), self.config["candidates"], "2026-09-03T00:00:00+00:00")
        snapshot = next(c for c in claims if c["attribute_path"] == "study.existing_fte")
        self.assertEqual(snapshot["subject"]["entity_type"], "campus")
        self.assertNotIn("entity_id", snapshot["subject"])
        self.assertEqual(snapshot["claim_date"], {"precision": "unknown"})
        for record, schema in [(r, "claim") for r in claims] + [(r, "source") for r in sources]:
            self.assertEqual(self.validator.validate_record(record, ROOT / f"schemas/v1/{schema}.schema.json"), [])

    def test_qualified_claims_do_not_become_exact_quantities(self):
        _, claims, _ = economic_products(read(EVIDENCE), self.config["candidates"], "2026-09-03T00:00:00+00:00")
        peak = next(c for c in claims if c["claim_id"] == "clm_study_meta_henrico_peak")
        self.assertEqual(peak["raw_value"]["type"], "json")
        self.assertEqual(peak["raw_value"]["value"]["qualifier"], "greater_than")
        self.assertEqual(peak["raw_value"]["value"]["value"], 1500)
        self.assertNotIn("page", peak["source_excerpt_reference"])
        self.assertEqual(peak["claim_date"], {"precision": "unknown"})

    def test_peak_and_bounds_cannot_become_annual_observations(self):
        evidence = read(EVIDENCE)
        row = next(r for r in evidence["records"] if r["period"]["kind"] == "historical_peak")
        row["annual_series_key"] = "unsupported_annual_series"
        with self.assertRaisesRegex(ValueError, "Annual series requires"):
            validate_evidence(evidence, self.config["candidates"])
        evidence = read(EVIDENCE)
        evidence["records"][0]["value_qualifier"] = "at_least"
        with self.assertRaisesRegex(ValueError, "Annual series requires"):
            validate_evidence(evidence, self.config["candidates"])

    def test_web_locators_and_completion_horizons_remain_honest(self):
        evidence = read(EVIDENCE)
        plan = next(r for r in evidence["records"] if r["claim_id"] == "clm_study_meta_henrico_jobs_plan")
        self.assertNotIn("horizon_years", plan["period"])
        self.assertNotIn("pdf_page", plan)
        validate_evidence(evidence, self.config["candidates"])
        plan["pdf_page"] = 1
        with self.assertRaisesRegex(ValueError, "web pages use section locators"):
            validate_evidence(evidence, self.config["candidates"])
        evidence = read(EVIDENCE)
        peak = next(r for r in evidence["records"] if r["period"]["kind"] == "historical_peak")
        peak["period"] = {"kind": "reported_snapshot", "report_date": "2026-09-03", "label": "Incorrect current count"}
        with self.assertRaisesRegex(ValueError, "Peak workforce requires"):
            validate_evidence(evidence, self.config["candidates"])

    def test_fiscal_receipts_and_incentives_retain_years_and_scope(self):
        _, details, _ = self.build()
        forest = next(r for r in details if r["name"] == "Meta Forest City")
        taxes = [r for r in forest["economic_records"] if r["metric_code"] == "study.property_tax_receipts"]
        incentives = [r for r in forest["economic_records"] if r["metric_code"] == "study.incentive_payments"]
        self.assertEqual([r["period"]["year"] for r in taxes], [2021, 2022, 2023, 2024, 2025])
        self.assertEqual([r["value"] for r in taxes], [6573472, 6052964, 4984437, 3834753, 3901427])
        self.assertEqual([r["value"] for r in incentives], [6082555, 5588056, 4572956, 3519179, 3582303])
        self.assertTrue(all(t["scope"] == i["scope"] for t, i in zip(taxes, incentives)))
        self.assertTrue(all("inferred" in r["notes"] for r in taxes + incentives))
        self.assertTrue(all(r["aggregation"] == "none" for r in taxes + incentives))

    def test_forest_city_depth_account_keeps_actuals_forecasts_and_scopes_distinct(self):
        _, details, _ = self.build()
        forest = next(r for r in details if r["name"] == "Meta Forest City")
        actual = [r for r in forest["economic_records"] if r["basis"] == "reported_actual"]
        plans = [r for r in forest["economic_records"] if r["basis"] == "source_projection"]
        self.assertEqual((forest["economic_record_count"], len(actual), len(plans)), (23, 20, 3))
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.cumulative_property_investment")["value"], 750000000)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.operational_jobs_supported")["value"], 275)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.cumulative_community_funding")["value"], 6400000)
        self.assertEqual(next(r for r in actual if r["metric_code"] == "study.public_infrastructure_grant")["scope"]["level"], "supporting_infrastructure")
        self.assertEqual({(r["metric_code"], r["value"]) for r in plans}, {
            ("study.operating_jobs_projection", 10),
            ("study.campus_investment_projection", 450000000),
            ("study.construction_workers", 250),
        })
        coverage = {g["code"]: g["status"] for g in forest["evidence_gaps"]}
        self.assertEqual(coverage["community"], "partial")
        self.assertEqual(len(forest["research_updates"]), 3)

    def test_cumulative_spending_and_modeled_net_do_not_become_annual_actuals(self):
        evidence = read(EVIDENCE)
        cumulative = next(r for r in evidence["records"] if r["period"]["kind"] == "cumulative")
        cumulative["annual_series_key"] = "invalid_cumulative"
        with self.assertRaisesRegex(ValueError, "Annual series requires"):
            validate_evidence(evidence, self.config["candidates"])
        evidence = read(EVIDENCE)
        net = next(r for r in evidence["records"] if r["metric_code"] == "study.net_fiscal_projection")
        self.assertEqual((net["value"], net["basis"], net["period"]["horizon_years"]), (56319724, "source_projection", 15))
        net["basis"] = "reported_actual"
        with self.assertRaisesRegex(ValueError, "Projection basis"):
            validate_evidence(evidence, self.config["candidates"])

    def test_hammond_expiry_update_does_not_change_lifecycle(self):
        _, details, entities = self.build()
        hammond = next(r for r in details if r["project_id"] == "prj_study_im3_building_00978934687")
        self.assertEqual(hammond["economic_record_count"], 113)
        self.assertEqual(len(hammond["research_updates"]), 30)
        expiry = next(r for r in hammond["research_updates"] if r["source_id"] == "src_study_hammond_agreement_expiry_2026")
        self.assertEqual(expiry["as_of"], "2026-07-01")
        self.assertIn("does not establish closure", expiry["notes"])
        self.assertEqual(next(e for e in entities if e["project_id"] == hammond["project_id"])["current_status"], "unknown")
        evidence = read(EVIDENCE)
        evidence["project_updates"][0]["source_id"] = "src_unknown_update"
        with self.assertRaisesRegex(ValueError, "Unknown research-update"):
            validate_evidence(evidence, self.config["candidates"])

    def test_revised_source_cannot_duplicate_a_fiscal_point_under_a_new_series_key(self):
        evidence = read(EVIDENCE)
        revised = copy.deepcopy(next(r for r in evidence["records"] if r["metric_code"] == "study.property_tax_receipts"))
        revised["claim_id"] += "_revision"
        revised["source_id"] = next(s["source_id"] for s in evidence["sources"] if s["source_id"] != revised["source_id"] and s["review_method"] in ("pdf_text_and_page_image", "web_pdf_text"))
        revised["annual_series_key"] += "_revision"
        evidence["records"].append(revised)
        with self.assertRaisesRegex(ValueError, "repeats a year"):
            validate_evidence(evidence, self.config["candidates"])

    def test_tax_bills_keep_separate_parties_and_do_not_become_receipts(self):
        _, details, _ = self.build()
        dalles = next(p for p in details if p["name"] == "Google The Dalles")
        bills = [r for r in dalles["economic_records"] if r["metric_code"] == "study.property_taxes_billed"]
        self.assertEqual(len(bills), 6)
        self.assertEqual(len({r["scope"]["label"] for r in bills}), 2)
        self.assertEqual([r["value"] for r in bills if "155421" in r["scope"]["label"]], [3100433.28, 1980648.69, 1813378.61])
        self.assertEqual([r["value"] for r in bills if "130136" in r["scope"]["label"]], [1729539.14, 1716154.44, 3009750.40])
        self.assertTrue(all(r["period"]["kind"] == "tax_year" and r["aggregation"] == "none" for r in bills))
        self.assertFalse(any(r["metric_code"] == "study.property_tax_receipts" for r in dalles["economic_records"]))
        self.assertEqual(dalles["economic_record_count"], 13)
        self.assertEqual(len(dalles["research_updates"]), 1)

    def test_calendar_year_decline_retained_and_year_bases_cannot_mix(self):
        evidence = read(EVIDENCE)
        rows = [r for r in evidence["records"] if r.get("annual_series_key") == "google_douglas_taxable_assessed"]
        self.assertEqual([r["value"] for r in rows], [64822718, 66591671, 53736860, 125030241])
        self.assertTrue(all(r["period"]["kind"] == "calendar_year" for r in rows))
        rows[1]["period"]["kind"] = "fiscal_year"
        with self.assertRaisesRegex(ValueError, "year bases"):
            validate_evidence(evidence, self.config["candidates"])

    def test_water_commitment_and_old_job_plan_are_not_reported_actuals(self):
        evidence = read(EVIDENCE)
        water = next(r for r in evidence["records"] if r["claim_id"] == "clm_study_lenoir_google_water_contribution_plan")
        jobs = next(r for r in evidence["records"] if r["claim_id"] == "clm_study_google_clarksville_jobs_plan")
        self.assertEqual((water["value"], jobs["value"]), (6800000, 70))
        self.assertEqual(water["scope"]["level"], "supporting_infrastructure")
        for r in [water, jobs]:
            self.assertEqual(r["basis"], "source_projection")
            self.assertNotIn("horizon_years", r["period"])
        water["basis"] = "reported_actual"
        with self.assertRaisesRegex(ValueError, "Projection basis"):
            validate_evidence(evidence, self.config["candidates"])

    def test_ntt_sv1_appeal_values_and_preopening_plans_remain_distinct(self):
        _, details, _ = self.build()
        sv1 = next(p for p in details if p["project_id"] == "prj_study_im3_building_00888253616")
        self.assertEqual((sv1["economic_record_count"], sv1["reported_actual_count"], sv1["projection_count"]), (4, 2, 2))
        actual = [r for r in sv1["economic_records"] if r["basis"] == "reported_actual"]
        plans = [r for r in sv1["economic_records"] if r["basis"] == "source_projection"]
        self.assertEqual([r["value"] for r in actual], [159579996, 83066779])
        self.assertTrue(all(r["metric_code"] == "study.assessor_appeal_county_value" for r in actual))
        self.assertTrue(all(r["period"]["kind"] == "source_year" for r in actual))
        self.assertEqual({r["metric_code"]: r["value"] for r in plans}, {
            "study.operating_jobs_projection": 40,
            "study.annual_water_use_projection": 173752,
        })
        self.assertEqual(next(r for r in plans if r["metric_code"] == "study.annual_water_use_projection")["unit"], "gallons_per_year")
        self.assertIn("address-renumbering instrument", sv1["research_updates"][0]["notes"])
        evidence = read(EVIDENCE)
        water = next(r for r in evidence["records"] if r["claim_id"] == "clm_study_ntt_sv1_annual_water_plan_2018")
        water["basis"] = "reported_actual"
        with self.assertRaisesRegex(ValueError, "Projection basis"):
            validate_evidence(evidence, self.config["candidates"])


if __name__ == "__main__":
    unittest.main()
