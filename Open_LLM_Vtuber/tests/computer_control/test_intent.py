import unittest

from open_llm_vtuber.computer_control.intent import detect_computer_control_intent


class ComputerControlIntentTests(unittest.TestCase):
    def test_detects_jd_open_request(self):
        intent = detect_computer_control_intent("帮我打开京东的网页。")

        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, "browser_open")
        self.assertEqual(intent.arguments["url"], "https://www.jd.com/")

    def test_detects_taobao_shopping_search(self):
        intent = detect_computer_control_intent("使用浏览器打开淘宝查看，电动螺丝刀多少钱？请把截图也显示出来。")

        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, "shopping_search")
        self.assertEqual(intent.arguments, {"site": "taobao", "query": "电动螺丝刀"})

    def test_detects_browser_screenshot_request(self):
        intent = detect_computer_control_intent("把当前浏览器页面截图给我。")

        self.assertIsNotNone(intent)
        self.assertEqual(intent.action, "browser_screenshot")
        self.assertEqual(intent.arguments, {})

    def test_ignores_general_chat(self):
        self.assertIsNone(detect_computer_control_intent("你是谁？"))


if __name__ == "__main__":
    unittest.main()
