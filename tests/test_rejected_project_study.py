import unittest

from scripts.build_rejected_project_study import CONFIG, ROOT, build_products, read
from scripts.validate_data_contract import ContractValidator


class RejectedProjectStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.validator = ContractValidator(ROOT / "schemas" / "v1")

    def test_build_preserves_distinct_proposals_and_sites(self):
        index, details, projects, sites = build_products(self.config, "2026-09-09T00:00:00+00:00")
        self.assertEqual(index["counts"]["projects"], 8)
        self.assertEqual(len(details), len(projects))
        self.assertEqual(len(details), len(sites))
        self.assertEqual(len({row["project_id"] for row in details}), 8)
        self.assertEqual(len({row["site_id"] for row in details}), 8)
        self.assertTrue(all(project["target_refs"][0]["entity_type"] == "proposed_site" for project in projects))

    def test_recent_cases_are_not_claimed_comparison_ready(self):
        index, _, _, _ = build_products(self.config, "2026-09-09T00:00:00+00:00")
        self.assertEqual(index["counts"]["by_readiness"].get("comparison_ready", 0), 0)

    def test_enrichment_has_depth_and_primary_records(self):
        index, details, _, _ = build_products(self.config, "2026-09-09T00:00:00+00:00")
        self.assertGreaterEqual(index["counts"]["sources"], 70)
        self.assertGreaterEqual(index["counts"]["primary_sources"], 30)
        self.assertGreaterEqual(index["counts"]["timeline_events"], 50)
        for detail in details:
            self.assertGreaterEqual(detail["source_count"], 7, detail["project_id"])
            self.assertGreaterEqual(detail["timeline_event_count"], 6, detail["project_id"])
            self.assertGreaterEqual(detail["primary_source_count"], 2, detail["project_id"])
            self.assertGreaterEqual(len(detail["unresolved_questions"]), 3, detail["project_id"])
            self.assertTrue(any(event["category"] == "site_afterlife" for event in detail["timeline"]))

    def test_county_outcome_windows_are_explicit(self):
        index, details, _, _ = build_products(self.config, "2026-09-09T00:00:00+00:00")
        contexts = {detail["county_fips"]: detail["county_outcome_context"] for detail in details}
        self.assertEqual(index["counts"]["counties_with_full_post_years"], 1)
        self.assertEqual(contexts["41027"]["full_post_years_available"], 8)
        self.assertTrue(all(context["history_end_year"] == 2024 for context in contexts.values()))
        self.assertTrue(all(context["analysis_status"] == "descriptive_only" for context in contexts.values()))

    def test_every_timeline_event_and_scale_claim_resolves_to_source(self):
        _, details, _, _ = build_products(self.config, "2026-09-09T00:00:00+00:00")
        for detail in details:
            sources = {source["source_id"] for source in detail["sources"]}
            self.assertTrue(all(set(event["source_ids"]) <= sources for event in detail["timeline"]))
            self.assertTrue(all(item["source_id"] in sources for item in detail["proposed_scale"]))

    def test_public_and_entity_schemas(self):
        index, details, projects, sites = build_products(self.config, "2026-09-09T00:00:00+00:00")
        records = [
            (index, "public-rejected-project-index.schema.json"),
            *[(detail, "public-rejected-project.schema.json") for detail in details],
            *[(project, "project.schema.json") for project in projects],
            *[(site, "proposed-site.schema.json") for site in sites],
        ]
        for record, schema in records:
            self.assertEqual(self.validator.validate_record(record, ROOT / "schemas" / "v1" / schema), [])


if __name__ == "__main__":
    unittest.main()
