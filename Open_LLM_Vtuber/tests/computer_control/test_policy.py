import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.models import PolicyDecision
from open_llm_vtuber.computer_control.policy import ComputerControlPolicy


class ComputerControlPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.allowed_root = Path(self.temp_dir.name)
        self.policy = ComputerControlPolicy(allowed_roots=[str(self.allowed_root)])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_only_browser_actions_are_allowed(self):
        result = self.policy.classify("browser_snapshot", {"include_html": False})
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_open_safe_url_is_allowed(self):
        result = self.policy.classify("browser_open", {"url": "https://example.com"})
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_non_http_navigation_is_denied(self):
        result = self.policy.classify("browser_open", {"url": "file:///C:/Users/sword/secrets.txt"})
        self.assertEqual(result.decision, PolicyDecision.DENY)

    def test_login_submit_requires_approval(self):
        result = self.policy.classify("browser_click", {"ref": "submit-button", "purpose": "login"})
        self.assertEqual(result.decision, PolicyDecision.APPROVAL_REQUIRED)
        self.assertEqual(result.risk_level, "high")

    def test_secret_values_are_redacted(self):
        result = self.policy.classify("browser_type", {"ref": "password", "text": "secret-value"})
        self.assertEqual(result.decision, PolicyDecision.APPROVAL_REQUIRED)
        self.assertEqual(result.sanitized_arguments["text"], "[REDACTED]")

    def test_arbitrary_browser_eval_is_denied(self):
        result = self.policy.classify("browser_eval", {"script": "document.cookie"})
        self.assertEqual(result.decision, PolicyDecision.DENY)

    def test_file_read_inside_allowed_root_is_allowed(self):
        target = self.allowed_root / "note.txt"
        result = self.policy.classify("file_read", {"path": str(target)})
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_file_write_inside_allowed_root_requires_approval(self):
        target = self.allowed_root / "note.txt"
        result = self.policy.classify("file_write", {"path": str(target)})
        self.assertEqual(result.decision, PolicyDecision.APPROVAL_REQUIRED)

    def test_file_outside_allowed_root_is_denied(self):
        result = self.policy.classify("file_read", {"path": r"C:\Users\sword\.ssh\id_rsa"})
        self.assertEqual(result.decision, PolicyDecision.DENY)

    def test_shell_allowlist_and_destructive_denial(self):
        allowed = self.policy.classify("shell_run", {"command": "node -v"})
        denied = self.policy.classify("shell_run", {"command": "Remove-Item -Recurse C:\\"})
        self.assertEqual(allowed.decision, PolicyDecision.ALLOW)
        self.assertEqual(denied.decision, PolicyDecision.DENY)


if __name__ == "__main__":
    unittest.main()
