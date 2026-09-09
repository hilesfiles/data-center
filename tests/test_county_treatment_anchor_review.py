import unittest

from scripts.build_county_comparison_matches import ROOT, read
from scripts.build_county_treatment_anchor_review import ADJUDICATIONS_PATH, EXPOSURE_POLICY_PATH, build_product
from scripts.validate_data_contract import ContractValidator


class CountyTreatmentAnchorReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product = build_product()
        cls.validator = ContractValidator(ROOT / "schemas" / "v1")

    def test_first_adjudication_tranche_is_explicit_and_not_causal_ready(self):
        self.assertEqual(self.product["counts"]["host_counties"], 35)
        self.assertEqual(self.product["counts"]["host_projects"], 36)
        self.assertEqual(self.product["counts"]["adjudicated_counties"], 5)
        self.assertEqual(self.product["counts"]["causal_ready_counties"], 0)
        self.assertEqual(self.product["counts"]["unresolved_counties"], 30)
        reviewed = [county for county in self.product["counties"] if county["county_first_material_exposure_status"] != "unresolved"]
        self.assertEqual(len(reviewed), 5)
        self.assertTrue(all(county["causal_use_status"].startswith("not_ready") for county in reviewed))
        self.assertTrue(all(county["adjudication_sources"] for county in reviewed))

    def test_stored_anchors_are_only_candidate_evidence(self):
        projects = [project for county in self.product["counties"] for project in county["projects"]]
        self.assertEqual(len(projects), 36)
        self.assertTrue(all(project["stored_history_anchor"]["status"] == "candidate_project_anchor_only" for project in projects))
        self.assertTrue(all(len(county["review_domains"]) == 7 for county in self.product["counties"]))

    def test_exposure_policy_and_queue_validate(self):
        cases = [
            (read(EXPOSURE_POLICY_PATH), "county-data-center-exposure-policy.schema.json"),
            (read(ADJUDICATIONS_PATH), "county-treatment-anchor-adjudications.schema.json"),
            (self.product, "public-county-treatment-anchor-review.schema.json"),
        ]
        for record, schema in cases:
            self.assertEqual(self.validator.validate_record(record, ROOT / "schemas" / "v1" / schema), [])


if __name__ == "__main__":
    unittest.main()
