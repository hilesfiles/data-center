import json
from pathlib import Path
import unittest

from scripts.build_project_media_timelines import ROOT, OUTPUT, SOURCE, STUDY_INDEX, validate


class ProjectMediaTimelineTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.index = json.loads(STUDY_INDEX.read_text(encoding="utf-8"))

    def test_pilot_is_valid_and_source_linked(self):
        validate(self.data, self.index)
        self.assertEqual(len(self.data["timelines"]), 3)
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

    def test_published_copy_matches_governed_source(self):
        self.assertTrue(OUTPUT.exists())
        self.assertEqual(json.loads(OUTPUT.read_text(encoding="utf-8")), self.data)


if __name__ == "__main__":
    unittest.main()
