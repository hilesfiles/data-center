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
        self.assertEqual((len(self.fragment["sources"]), len(self.fragment["records"]), len(self.fragment["project_updates"])), (13, 28, 14))
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment["records"]))
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment["project_updates"]))
        self.assertEqual(
            (
                sum(row["basis"] == "reported_actual" for row in self.fragment["records"]),
                sum(row["basis"] == "source_projection" for row in self.fragment["records"]),
            ),
            (27, 1),
        )
        validate_evidence(self.evidence, self.config["candidates"])
        self.assertFalse(SYNTHESIS_FRAGMENT.exists())
        self.assertEqual(
            (
                self.project["economic_record_count"],
                self.project["reported_actual_count"],
                self.project["projection_count"],
                self.project["modeled_synthesis_count"],
            ),
            (29, 28, 1, 0),
        )
        self.assertIn("candidate_pending_adversarial_review", self.fragment["project_updates"][-1]["notes"])
        self.assertIn("provisional and never accepted", self.fragment["project_updates"][-1]["notes"])

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
        taxes = [row for row in rows if row["metric_code"] == "study.property_taxes_paid"]
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

    def test_search_audit_and_metric_model_dispositions_are_complete(self):
        updates = self.fragment["project_updates"]
        titles = [row["title"] for row in updates]
        self.assertEqual(sum(title.startswith("Direct discovery") for title in titles), 8)
        self.assertEqual(sum(title.startswith("Gap closure") for title in titles), 5)
        self.assertEqual(sum(title.startswith("Adversarial continuation") for title in titles), 1)
        audit = " ".join(row["notes"] for row in updates)
        for token in (
            "Source families checked:",
            "Queries/identifiers:",
            "account 72793",
            "account 84139",
            "22AQ-E035",
            "201805050",
            "140-10532",
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
            "Public costs",
            "Community",
            "Resources",
            "County employment",
            "County wages",
            "County GDP",
        ):
            self.assertIn(metric_family, decisions)
        for rejected_model in (
            "assessor-value-to-investment conversion",
            "tax-share allocation by floor area",
            "tax-equal public-cost break-even",
            "utility capacity/annual-use conversion",
            "construction job-years/payroll",
            "supplier multiplier",
            "county comparison gaps",
        ):
            self.assertIn(rejected_model, decisions)
        self.assertIn("modeled additions: zero", decisions)
        self.assertEqual(
            self.project["model_completeness"]["missing_categories"],
            ["construction", "operations", "public_costs", "suppliers"],
        )


if __name__ == "__main__":
    unittest.main()
