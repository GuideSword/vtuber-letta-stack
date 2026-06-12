import unittest

from open_llm_vtuber.agent.agents.letta_agent import LettaAgent
from open_llm_vtuber.computer_control.artifacts import COMPUTER_CONTROL_ARTIFACT_ROOT
from open_llm_vtuber.computer_control.intent import ComputerControlIntent


class LettaAgentLocalIntentTests(unittest.TestCase):
    def test_screenshot_intent_gets_artifact_path(self):
        agent = object.__new__(LettaAgent)
        intent = ComputerControlIntent("browser_screenshot", {})

        arguments = agent._local_intent_arguments(intent)

        screenshot_path = arguments["path"]
        self.assertTrue(str(screenshot_path).endswith(".png"))
        self.assertIn(str(COMPUTER_CONTROL_ARTIFACT_ROOT), str(screenshot_path))


if __name__ == "__main__":
    unittest.main()
