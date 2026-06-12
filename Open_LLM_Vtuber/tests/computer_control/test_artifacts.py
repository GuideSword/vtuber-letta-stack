import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.artifacts import (
    COMPUTER_CONTROL_ARTIFACT_ROOT,
    artifact_url_for_path,
)


class ComputerControlArtifactTests(unittest.TestCase):
    def test_artifact_url_for_allowed_image(self):
        COMPUTER_CONTROL_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        screenshot = COMPUTER_CONTROL_ARTIFACT_ROOT / "unit-artifact.png"
        screenshot.write_bytes(b"png")
        try:
            self.assertEqual(
                artifact_url_for_path(screenshot),
                "/computer-control-artifacts/unit-artifact.png",
            )
        finally:
            screenshot.unlink(missing_ok=True)

    def test_artifact_url_rejects_paths_outside_root(self):
        self.assertIsNone(artifact_url_for_path(Path(__file__)))


if __name__ == "__main__":
    unittest.main()
