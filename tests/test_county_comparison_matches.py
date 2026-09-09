import unittest

from scripts.build_county_comparison_matches import ABSENCE_ADJUDICATIONS_PATH, EXPOSURE_FINDINGS_PATH, POLICY_PATH, ROOT, build_products, build_verification_queue, read
from scripts.validate_data_contract import ContractValidator


class CountyComparisonMatchesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product = build_products()
        cls.queue = build_verification_queue(cls.product)
        cls.validator = ContractValidator(ROOT / "schemas" / "v1")

    def test_all_host_counties_receive_twelve_ranked_candidates(self):
        self.assertEqual(self.product["counts"]["host_counties"], 35)
        self.assertEqual(self.product["counts"]["host_projects"], 36)
        self.assertEqual(self.product["counts"]["comparison_candidates"], 420)
        self.assertEqual(self.product["counts"]["presentation_candidates_per_host"], 5)
        self.assertTrue(all(len(host["comparison_candidates"]) == 12 for host in self.product["hosts"]))

    def test_candidates_are_not_host_counties_or_known_active_facilities(self):
        hosts = {host["county_fips"] for host in self.product["hosts"]}
        positive_exposure_fips = {finding["county_fips"] for finding in read(EXPOSURE_FINDINGS_PATH)["findings"]}
        for host in self.product["hosts"]:
            self.assertEqual([candidate["rank"] for candidate in host["comparison_candidates"]], list(range(1, 13)))
            for candidate in host["comparison_candidates"]:
                self.assertNotIn(candidate["county_fips"], hosts)
                self.assertNotIn(candidate["county_fips"], positive_exposure_fips)
                self.assertEqual(candidate["facility_screen_status"], "zero_known_records_across_three_national_registries")

    def test_nothing_is_falsely_presented_as_verified_absent(self):
        adjudications = {record["county_fips"]: record for record in read(ABSENCE_ADJUDICATIONS_PATH)["adjudications"]}
        candidate_fips = {candidate["county_fips"] for host in self.product["hosts"] for candidate in host["comparison_candidates"]}
        expected = {fips for fips, record in adjudications.items() if record["review_status"] == "verified_no_qualifying_exposure_found"} & candidate_fips
        surfaced = {candidate["county_fips"] for host in self.product["hosts"] for candidate in host["comparison_candidates"] if candidate["verification_status"] == "eligible_verified_no_known_project"}
        self.assertEqual(surfaced, expected)
        self.assertEqual(self.product["counts"]["externally_verified_absent"], len(expected))

    def test_three_pinned_sources_screen_the_candidate_pool(self):
        self.assertEqual(len(self.product["screening_sources"]), 3)
        self.assertGreaterEqual(self.product["screening_sources"][1]["record_count"], 1300)
        self.assertGreaterEqual(self.product["screening_sources"][2]["record_count"], 3400)
        self.assertTrue(all(len(source["sha256"]) == 64 for source in self.product["screening_sources"]))
        self.assertGreater(self.product["counts"]["screened_candidate_pool_count"], 1000)

    def test_candidate_specific_positive_findings_are_governed_exclusions(self):
        findings = read(EXPOSURE_FINDINGS_PATH)
        self.assertEqual(self.product["counts"]["candidate_specific_positive_exclusions"], len(findings["findings"]))
        self.assertEqual(self.product["positive_exposure_findings"]["record_count"], len(findings["findings"]))
        self.assertTrue(all(finding["sources"] for finding in findings["findings"]))

    def test_matching_uses_five_year_windows_and_no_2024_features(self):
        for host in self.product["hosts"]:
            baseline = host["baseline"]
            self.assertEqual(baseline["end_year"] - baseline["start_year"], 4)
            self.assertLessEqual(baseline["end_year"], 2020)
        self.assertNotIn("2024", str(self.product["method"]))

    def test_verification_queue_prioritizes_reused_candidates_without_claiming_absence(self):
        self.assertEqual(self.queue["counts"]["candidate_slots"], 420)
        self.assertEqual(self.queue["counts"]["unique_candidates"], self.product["counts"]["unique_comparison_counties"])
        self.assertEqual(self.queue["counts"]["locally_verified_absent"], self.product["counts"]["externally_verified_absent"])
        self.assertEqual([candidate["priority"] for candidate in self.queue["candidates"]], list(range(1, len(self.queue["candidates"]) + 1)))
        self.assertTrue(all(len(candidate["domain_reviews"]) == 7 for candidate in self.queue["candidates"]))
        self.assertTrue(all(domain["status"] in {"not_reviewed", "review_incomplete", "reviewed_no_qualifying_evidence", "qualifying_evidence_found"} for candidate in self.queue["candidates"] for domain in candidate["domain_reviews"]))

    def test_policy_and_product_validate(self):
        cases = [
            (read(POLICY_PATH), "county-comparison-matching-policy.schema.json"),
            (read(EXPOSURE_FINDINGS_PATH), "county-comparison-exposure-findings.schema.json"),
            (read(ABSENCE_ADJUDICATIONS_PATH), "county-comparison-absence-adjudications.schema.json"),
            (self.product, "public-county-comparison-match-index.schema.json"),
            (self.queue, "public-county-comparison-verification-queue.schema.json"),
        ]
        for record, schema in cases:
            self.assertEqual(self.validator.validate_record(record, ROOT / "schemas" / "v1" / schema), [])


if __name__ == "__main__":
    unittest.main()
