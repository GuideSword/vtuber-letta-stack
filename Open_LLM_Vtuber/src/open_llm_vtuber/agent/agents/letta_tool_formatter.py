from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse


SITE_NAMES = {
    "jd.com": "京东",
    "taobao.com": "淘宝",
    "tmall.com": "天猫",
}


def format_tool_return_for_user(tool_return: Any) -> str | None:
    payload = _load_payload(tool_return)
    if not payload or "status" not in payload or "action" not in payload:
        return None

    status = str(payload.get("status") or "")
    action = str(payload.get("action") or "")
    message = str(payload.get("message") or "")

    if status == "ok":
        return _format_ok(action, payload, message)
    if status == "approval_required":
        approval_id = payload.get("approval_id") or (payload.get("data") or {}).get("approval", {}).get("approval_id")
        suffix = f"审批编号：{approval_id}。" if approval_id else ""
        return f"这个操作需要你确认后才能继续。{suffix}"
    if status in {"denied", "unavailable"}:
        return f"操作没有执行：{message or '当前策略不允许这个动作。'}"
    if status == "error":
        return f"操作失败：{message or '工具返回了错误。'}"
    return None


def _format_ok(action: str, payload: dict[str, Any], message: str) -> str:
    if action == "browser_open":
        url = _extract_url(payload, message)
        site_name = _site_name(url)
        if site_name:
            return f"已打开{site_name}网页。"
        if url:
            return f"已打开网页：{url}。"
        return "网页已打开。"

    if action == "browser_snapshot":
        return "已读取当前网页内容。"
    if action == "browser_screenshot":
        path = (payload.get("data") or {}).get("screenshot_path")
        return f"截图已保存到：{path}。" if path else "截图已完成。"
    if action == "browser_click":
        return "点击已完成。"
    if action == "browser_type":
        return "输入已完成。"
    if action == "browser_wait":
        return "等待已完成。"
    if action == "preflight":
        return "电脑控制已就绪。"
    return "操作已完成。"


def _load_payload(tool_return: Any) -> dict[str, Any] | None:
    if isinstance(tool_return, dict):
        return tool_return

    text = str(tool_return).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None

    nested_message = payload.get("message")
    if payload.get("status") == "error" and isinstance(nested_message, str) and nested_message.strip().startswith("{"):
        try:
            nested_payload = json.loads(nested_message)
            if isinstance(nested_payload, dict):
                return nested_payload
        except json.JSONDecodeError:
            pass
    return payload


def _extract_url(payload: dict[str, Any], message: str) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    command = data.get("command")
    if isinstance(command, list):
        for item in reversed(command):
            candidate = str(item)
            if candidate.startswith(("http://", "https://")):
                return candidate

    stdout = str(data.get("stdout") or message or "")
    match = re.search(r"opened:\s*(https?://\S+)", stdout)
    return match.group(1) if match else ""


def _site_name(url: str) -> str:
    if not url:
        return ""
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    for suffix, name in SITE_NAMES.items():
        if host == suffix or host.endswith(f".{suffix}"):
            return name
    return ""
