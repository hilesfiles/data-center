import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports" / "private-sector-study" / "orchestration-ledger.json"
EVIDENCE = ROOT / "config" / "v1" / "study-economic-evidence.json"
POOLED = ROOT / "data" / "silver" / "study" / "pooled"


class OrchestrationAcceptanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_batch_nine_uses_mandatory_adversarial_contract(self):
        contract = self.ledger["worker_research_contract"]
        self.assertEqual(contract["version"], "3.1.0")
        self.assertLessEqual(contract["effective_batch"], 9)
        self.assertIn("candidate_pending_adversarial_review", contract["required_phases"])
        self.assertIn("mandatory_adversarial_continuation", contract["required_phases"])
        self.assertIn("corrective_handoff_ready", contract["required_phases"])
        self.assertIn("independent_orchestrator_acceptance", contract["required_phases"])

    def test_future_acceptance_requires_candidate_correction_and_audit(self):
        accepted_markers = ("accepted", "integrated", "published")
        for row in self.ledger["queue"]:
            if row["queue_position"] < 25:
                continue
            status = row["status"]
            if not any(marker in status for marker in accepted_markers):
                continue
            with self.subTest(project_id=row["project_id"], status=status):
                self.assertTrue(row.get("candidate_commit_sha"))
                self.assertTrue(row.get("corrective_commit_sha"))
                self.assertTrue(row.get("worker_commit_sha"))
                self.assertTrue(row.get("independent_acceptance_audit"))
                self.assertTrue(row.get("validation_result"))

    def test_current_batch_acceptance_records_correction_and_independent_audit(self):
        rows = {row["queue_position"]: row for row in self.ledger["queue"]}
        for position in (25, 26, 27):
            with self.subTest(queue_position=position):
                self.assertEqual(rows[position]["status"], "integrated_validated_published")
                self.assertTrue(rows[position]["candidate_commit_sha"])
                self.assertTrue(rows[position]["corrective_commit_sha"])
                self.assertTrue(rows[position]["worker_commit_sha"])
                self.assertTrue(rows[position]["independent_acceptance_audit"])

    def test_batch_ten_acceptance_records_correction_and_independent_audit(self):
        rows = {row["queue_position"]: row for row in self.ledger["queue"]}
        for position in (28, 29, 30):
            with self.subTest(queue_position=position):
                self.assertIn("accepted", rows[position]["status"])
                self.assertTrue(rows[position]["candidate_commit_sha"])
                self.assertTrue(rows[position]["corrective_commit_sha"])
                self.assertTrue(rows[position]["worker_commit_sha"])
                self.assertTrue(rows[position]["independent_acceptance_audit"])

    def test_public_utility_payments_have_a_distinct_direct_metric(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        metrics = {metric["metric_code"]: metric for metric in evidence["metrics"]}
        utility = metrics["study.utility_service_payments"]
        self.assertEqual(utility["category"], "fiscal")
        self.assertEqual(utility["unit"], "USD")
        self.assertNotEqual(
            utility["metric_code"], "study.infrastructure_company_payments"
        )

    def test_modeling_synthesis_checkpoint_matches_governed_artifacts(self):
        checkpoint = self.ledger["modeling_synthesis_checkpoint"]
        portfolio = json.loads(
            (POOLED / "portfolio-level-0-synthesis.json").read_text(encoding="utf-8")
        )
        derived = json.loads(
            (POOLED / "derived-parameter-screen.json").read_text(encoding="utf-8")
        )
        reassessment = json.loads(
            (POOLED / "synthesis-reassessment.json").read_text(encoding="utf-8")
        )
        facility_year = json.loads(
            (POOLED / "facility-year-exposures.json").read_text(encoding="utf-8")
        )

        self.assertEqual(checkpoint["status"], "level_0_portfolio_published_shift_ready")
        self.assertEqual(checkpoint["scope"]["projects"], portfolio["scope"]["project_count"])
        self.assertEqual(checkpoint["scope"]["host_counties"], portfolio["scope"]["county_count"])
        self.assertEqual(
            checkpoint["derived_and_exposure_state"]["derived_parameter_observations"],
            derived["counts"]["derived_observations"],
        )
        self.assertEqual(
            checkpoint["derived_and_exposure_state"]["authorized_transferable_calibration_parameters"],
            derived["counts"]["calibration_authorized_parameters"],
        )
        self.assertEqual(
            checkpoint["derived_and_exposure_state"]["facility_year_rows"],
            facility_year["counts"]["project_years"],
        )
        self.assertEqual(
            checkpoint["modeled_synthesis_dispositions"],
            reassessment["counts"]["substantive_dispositions"],
        )
        self.assertTrue((ROOT / checkpoint["artifacts"]["readable_checkpoint"]).is_file())


if __name__ == "__main__":
    unittest.main()
