import json
import unittest
from pathlib import Path

from scripts.study_modeled_synthesis import load_synthesis


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_study_im3_building_00472761713"
FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT}.json"


class NyseMahwahContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))

    def test_fragment_is_project_scoped_and_has_one_description(self):
        fragment = self.fragment
        self.assertEqual(fragment["project_id"], PROJECT)
        self.assertEqual((len(fragment["sources"]), len(fragment["records"]), len(fragment["project_updates"])), (23, 11, 16))
        self.assertTrue(all(row["project_id"] == PROJECT for row in fragment["records"]))
        self.assertTrue(all(row["project_id"] == PROJECT for row in fragment["project_updates"]))
        descriptions = [row["project_description"] for row in fragment["project_updates"] if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        for marker in ["398,000-square-foot", "Mahwah", "since 2010", "customers' equipment", "Building 2"]:
            self.assertIn(marker, descriptions[0])

    def test_direct_records_keep_fiscal_capacity_and_area_definitions_separate(self):
        rows = self.fragment["records"]
        by_metric = {}
        for row in rows:
            by_metric.setdefault(row["metric_code"], []).append(row)
        self.assertEqual(sorted(row["period"]["year"] for row in by_metric["study.account_assessed_value"]), [2011, 2012, 2018, 2019, 2020, 2021])
        self.assertEqual([(row["period"]["year"], row["value"]) for row in by_metric["study.property_taxes_billed"]], [(2025, 2169540)])
        self.assertEqual(sorted((row["period"]["year"], row["value"]) for row in by_metric["study.property_taxes_paid"]), [(2024, 2105280), (2025, 2169540)])
        self.assertEqual(by_metric["study.operating_property_floor_area"][0]["value"], 398000)
        self.assertEqual(by_metric["study.operating_power_capacity"][0]["value"], 28)
        self.assertIn("not critical IT load", by_metric["study.operating_power_capacity"][0]["notes"])

    def test_search_matrix_and_model_rejections_are_auditable(self):
        updates = self.fragment["project_updates"]
        titles = [row["title"] for row in updates]
        for expected in [
            "Assessor, tax-collector and payment audit",
            "Planning, permit and environmental audit separates Building 2",
            "Incentive, compliance and public-finance audit",
            "Utility and resource audit preserves meter and scope limits",
            "Workforce, payroll and training audit",
            "Supplier and procurement audit identifies roles, not payments",
            "Community and recipient-side audit",
            "Filings, archives and local-reporting gap closure",
        ]:
            self.assertIn(expected, titles)
        audit = "\n".join(row["notes"] for row in updates)
        for marker in ["account 5447", "203167-0", "NJEDA", "dockets 651", "Structure Tone", "recipient-side", "QCEW/OEWS/CBP", "2026 is partial-year", "Rutgers' MOD-IV", "cubic feet"]:
            self.assertIn(marker, audit)
        model_updates = [row for row in updates if row["title"].startswith("Model candidate rejected")]
        self.assertEqual(len(model_updates), 4)
        synthesis = load_synthesis()
        models = [row for row in synthesis["estimates"] if row["project_id"] == PROJECT]
        self.assertEqual(len(models), 7)
        self.assertTrue(all(row["presentation"] == "modeled_not_observed_or_audited" for row in models))

    def test_modeled_fiscal_allocations_reconcile_and_break_even_stays_conditional(self):
        rows = {
            row["metric_code"]: row
            for row in load_synthesis()["estimates"]
            if row["project_id"] == PROJECT
        }
        allocated = sum(
            rows[metric]["value"]
            for metric in [
                "study.modeled_real_property_school_levy_allocation",
                "study.modeled_real_property_city_levy_allocation",
                "study.modeled_real_property_county_levy_allocation",
            ]
        )
        self.assertEqual(allocated, 2169540)
        threshold = rows["study.modeled_annual_local_service_cost_break_even"]
        self.assertEqual(threshold["value"], 2169540)
        self.assertIn("No positive or negative net fiscal result", threshold["notes"])
        self.assertIn("actual same-recipient marginal costs", threshold["confidence_rationale"])

    def test_resource_and_coverage_models_preserve_non_observation_boundaries(self):
        rows = {
            row["metric_code"]: row
            for row in load_synthesis()["estimates"]
            if row["project_id"] == PROJECT
        }
        electricity = rows["study.modeled_facility_electricity_consumption"]
        self.assertEqual(electricity["interval"]["high"], 245280000)
        self.assertIn("mathematical nameplate ceiling", electricity["limitations"][1])
        self.assertNotIn("PUE", electricity["derivation"]["formula"])
        water = rows["study.modeled_annual_water_withdrawal"]
        self.assertAlmostEqual(water["value"], 41406166.82348)
        self.assertIn("parcel-scoped", water["limitations"][1])
        coverage = rows["study.modeled_minimum_continuous_coverage_fte_equivalent"]
        self.assertAlmostEqual(coverage["value"], 8760 / 2080)
        self.assertIn("not employee headcount", coverage["limitations"][0])
        self.assertIn("does not say support personnel are onsite", coverage["limitations"][1])


if __name__ == "__main__":
    unittest.main()
