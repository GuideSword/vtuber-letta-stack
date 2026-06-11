import subprocess
import unittest

from open_llm_vtuber.computer_control.openclaw_cli import OpenClawCLI


class OpenClawCLITests(unittest.TestCase):
    def test_preflight_ready_with_node_22_and_browser_doctor(self):
        calls = []

        def runner(args, timeout):
            calls.append(args)
            if args == ["node", "-v"]:
                return subprocess.CompletedProcess(args, 0, stdout="v22.22.1\n", stderr="")
            if args == ["openclaw", "--version"]:
                return subprocess.CompletedProcess(args, 0, stdout="openclaw 1.0.0\n", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout='{"ok":true}', stderr="")

        cli = OpenClawCLI(command="openclaw", runner=runner)
        result = cli.preflight()
        self.assertTrue(result.ready)
        self.assertTrue(result.openclaw_available)
        self.assertTrue(result.browser_available)
        self.assertIn(["openclaw", "browser", "--browser-profile", "openclaw", "--json", "doctor"], calls)

    def test_preflight_rejects_old_node(self):
        def runner(args, timeout):
            if args[0] == "node":
                return subprocess.CompletedProcess(args, 0, stdout="v20.19.2\n", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        cli = OpenClawCLI(command="openclaw", runner=runner)
        result = cli.preflight()
        self.assertFalse(result.ready)
        self.assertIn("Node 22.19+", result.message)

    def test_preflight_rejects_node_22_18(self):
        def runner(args, timeout):
            if args[0] == "node":
                return subprocess.CompletedProcess(args, 0, stdout="v22.18.0\n", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        cli = OpenClawCLI(command="openclaw", runner=runner)
        result = cli.preflight()
        self.assertFalse(result.ready)
        self.assertIn("Node 22.19+", result.message)

    def test_preflight_rejects_doctor_json_ok_false(self):
        def runner(args, timeout):
            if args == ["node", "-v"]:
                return subprocess.CompletedProcess(args, 0, stdout="v22.22.1\n", stderr="")
            if args == ["openclaw", "--version"]:
                return subprocess.CompletedProcess(args, 0, stdout="openclaw 1.0.0\n", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout='{"ok": false}', stderr="")

        cli = OpenClawCLI(command="openclaw", runner=runner)
        result = cli.preflight()
        self.assertFalse(result.ready)
        self.assertTrue(result.openclaw_available)
        self.assertFalse(result.browser_available)

    def test_browser_open_command_shape(self):
        calls = []

        def runner(args, timeout):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, stdout="opened", stderr="")

        cli = OpenClawCLI(command="openclaw", browser_profile="openclaw", runner=runner)
        output = cli.run_browser_action("browser_open", {"url": "https://example.com"})
        self.assertEqual(output["returncode"], 0)
        self.assertEqual(calls[0], ["openclaw", "browser", "--browser-profile", "openclaw", "open", "https://example.com"])

    def test_browser_type_redacts_command_text(self):
        def runner(args, timeout):
            return subprocess.CompletedProcess(args, 0, stdout="typed", stderr="")

        cli = OpenClawCLI(command="openclaw", browser_profile="openclaw", runner=runner)
        output = cli.run_browser_action("browser_type", {"ref": "e12", "text": "secret"})
        self.assertEqual(output["command"][-1], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
