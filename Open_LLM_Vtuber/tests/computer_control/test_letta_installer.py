import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "install_letta_computer_control_tool.py"


def load_installer_module():
    spec = importlib.util.spec_from_file_location("install_letta_computer_control_tool", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LettaInstallerTests(unittest.TestCase):
    def test_tool_source_sets_pythonpath_and_returns_json_error(self):
        installer = load_installer_module()
        source = installer.build_tool_source(r"C:\Python\python.exe", r"D:\ChatWithSmallC\Open_LLM_Vtuber")

        self.assertIn("PYTHONPATH", source)
        self.assertIn("json.dumps", source)
        self.assertIn("approval_required", source)
        self.assertNotIn("sk-", source)

    def test_tool_payload_uses_openclaw_tags(self):
        installer = load_installer_module()
        payload = installer.tool_payload("def computer_control(): pass")

        self.assertEqual(payload["source_type"], "python")
        self.assertEqual(payload["json_schema"]["name"], "computer_control")
        self.assertIn("action", payload["json_schema"]["parameters"]["required"])
        self.assertIn("computer_control", payload["tags"])
        self.assertIn("openclaw", payload["tags"])


if __name__ == "__main__":
    unittest.main()
