import json
import os
import subprocess
import sys
import tempfile
import unittest

from open_llm_vtuber.computer_control.cli import _load_arguments


class ComputerControlCLITests(unittest.TestCase):
    def test_load_arguments_accepts_common_loose_object_format(self):
        arguments = _load_arguments("{url:https://example.com,seconds:2,purpose:payment}")

        self.assertEqual(
            arguments,
            {"url": "https://example.com", "seconds": 2, "purpose": "payment"},
        )

    def test_approval_status_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = dict(os.environ)
            env["PYTHONPATH"] = os.path.abspath("src") + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, "-m", "open_llm_vtuber.computer_control.cli", "approval-status"],
                cwd=os.getcwd(),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("pending", payload)

    def test_invalid_arguments_json_returns_error(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.abspath("src") + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "open_llm_vtuber.computer_control.cli",
                "execute",
                "browser_open",
                "--arguments-json",
                "{bad",
            ],
            cwd=os.getcwd(),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()
