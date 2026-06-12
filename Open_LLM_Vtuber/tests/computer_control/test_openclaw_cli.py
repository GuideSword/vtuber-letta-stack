import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

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

    def test_screenshot_copies_openclaw_output_to_requested_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.png"
            destination = Path(temp_dir) / "copy.png"
            source.write_bytes(b"png")

            def runner(args, timeout):
                return subprocess.CompletedProcess(args, 0, stdout=str(source), stderr="")

            cli = OpenClawCLI(command="openclaw", browser_profile="openclaw", runner=runner)
            output = cli.run_browser_action("browser_screenshot", {"path": str(destination)})

            self.assertEqual(output["command"], ["openclaw", "browser", "--browser-profile", "openclaw", "screenshot"])
            self.assertEqual(output["screenshot_path"], str(destination.resolve()))
            self.assertEqual(destination.read_bytes(), b"png")

    def test_screenshot_accepts_jpg_openclaw_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.jpg"
            destination = Path(temp_dir) / "copy.jpg"
            source.write_bytes(b"jpg")

            def runner(args, timeout):
                return subprocess.CompletedProcess(args, 0, stdout=str(source), stderr="")

            cli = OpenClawCLI(command="openclaw", browser_profile="openclaw", runner=runner)
            output = cli.run_browser_action("browser_screenshot", {"path": str(destination), "full_page": True})

            self.assertEqual(output["screenshot_path"], str(destination.resolve()))
            self.assertEqual(destination.read_bytes(), b"jpg")

    def test_output_cleaning_removes_openclaw_config_warning_noise(self):
        def runner(args, timeout):
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="|\n+---+\nopened: https://example.com/\ntab: t1\n",
                stderr="Config warnings:\n- plugins.entries.openclaw-weixin: plugin disabled\n[channels] failed to load bundled channel setup entry imessage\n",
            )

        cli = OpenClawCLI(command="openclaw", browser_profile="openclaw", runner=runner)
        output = cli.run_browser_action("browser_open", {"url": "https://example.com"})

        self.assertEqual(output["stdout"], "opened: https://example.com/\ntab: t1\n")
        self.assertEqual(output["stderr"], "")

    def test_shopping_search_opens_site_and_returns_price_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            screenshot = Path(temp_dir) / "source.png"
            requested = Path(temp_dir) / "shopping.png"
            screenshot.write_bytes(b"png")
            calls = []

            def runner(args, timeout):
                calls.append(args)
                if args[-1].startswith("https://s.taobao.com/search"):
                    return subprocess.CompletedProcess(args, 0, stdout="opened", stderr="")
                if args[-1] == "snapshot":
                    snapshot = '{"ok": true, "url": "https://s.taobao.com/search?q=mac+book", "snapshot": "Apple MacBook ¥9999"}'
                    return subprocess.CompletedProcess(args, 0, stdout=snapshot, stderr="")
                if args[-1] == "screenshot" or "screenshot" in args:
                    return subprocess.CompletedProcess(args, 0, stdout=str(screenshot), stderr="")
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

            cli = OpenClawCLI(command="openclaw", browser_profile="openclaw", runner=runner)
            with patch("open_llm_vtuber.computer_control.openclaw_cli.time.sleep", return_value=None):
                output = cli.run_shopping_search({"site": "taobao", "query": "mac book", "path": str(requested)})

            self.assertEqual(output["returncode"], 0)
            self.assertIn("¥9999", output["prices"])
            self.assertEqual(output["screenshot_path"], str(requested.resolve()))
            self.assertTrue(any(call[-1].startswith("https://s.taobao.com/search") for call in calls))


if __name__ == "__main__":
    unittest.main()
