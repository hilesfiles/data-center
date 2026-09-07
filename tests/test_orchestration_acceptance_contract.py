import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports" / "private-sector-study" / "orchestration-ledger.json"
EVIDENCE = ROOT / "config" / "v1" / "study-economic-evidence.json"


class OrchestrationAcceptanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_batch_nine_uses_mandatory_adversarial_contract(self):
        contract = self.ledger["worker_research_contract"]
        self.assertEqual(contract["version"], "3.0.0")
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

    def test_current_batch_is_not_prematurely_accepted(self):
        rows = {row["queue_position"]: row for row in self.ledger["queue"]}
        for position in (25, 26, 27):
            with self.subTest(queue_position=position):
                self.assertNotIn("accepted", rows[position]["status"])
                self.assertNotIn("integrated", rows[position]["status"])
                self.assertIsNone(rows[position]["worker_commit_sha"])

    def test_public_utility_payments_have_a_distinct_direct_metric(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        metrics = {metric["metric_code"]: metric for metric in evidence["metrics"]}
        utility = metrics["study.utility_service_payments"]
        self.assertEqual(utility["category"], "fiscal")
        self.assertEqual(utility["unit"], "USD")
        self.assertNotEqual(
            utility["metric_code"], "study.infrastructure_company_payments"
        )


if __name__ == "__main__":
    unittest.main()
