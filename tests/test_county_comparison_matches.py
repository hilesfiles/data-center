import unittest

from scripts.build_county_comparison_matches import POLICY_PATH, ROOT, build_products, read
from scripts.validate_data_contract import ContractValidator


class CountyComparisonMatchesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product = build_products()
        cls.validator = ContractValidator(ROOT / "schemas" / "v1")

    def test_all_host_counties_receive_five_ranked_candidates(self):
        self.assertEqual(self.product["counts"]["host_counties"], 35)
        self.assertEqual(self.product["counts"]["host_projects"], 36)
        self.assertEqual(self.product["counts"]["comparison_candidates"], 175)
        self.assertTrue(all(len(host["comparison_candidates"]) == 5 for host in self.product["hosts"]))

    def test_candidates_are_not_host_counties_or_known_active_facilities(self):
        hosts = {host["county_fips"] for host in self.product["hosts"]}
        for host in self.product["hosts"]:
            self.assertEqual([candidate["rank"] for candidate in host["comparison_candidates"]], [1, 2, 3, 4, 5])
            for candidate in host["comparison_candidates"]:
                self.assertNotIn(candidate["county_fips"], hosts)
                self.assertEqual(candidate["facility_screen_status"], "zero_known_records_across_two_national_registries")

    def test_nothing_is_falsely_presented_as_verified_absent(self):
        self.assertEqual(self.product["counts"]["externally_verified_absent"], 0)
        statuses = {candidate["verification_status"] for host in self.product["hosts"] for candidate in host["comparison_candidates"]}
        self.assertEqual(statuses, {"local_facility_absence_review_required"})

    def test_two_pinned_sources_screen_the_candidate_pool(self):
        self.assertEqual(len(self.product["screening_sources"]), 2)
        self.assertGreaterEqual(self.product["screening_sources"][1]["record_count"], 1300)
        self.assertTrue(all(len(source["sha256"]) == 64 for source in self.product["screening_sources"]))
        self.assertGreater(self.product["counts"]["screened_candidate_pool_count"], 1000)

    def test_matching_uses_five_year_windows_and_no_2024_features(self):
        for host in self.product["hosts"]:
            baseline = host["baseline"]
            self.assertEqual(baseline["end_year"] - baseline["start_year"], 4)
            self.assertLessEqual(baseline["end_year"], 2020)
        self.assertNotIn("2024", str(self.product["method"]))

    def test_policy_and_product_validate(self):
        cases = [
            (read(POLICY_PATH), "county-comparison-matching-policy.schema.json"),
            (self.product, "public-county-comparison-match-index.schema.json"),
        ]
        for record, schema in cases:
            self.assertEqual(self.validator.validate_record(record, ROOT / "schemas" / "v1" / schema), [])


if __name__ == "__main__":
    unittest.main()
