import json
from pathlib import Path
import unittest

from scripts.build_project_media_timelines import ROOT, OUTPUT, SOURCE, STUDY_INDEX, validate


class ProjectMediaTimelineTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.index = json.loads(STUDY_INDEX.read_text(encoding="utf-8"))

    def test_full_dataset_is_valid_complete_and_source_linked(self):
        validate(self.data, self.index)
        project_ids = {project["project_id"] for project in self.index["projects"]}
        timeline_ids = {timeline["project_id"] for timeline in self.data["timelines"]}
        self.assertEqual(timeline_ids, project_ids)
        self.assertEqual(len(self.data["timelines"]), 36)
        self.assertTrue(all(len(timeline["events"]) >= 2 for timeline in self.data["timelines"]))
        categories = {
            event["presentation_category"]
            for timeline in self.data["timelines"]
            for event in timeline["events"]
        }
        self.assertTrue({"announcement", "milestone", "expansion", "ownership", "incident", "controversy"}.issubset(categories))
        for timeline in self.data["timelines"]:
            for event in timeline["events"]:
                self.assertTrue(event["sources"])
                self.assertTrue(all(source["url"].startswith("https://") for source in event["sources"]))

        urls = {
            source["url"]
            for timeline in self.data["timelines"]
            for event in timeline["events"]
            for source in event["sources"]
        }
        self.assertGreaterEqual(len(urls), 280)

    def test_published_copy_matches_governed_source(self):
        self.assertTrue(OUTPUT.exists())
        self.assertEqual(json.loads(OUTPUT.read_text(encoding="utf-8")), self.data)


if __name__ == "__main__":
    unittest.main()
