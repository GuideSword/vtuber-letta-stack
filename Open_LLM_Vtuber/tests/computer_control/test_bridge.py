import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.approvals import ApprovalStore
from open_llm_vtuber.computer_control.audit import AuditLogger
from open_llm_vtuber.computer_control.bridge import ComputerControlBridge
from open_llm_vtuber.computer_control.models import ResultStatus


class FakeOpenClaw:
    def preflight(self):
        raise AssertionError("preflight is not used in this test")

    def run_browser_action(self, action, arguments):
        return {"returncode": 0, "stdout": "opened", "stderr": "", "command": ["openclaw"]}


class ComputerControlBridgeTests(unittest.TestCase):
    def test_allowed_action_executes_and_audits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bridge = ComputerControlBridge(
                openclaw=FakeOpenClaw(),
                audit_logger=AuditLogger(Path(temp_dir) / "audit.jsonl"),
                approval_store=ApprovalStore(Path(temp_dir) / "approvals.jsonl"),
            )
            result = bridge.execute("browser_open", {"url": "https://example.com"})
            self.assertEqual(result.status, ResultStatus.OK)
            self.assertIn("opened", result.message)
            self.assertTrue((Path(temp_dir) / "audit.jsonl").exists())

    def test_risky_action_creates_approval_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bridge = ComputerControlBridge(
                openclaw=FakeOpenClaw(),
                audit_logger=AuditLogger(Path(temp_dir) / "audit.jsonl"),
                approval_store=ApprovalStore(Path(temp_dir) / "approvals.jsonl"),
            )
            result = bridge.execute("browser_click", {"ref": "pay-now", "purpose": "payment"})
            self.assertEqual(result.status, ResultStatus.APPROVAL_REQUIRED)
            self.assertTrue(result.approval_id)

    def test_approved_risky_action_executes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalStore(Path(temp_dir) / "approvals.jsonl")
            approval = store.create_request("letta", "browser_click", "pay-now", "high", "payment")
            store.set_status(approval.approval_id, "approved")
            bridge = ComputerControlBridge(
                openclaw=FakeOpenClaw(),
                audit_logger=AuditLogger(Path(temp_dir) / "audit.jsonl"),
                approval_store=store,
            )
            result = bridge.execute(
                "browser_click",
                {"ref": "pay-now", "purpose": "payment", "approval_id": approval.approval_id},
            )
            self.assertEqual(result.status, ResultStatus.OK)

    def test_non_browser_policy_classified_action_is_not_executed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bridge = ComputerControlBridge(
                openclaw=FakeOpenClaw(),
                audit_logger=AuditLogger(Path(temp_dir) / "audit.jsonl"),
                approval_store=ApprovalStore(Path(temp_dir) / "approvals.jsonl"),
            )
            result = bridge.execute("shell_run", {"command": "node -v"})
            self.assertEqual(result.status, ResultStatus.UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
