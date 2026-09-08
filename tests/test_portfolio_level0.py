import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_portfolio_level0 import build_portfolio_level0  # noqa: E402
from scripts.study_project_fragments import load_evidence, load_synthesis  # noqa: E402
from scripts.validate_data_contract import ContractValidator  # noqa: E402


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PortfolioLevel0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study_index = read("site/public/data/v1/study/index.json")
        cls.study_manifest = read("site/public/data/v1/study/manifest.json")
        cls.evidence = load_evidence()
        cls.synthesis = load_synthesis()
        cls.reassessment = read("data/silver/study/pooled/synthesis-reassessment.json")
        cls.derived_screen = read("data/silver/study/pooled/derived-parameter-screen.json")
        cls.aggregation_rules = read("data/silver/study/pooled/metric-aggregation-rules.json")
        cls.county_year = read("data/silver/study/pooled/county-year-exposures.json")
        cls.artifact = read("data/silver/study/pooled/portfolio-level-0-synthesis.json")
        cls.public_artifact = read("site/public/data/v1/study/pooled/portfolio-level-0-synthesis.json")
        cls.manifest = read("data/silver/study/pooled/portfolio-level-0-manifest.json")

    def test_artifact_and_manifest_validate(self):
        validator = ContractValidator(ROOT / "schemas/v1")
        self.assertEqual(
            validator.validate_record(
                self.artifact, ROOT / "schemas/v1/portfolio-level-0-synthesis.schema.json"
            ),
            [],
        )
        self.assertEqual(
            validator.validate_record(
                self.manifest, ROOT / "schemas/v1/portfolio-level-0-manifest.schema.json"
            ),
            [],
        )
        self.assertEqual(self.artifact, self.public_artifact)

    def test_scope_is_exactly_the_selected_portfolio(self):
        expected_projects = {row["project_id"] for row in self.study_index["projects"]}
        expected_counties = {row["county_fips"] for row in self.study_index["projects"]}
        self.assertEqual(len(expected_projects), 36)
        self.assertEqual(len(expected_counties), 35)
        self.assertEqual(set(self.artifact["scope"]["project_ids"]), expected_projects)
        self.assertEqual(set(self.artifact["scope"]["county_fips"]), expected_counties)
        self.assertEqual(
            {row["project_id"] for row in self.artifact["project_matrix"]},
            expected_projects,
        )

    def test_every_project_has_eight_explicit_category_gaps(self):
        expected_categories = {
            "investment", "construction", "suppliers", "operations",
            "fiscal", "public_costs", "resources", "community",
        }
        for row in self.artifact["project_matrix"]:
            self.assertEqual({cell["category"] for cell in row["categories"]}, expected_categories)
        self.assertEqual(len(self.artifact["gap_register"]), 36 * 8)
        self.assertEqual(
            len({(row["project_id"], row["category"]) for row in self.artifact["gap_register"]}),
            36 * 8,
        )

    def test_distributions_use_reported_same_year_claims_only(self):
        evidence_by_id = {row["claim_id"]: row for row in self.evidence["records"]}
        self.assertGreater(len(self.artifact["timing_aligned_reported_cohorts"]), 0)
        for cohort in self.artifact["timing_aligned_reported_cohorts"]:
            self.assertGreaterEqual(cohort["project_count"], 3)
            self.assertGreaterEqual(cohort["county_count"], 3)
            values = []
            for project_value in cohort["project_values"]:
                values.append(project_value["value"])
                for claim_id in project_value["claim_ids"]:
                    claim = evidence_by_id[claim_id]
                    self.assertEqual(claim["basis"], "reported_actual")
                    self.assertEqual(claim["project_id"], project_value["project_id"])
                    self.assertEqual(claim["metric_code"], cohort["metric_code"])
                    self.assertEqual(claim["period"]["year"], cohort["year"])
                    self.assertEqual(claim["value"], project_value["value"])
            self.assertEqual(min(values), cohort["distribution"]["minimum"])
            self.assertEqual(max(values), cohort["distribution"]["maximum"])

    def test_modeled_records_remain_separate_and_no_total_is_created(self):
        exposure_ids = {
            estimate_id
            for row in self.county_year["county_years"]
            for exposure in row["metric_exposures"]
            for estimate_id in exposure["contributing_estimate_ids"]
        }
        portfolio_ids = {
            estimate_id
            for row in self.artifact["modeled_level_0_identities"]
            for estimate_id in row["estimate_ids"]
        }
        self.assertEqual(portfolio_ids, exposure_ids)
        self.assertEqual(len(portfolio_ids), 48)
        self.assertEqual(self.artifact["counts"]["authorized_portfolio_totals"], 0)
        self.assertFalse(self.artifact["methodology"]["new_modeled_values_created"])
        self.assertEqual(
            self.artifact["publication_gate"]["portfolio_totals"],
            "blocked_no_overlap_adjudicated_cross_project_sum",
        )

    def test_checked_in_output_is_deterministic(self):
        rebuilt = build_portfolio_level0(
            self.study_index,
            self.study_manifest,
            self.evidence,
            self.synthesis,
            self.reassessment,
            self.derived_screen,
            self.aggregation_rules,
            self.county_year,
        )
        self.assertEqual(rebuilt, self.artifact)

    def test_manifest_hashes_match(self):
        for section in ("builder", "inputs", "outputs"):
            rows = [self.manifest[section]] if section == "builder" else self.manifest[section]
            for row in rows:
                path = ROOT / row["path"]
                payload = path.read_bytes()
                self.assertEqual(len(payload), row["byte_size"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), row["sha256"])


if __name__ == "__main__":
    unittest.main()
