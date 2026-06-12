import json
import unittest

from open_llm_vtuber.agent.agents.letta_tool_formatter import (
    extract_tool_media_for_user,
    format_tool_return_for_user,
)
from open_llm_vtuber.computer_control.artifacts import COMPUTER_CONTROL_ARTIFACT_ROOT


class LettaToolFormatterTests(unittest.TestCase):
    def test_formats_browser_open_for_jd(self):
        payload = {
            "status": "ok",
            "action": "browser_open",
            "message": "opened: https://www.jd.com/\ntab: t14\n",
            "data": {
                "command": ["openclaw", "browser", "open", "https://www.jd.com"],
            },
        }

        self.assertEqual(format_tool_return_for_user(json.dumps(payload)), "已打开京东网页。")

    def test_formats_browser_open_for_taobao(self):
        payload = {
            "status": "ok",
            "action": "browser_open",
            "message": "opened: https://www.taobao.com/\ntab: t13\n",
            "data": {"stdout": "opened: https://www.taobao.com/\ntab: t13\n"},
        }

        self.assertEqual(format_tool_return_for_user(json.dumps(payload)), "已打开淘宝网页。")

    def test_formats_approval_required(self):
        payload = {
            "status": "approval_required",
            "action": "browser_click",
            "message": "Approval required before executing browser_click",
            "approval_id": "approval-123",
        }

        self.assertEqual(format_tool_return_for_user(json.dumps(payload)), "这个操作需要你确认后才能继续。审批编号：approval-123。")

    def test_formats_shopping_search_prices(self):
        payload = {
            "status": "ok",
            "action": "shopping_search",
            "message": "已在淘宝搜索",
            "data": {
                "site": "taobao",
                "query": "mac book",
                "prices": ["¥9999", "¥12999"],
                "screenshot_path": r"D:\ChatWithSmallC\Open_LLM_Vtuber\.run_logs\computer_control\taobao.png",
            },
        }

        text = format_tool_return_for_user(json.dumps(payload))

        self.assertIn("我在淘宝搜索了“mac book”", text)
        self.assertIn("¥9999", text)
        self.assertIn("截图已保存到", text)

    def test_formats_shopping_search_login_required(self):
        payload = {
            "status": "ok",
            "action": "shopping_search",
            "message": "已在淘宝搜索",
            "data": {
                "site": "taobao",
                "query": "mac book",
                "prices": [],
                "login_required": True,
                "screenshot_path": r"D:\ChatWithSmallC\Open_LLM_Vtuber\.run_logs\computer_control\taobao.png",
            },
        }

        text = format_tool_return_for_user(json.dumps(payload))

        self.assertIn("要求登录或重新登录", text)
        self.assertIn("截图已保存到", text)

    def test_extracts_screenshot_media_for_allowed_artifact(self):
        COMPUTER_CONTROL_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        screenshot = COMPUTER_CONTROL_ARTIFACT_ROOT / "formatter-test.png"
        screenshot.write_bytes(b"png")
        payload = {
            "status": "ok",
            "action": "shopping_search",
            "message": "已在淘宝搜索",
            "data": {
                "site": "taobao",
                "query": "mac book",
                "prices": ["¥9999"],
                "screenshot_path": str(screenshot),
            },
        }

        try:
            text = format_tool_return_for_user(json.dumps(payload))
            media = extract_tool_media_for_user(json.dumps(payload))
        finally:
            screenshot.unlink(missing_ok=True)

        self.assertIn("截图如下", text)
        self.assertNotIn(str(screenshot), text)
        self.assertEqual(
            media,
            [
                {
                    "type": "image",
                    "url": "/computer-control-artifacts/formatter-test.png",
                    "caption": "浏览器截图",
                }
            ],
        )

    def test_ignores_unrelated_json(self):
        self.assertIsNone(format_tool_return_for_user('{"foo": "bar"}'))


if __name__ == "__main__":
    unittest.main()
