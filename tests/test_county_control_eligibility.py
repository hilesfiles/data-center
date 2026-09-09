import unittest

from scripts.build_county_control_eligibility import POLICY_PATH, ROOT, build_products, read
from scripts.validate_data_contract import ContractValidator


class CountyControlEligibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index, cls.partitions, cls.records = build_products()
        cls.validator = ContractValidator(ROOT / "schemas" / "v1")

    def test_national_county_coverage_is_unique(self):
        self.assertEqual(len(self.records), 3144)
        self.assertEqual(len({record["county_fips"] for record in self.records}), 3144)
        self.assertEqual(sum(len(records) for records in self.partitions.values()), 3144)
        self.assertEqual(self.index["counts"]["states"], 51)

    def test_inventory_absence_never_becomes_verified_control(self):
        blank = [record for record in self.records if record["exposure_status"] == "no_known_project_record"]
        self.assertTrue(blank)
        self.assertTrue(all(record["control_eligibility"] == "unresolved_negative_evidence" for record in blank))
        self.assertTrue(all(record["negative_evidence_status"] == "not_audited" for record in blank))
        self.assertEqual(self.index["counts"]["by_control_eligibility"].get("eligible_verified_no_known_project", 0), 0)

    def test_known_facilities_and_stopped_proposals_are_excluded(self):
        known = [record for record in self.records if record["exposure_status"] != "no_known_project_record"]
        self.assertEqual(len(known), 231)
        self.assertTrue(all(record["control_eligibility"] == "excluded_known_exposure" for record in known))
        self.assertEqual(sum(bool(record["known_evidence"]["stopped_proposal_ids"]) for record in self.records), 7)

    def test_no_post_treatment_match_score_is_published(self):
        forbidden = {"match_score", "similarity_score", "causal_effect", "estimated_impact"}
        self.assertTrue(all(not (forbidden & set(record)) for record in self.records))
        self.assertTrue(all(record["latest_metrics"]["year"] == 2024 for record in self.records))

    def test_policy_and_public_records_validate(self):
        cases = [
            (read(POLICY_PATH), "county-control-eligibility-policy.schema.json"),
            (self.index, "public-county-control-index.schema.json"),
            *[(record, "public-county-control-eligibility.schema.json") for record in self.records],
        ]
        for record, schema in cases:
            issues = self.validator.validate_record(record, ROOT / "schemas" / "v1" / schema)
            self.assertEqual(issues, [], f"{schema}: {issues[:3]}")


if __name__ == "__main__":
    unittest.main()
