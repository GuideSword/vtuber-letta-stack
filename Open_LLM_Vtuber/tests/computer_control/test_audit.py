import json
import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.audit import AuditLogger


class AuditLoggerTests(unittest.TestCase):
    def test_write_jsonl_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audit.jsonl"
            logger = AuditLogger(path)
            logger.write_event(
                request_id="req-1",
                action="browser_open",
                policy_decision="allow",
                sanitized_arguments={"url": "https://example.com"},
                result_status="ok",
                output_summary="opened",
            )

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])
            self.assertEqual(event["request_id"], "req-1")
            self.assertEqual(event["action"], "browser_open")
            self.assertEqual(event["sanitized_arguments"]["url"], "https://example.com")


if __name__ == "__main__":
    unittest.main()
