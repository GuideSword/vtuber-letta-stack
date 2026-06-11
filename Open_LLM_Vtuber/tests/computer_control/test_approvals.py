import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.approvals import ApprovalStore


class ApprovalStoreTests(unittest.TestCase):
    def test_create_and_list_pending_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalStore(Path(temp_dir) / "approvals.jsonl")
            record = store.create_request(
                requested_by="letta",
                action="browser_click",
                target="pay-now",
                risk_level="high",
                reason="payment",
                arguments={"ref": "pay-now"},
            )

            pending = store.pending()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].approval_id, record.approval_id)

    def test_approve_request(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalStore(Path(temp_dir) / "approvals.jsonl")
            record = store.create_request("letta", "browser_click", "pay-now", "high", "payment")
            updated = store.set_status(record.approval_id, "approved")

            self.assertEqual(updated.status, "approved")
            self.assertTrue(store.is_approved_for(record.approval_id, "browser_click", "pay-now"))
            self.assertEqual(store.pending(), [])


if __name__ == "__main__":
    unittest.main()
