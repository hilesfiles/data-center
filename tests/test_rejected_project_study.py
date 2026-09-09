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
