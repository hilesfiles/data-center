import json
import unittest
from collections import Counter
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


PROJECT_ID = "prj_study_im3_building_00116005354"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FRAGMENT = ROOT / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"
MODEL_FRAGMENT = ROOT / "config/v1/study-modeled-synthesis.projects" / f"{PROJECT_ID}.json"


class AppleMaidenContributionAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fragment = json.loads(EVIDENCE_FRAGMENT.read_text(encoding="utf-8"))
        cls.model_fragment = json.loads(MODEL_FRAGMENT.read_text(encoding="utf-8"))
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

    def test_fragments_are_project_scoped_and_boundary_safe(self):
        self.assertEqual(self.fragment["project_id"], PROJECT_ID)
        self.assertEqual(self.model_fragment["project_id"], PROJECT_ID)
        for key in ("records", "project_updates"):
            self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment[key]))
        self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.model_fragment["estimates"]))
        boundary = self.fragment["scope_note"]
        for marker in ("564,402", "5977 Startown", "MDN.06", "237,600", "unallocated"):
            self.assertIn(marker, boundary)
        self.assertTrue(all(row["scope"]["inventory_allocation"] == "unallocated" for row in self.fragment["records"]))

    def test_direct_records_validate_and_extend_the_baseline(self):
        validate_evidence(self.evidence, self.config["candidates"])
        self.assertEqual(len(self.fragment["records"]), 30)
        self.assertEqual(Counter(row["basis"] for row in self.fragment["records"]), {"reported_actual": 26, "source_projection": 4})
        self.assertEqual(self.project["economic_record_count"], 38)
        self.assertEqual((self.project["reported_actual_count"], self.project["projection_count"]), (34, 4))
        self.assertEqual(self.project["modeled_synthesis_count"], 0)
        self.assertEqual(self.project["model_completeness"]["missing_categories"], ["community", "suppliers"])

    def test_electricity_and_incentive_series_are_exact(self):
        records = self.fragment["records"]
        electricity = sorted(
            (row for row in records if row.get("annual_series_key") == "apple_maiden_annual_electricity"),
            key=lambda row: row["period"]["year"],
        )
        incentives = sorted(
            (row for row in records if row.get("annual_series_key") == "apple_catawba_incentive_payments"),
            key=lambda row: row["period"]["year"],
        )
        self.assertEqual([row["period"]["year"] for row in electricity], list(range(2016, 2026)))
        self.assertEqual(
            [row["value"] for row in electricity],
            [244_000_000, 273_000_000, 303_000_000, 321_000_000, 358_000_000,
             392_000_000, 432_000_000, 453_000_000, 466_000_000, 470_000_000],
        )
        self.assertEqual([row["period"]["year"] for row in incentives], [2015, 2019, 2020, 2021, 2022, 2023])
        self.assertEqual(
            [row["value"] for row in incentives],
            [4_200_284, 4_758_818, 4_834_822, 4_970_048, 5_083_551, 5_440_851],
        )
        self.assertTrue(all(row.get("value_qualifier") == "exact" for row in electricity + incentives))

    def test_phase_and_measure_boundaries_are_explicit(self):
        added = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(added["clm_study_apple_maiden_floor_area_2012"]["value"], 500_000)
        self.assertEqual(added["clm_study_apple_mdn06_floor_area_2022"]["value"], 237_600)
        self.assertIn("must not be added", added["clm_study_apple_mdn06_floor_area_2022"]["notes"])
        self.assertEqual(added["clm_study_apple_mdn06_permit_value_2022"]["value"], 25_176_096)
        self.assertIn("not verified expenditure", added["clm_study_apple_mdn06_permit_value_2022"]["notes"])
        self.assertEqual(added["clm_study_apple_catawba_cumulative_investment_2025"]["value_qualifier"], "greater_than")
        self.assertIn("do not sum", added["clm_study_apple_catawba_cumulative_investment_2025"]["notes"])

    def test_pdf_sources_have_auditable_page_locators(self):
        sources = {row["source_id"]: row for row in self.fragment["sources"]}
        for record in self.fragment["records"]:
            is_pdf = sources[record["source_id"]]["review_method"] in ("web_pdf_text", "pdf_text_and_page_image")
            self.assertEqual(is_pdf, "pdf_page" in record and "printed_page" in record)

    def test_description_and_two_pass_search_matrix(self):
        descriptions = [row["project_description"] for row in self.fragment["project_updates"] if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual(len([part for part in descriptions[0].split(". ") if part]), 3)
        for marker in ("5977 Startown Road", "564,402-square-foot", "MDN.06", "2025"):
            self.assertIn(marker, descriptions[0])

        updates = self.fragment["project_updates"]
        self.assertEqual(len(updates), 11)
        self.assertEqual(
            {row["title"].split(" audit", 1)[0] for row in updates[:8]},
            {"Investment", "Construction", "Supplier", "Operations", "Fiscal", "Public-cost", "Resource", "Community"},
        )
        self.assertTrue(all(row["as_of"] == "2026-09-07" for row in updates))
        self.assertTrue(all("Source families checked:" in row["notes"] for row in updates[:8]))

    def test_search_uses_exact_identifiers_and_alternate_sources(self):
        source_ids = {row["source_id"] for row in self.fragment["sources"]}
        self.assertTrue(
            {
                "src_study_catawba_apple_incentive_minutes_2009",
                "src_study_catawba_apple_cafr_2012",
                "src_study_catawba_tax_apple_2026",
                "src_study_catawba_mdn06_occupancy_2022",
                "src_study_catawba_apple_permit_index_2026",
                "src_study_nc_one_fund_apple_2010",
                "src_study_ncdeq_apple_air_2025",
                "src_study_ncdeq_apple_rcra_order_2017",
                "src_study_a4ws_apple_maiden_2023",
                "src_study_apple_jobs_maiden_2026",
            }.issubset(source_ids)
        )
        trail = json.dumps(self.fragment["sources"] + self.fragment["project_updates"])
        for identifier in (
            "Project Dolphin", "5977", "6028", "6029", "2201 Elbow", "362711760090",
            "BLDC-05-2022-171970", "MDN.06", "NCR000149526", "10040R07",
        ):
            self.assertIn(identifier, trail)

    def test_last_resort_modeling_gate_rejects_every_candidate(self):
        self.assertEqual(self.model_fragment["sources"], [])
        self.assertEqual(self.model_fragment["estimates"], [])
        decisions = self.fragment["project_updates"][-1]["notes"]
        for candidate in (
            "Investment", "Construction", "Suppliers", "Operations", "Fiscal", "Public costs", "Resources",
            "Community", "County employment", "County wages", "County GDP",
        ):
            self.assertIn(f"{candidate}: rejected", decisions)
        self.assertIn("Modeled additions: zero", decisions)
        forecast_count = sum(
            record["basis"] == "source_projection"
            for record in self.fragment["records"]
        )
        self.assertEqual(forecast_count, 4)
        self.assertIn("forecasts added: four", decisions)


if __name__ == "__main__":
    unittest.main()
