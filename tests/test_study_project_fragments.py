import json
from pathlib import Path
import tempfile
import unittest

from scripts.study_project_fragments import load_evidence, load_synthesis


class StudyProjectFragmentTest(unittest.TestCase):
    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_project_fragments_merge_in_filename_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_base = root / "evidence.json"
            evidence_fragments = root / "evidence"
            synthesis_base = root / "synthesis.json"
            synthesis_fragments = root / "synthesis"
            self.write(evidence_base, {
                "reviewed_on": "2026-09-01", "scope_note": "Base.",
                "sources": [], "records": [], "project_updates": [],
            })
            self.write(synthesis_base, {
                "reviewed_on": "2026-09-01", "scope_note": "Base.",
                "sources": [], "estimates": [],
            })
            for project_id in ("prj_study_b", "prj_study_a"):
                self.write(evidence_fragments / f"{project_id}.json", {
                    "schema_version": "1.0.0", "project_id": project_id,
                    "reviewed_on": "2026-09-05", "scope_note": "Reviewed.",
                    "sources": [{"source_id": f"src_{project_id}"}],
                    "records": [{"project_id": project_id}],
                    "project_updates": [{"project_id": project_id}],
                })
                self.write(synthesis_fragments / f"{project_id}.json", {
                    "schema_version": "1.0.0", "project_id": project_id,
                    "reviewed_on": "2026-09-05", "scope_note": "Modeled.",
                    "sources": [], "estimates": [{"project_id": project_id}],
                })
            evidence = load_evidence(evidence_base, evidence_fragments)
            synthesis = load_synthesis(synthesis_base, synthesis_fragments)
            self.assertEqual([row["project_id"] for row in evidence["records"]], ["prj_study_a", "prj_study_b"])
            self.assertEqual([row["project_id"] for row in synthesis["estimates"]], ["prj_study_a", "prj_study_b"])
            self.assertEqual(evidence["reviewed_on"], "2026-09-05")

    def test_cross_project_rows_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "evidence.json"
            fragments = root / "fragments"
            self.write(base, {
                "reviewed_on": "2026-09-01", "scope_note": "Base.",
                "sources": [], "records": [], "project_updates": [],
            })
            self.write(fragments / "prj_study_a.json", {
                "schema_version": "1.0.0", "project_id": "prj_study_a",
                "reviewed_on": "2026-09-05", "scope_note": "Reviewed.",
                "sources": [], "records": [{"project_id": "prj_study_b"}],
                "project_updates": [],
            })
            with self.assertRaisesRegex(ValueError, "cross-project"):
                load_evidence(base, fragments)


if __name__ == "__main__":
    unittest.main()
