import json
import unittest
from pathlib import Path

from scripts.build_private_sector_study import CONFIG, MODELING_POLICY, PUBLIC, build_products, read
from scripts.study_economic_evidence import load_evidence, validate_evidence
from scripts.study_modeled_synthesis import load_synthesis


PROJECT_ID = "prj_study_im3_point_09190480200"
FRAGMENT = Path(__file__).resolve().parents[1] / "config/v1/study-economic-evidence.projects" / f"{PROJECT_ID}.json"


class StreamHoustonContributionAccountTest(unittest.TestCase):
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

    def test_fragment_is_project_scoped_and_boundary_safe(self):
        self.assertEqual(self.fragment["project_id"], PROJECT_ID)
        for key in ("records", "project_updates"):
            self.assertTrue(all(row["project_id"] == PROJECT_ID for row in self.fragment[key]))
        boundary = self.fragment["scope_note"]
        self.assertIn("4001 Technology Forest", boundary)
        self.assertIn("4000 Technology Forest", boundary)
        self.assertIn("tenant", boundary.lower())
        records_text = json.dumps(self.fragment["records"])
        self.assertNotIn("TABS2022003527", records_text)
        self.assertNotIn("T-Systems", records_text)

    def test_direct_actuals_are_exact_and_nonduplicative(self):
        validate_evidence(self.evidence, self.config["candidates"])
        added = {row["claim_id"]: row for row in self.fragment["records"]}
        self.assertEqual(len(added), 3)
        self.assertTrue(all(row["basis"] == "reported_actual" for row in added.values()))
        self.assertEqual(
            (added["clm_study_stream_houston_operating_floor_area_2013"]["value"],
             added["clm_study_stream_houston_commissioned_capacity_2013"]["value"],
             added["clm_study_stream_houston_operating_capacity_2026"]["value"]),
            (74_901, 3.375, 7.8),
        )
        self.assertIn("must not be summed", added["clm_study_stream_houston_commissioned_capacity_2013"]["notes"])
        self.assertIn("not a meter", added["clm_study_stream_houston_operating_capacity_2026"]["notes"])

    def test_description_and_completed_account_state(self):
        descriptions = [row["project_description"] for row in self.fragment["project_updates"] if "project_description" in row]
        self.assertEqual(len(descriptions), 1)
        self.assertGreaterEqual(len(descriptions[0]), 80)
        self.assertLessEqual(len(descriptions[0]), 1000)
        self.assertEqual(len([part for part in descriptions[0].split(". ") if part]), 3)
        self.assertIn("commissioning complete on June 11, 2013", descriptions[0])
        self.assertIn("4000 Technology Forest", descriptions[0])
        self.assertEqual(self.project["economic_record_count"], 49)
        self.assertEqual((self.project["reported_actual_count"], self.project["projection_count"]), (49, 0))
        self.assertEqual(self.project["modeled_synthesis_count"], 0)
        self.assertEqual(
            self.project["model_completeness"]["missing_categories"],
            ["community", "construction", "investment", "public_costs", "suppliers"],
        )

    def test_all_categories_and_model_candidates_are_auditable(self):
        updates = self.fragment["project_updates"]
        self.assertEqual(len(updates), 12)
        self.assertEqual(
            {row["title"].split(" audit", 1)[0] for row in updates[:8]},
            {"Investment", "Construction", "Supplier", "Operations", "Fiscal", "Public-cost", "Resource", "Community"},
        )
        self.assertTrue(all(row["as_of"] == "2026-09-07" for row in updates))
        self.assertTrue(all("Source families checked:" in row["notes"] for row in updates[:8]))
        decisions = updates[-1]["notes"]
        for candidate in (
            "Investment", "Construction", "Suppliers", "Operations", "Fiscal", "Public costs", "Resources",
            "Community", "County employment", "County wages", "County GDP",
        ):
            self.assertIn(f"{candidate}: rejected", decisions)
        self.assertIn("Modeled additions: zero", decisions)
        self.assertIn("forecasts added: zero", decisions)

    def test_search_matrix_uses_exact_identifiers_and_alternate_repositories(self):
        source_ids = {row["source_id"] for row in self.fragment["sources"]}
        self.assertTrue(
            {
                "src_study_montgomery_clerk_stream_search_2026",
                "src_study_sec_ip_stream_houston_reit_2016",
                "src_study_tdlr_stream_houston_search_2026",
                "src_study_texas_data_center_registry_stream_search_2026",
                "src_study_texas_local_agreement_stream_search_2026",
                "src_study_montgomery_budget_acfr_stream_search_2026",
                "src_study_tceq_stream_houston_search_2026",
                "src_study_osha_stream_houston_search_2026",
                "src_study_stream_support_foundation_irs_2018",
                "src_study_bls_montgomery_qcew_access_2026",
                "src_study_bea_montgomery_gdp_access_2026",
            }.issubset(source_ids)
        )
        trail = json.dumps(self.fragment["sources"] + self.fragment["project_updates"])
        for identifier in (
            "IP Stream Houston", "IAHA1", "4001 Technology Forest", "4001 Research Forest",
            "9714-07-00103", "0097140700103", "P454338", "TABS2022003527",
        ):
            self.assertIn(identifier, trail)


if __name__ == "__main__":
    unittest.main()
