from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus

from .models import PreflightResult


Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def _default_runner(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


class OpenClawCLI:
    def __init__(
        self,
        command: str | None = None,
        browser_profile: str | None = None,
        timeout_seconds: int | None = None,
        runner: Runner | None = None,
    ) -> None:
        raw_command = command or os.environ.get("OPENCLAW_COMMAND", "openclaw")
        self.command = raw_command if runner is not None else self._resolve_command(raw_command)
        self.browser_profile = browser_profile or os.environ.get("OPENCLAW_BROWSER_PROFILE", "openclaw")
        self.timeout_seconds = int(timeout_seconds or os.environ.get("OPENCLAW_TIMEOUT_SECONDS", "30"))
        self.runner = runner or _default_runner

    def preflight(self) -> PreflightResult:
        node = self._run(["node", "-v"])
        node_version = node.stdout.strip() if node.returncode == 0 else None
        if not node_version or not self._node_is_supported(node_version):
            return PreflightResult(
                ready=False,
                node_version=node_version,
                openclaw_available=False,
                browser_available=False,
                message=f"OpenClaw requires Node 22.19+; current node is {node_version or 'unavailable'}.",
                details={"stderr": node.stderr[-1000:]},
            )

        version = self._run([self.command, "--version"])
        if version.returncode != 0:
            return PreflightResult(
                ready=False,
                node_version=node_version,
                openclaw_available=False,
                browser_available=False,
                message="OpenClaw CLI is not available.",
                details={"stdout": version.stdout[-1000:], "stderr": version.stderr[-1000:]},
            )

        doctor = self._run(self._browser_base(json_output=True) + ["doctor"])
        if doctor.returncode != 0 or not self._doctor_is_ok(doctor.stdout):
            return PreflightResult(
                ready=False,
                node_version=node_version,
                openclaw_available=True,
                browser_available=False,
                message="OpenClaw Browser preflight failed.",
                details={"stdout": doctor.stdout[-1000:], "stderr": doctor.stderr[-1000:]},
            )

        return PreflightResult(
            ready=True,
            node_version=node_version,
            openclaw_available=True,
            browser_available=True,
            message="OpenClaw Browser is ready.",
            details={"stdout": doctor.stdout[-1000:], "openclaw_version": version.stdout.strip()},
        )

    def run_browser_action(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        command = self._build_browser_command(action, arguments)
        result = self._run(command)
        stdout = self._clean_output(result.stdout)
        stderr = self._clean_output(result.stderr)
        payload = {
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "command": self._sanitize_command(command, action),
        }
        if action == "browser_screenshot" and result.returncode == 0:
            payload.update(self._handle_screenshot_output(stdout, arguments))
        return payload

    def run_shopping_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        site = str(arguments.get("site", "")).lower()
        query = str(arguments.get("query", "")).strip()
        url = self._shopping_search_url(site, query)

        open_result = self.run_browser_action("browser_open", {"url": url})
        if open_result["returncode"] != 0:
            return {
                "returncode": open_result["returncode"],
                "stdout": "",
                "stderr": open_result["stderr"],
                "command": open_result["command"],
                "site": site,
                "query": query,
                "url": url,
            }

        wait_ms = int(arguments.get("wait_ms") or 6000)
        time.sleep(max(0, wait_ms) / 1000)

        snapshot_result = self.run_browser_action("browser_snapshot", {})
        snapshot_payload = self._parse_snapshot(snapshot_result.get("stdout", ""))
        snapshot_text = snapshot_payload.get("snapshot", "")

        screenshot_path = arguments.get("path") or arguments.get("output_path") or self._default_shopping_screenshot_path(site)
        screenshot_result = self.run_browser_action("browser_screenshot", {"path": str(screenshot_path)})

        summary = self._summarize_shopping_snapshot(site, query, snapshot_payload, snapshot_text)
        return {
            "returncode": 0,
            "stdout": summary,
            "stderr": snapshot_result.get("stderr") or screenshot_result.get("stderr") or "",
            "command": open_result["command"],
            "site": site,
            "query": query,
            "url": url,
            "prices": self._extract_prices(snapshot_text),
            "login_required": self._looks_login_required(snapshot_text),
            "loading": "加载中" in snapshot_text,
            "snapshot_url": snapshot_payload.get("url"),
            "snapshot_summary": snapshot_text[:2000],
            "screenshot_path": screenshot_result.get("screenshot_path") or screenshot_result.get("openclaw_screenshot_path"),
        }

    def _build_browser_command(self, action: str, arguments: dict[str, Any]) -> list[str]:
        base = self._browser_base()
        if action == "browser_open":
            return base + ["open", str(arguments["url"])]
        if action == "browser_snapshot":
            command = self._browser_base(json_output=bool(arguments.get("json", True))) + ["snapshot"]
            if arguments.get("urls"):
                command.append("--urls")
            return command
        if action == "browser_screenshot":
            command = base + ["screenshot"]
            if arguments.get("full_page"):
                command.append("--full-page")
            if arguments.get("labels"):
                command.append("--labels")
            if arguments.get("ref"):
                command += ["--ref", str(arguments["ref"])]
            return command
        if action == "browser_click":
            return base + ["click", self._ref(arguments)]
        if action == "browser_type":
            return base + ["type", self._ref(arguments), str(arguments["text"])]
        if action == "browser_wait":
            command = base + ["wait"]
            if arguments.get("text"):
                command += ["--text", str(arguments["text"])]
            elif arguments.get("timeout_ms"):
                command += ["--timeout-ms", str(arguments["timeout_ms"])]
            return command
        raise ValueError(f"Unsupported browser action: {action}")

    def _shopping_search_url(self, site: str, query: str) -> str:
        encoded = quote_plus(query)
        if site == "taobao":
            return f"https://s.taobao.com/search?q={encoded}"
        if site in {"jd", "jingdong"}:
            return f"https://search.jd.com/Search?keyword={encoded}&enc=utf-8"
        raise ValueError(f"Unsupported shopping site: {site}")

    def _parse_snapshot(self, stdout: str) -> dict[str, Any]:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return {"snapshot": stdout}
        return payload if isinstance(payload, dict) else {"snapshot": stdout}

    def _summarize_shopping_snapshot(
        self,
        site: str,
        query: str,
        payload: dict[str, Any],
        snapshot_text: str,
    ) -> str:
        site_name = {"taobao": "淘宝", "jd": "京东", "jingdong": "京东"}.get(site, site)
        prices = self._extract_prices(snapshot_text)
        if prices:
            sample = "、".join(prices[:5])
            return f"已在{site_name}搜索“{query}”。页面中识别到的价格包括：{sample}。"
        if self._looks_login_required(snapshot_text):
            return f"已在{site_name}搜索“{query}”，但页面要求登录或重新登录，暂时无法读取商品价格。"
        if "加载中" in snapshot_text:
            return f"已在{site_name}搜索“{query}”，但商品列表仍在加载中，暂时没有读到价格。"
        if payload.get("url"):
            return f"已在{site_name}打开“{query}”的搜索结果页，但当前页面没有读到明确价格。"
        return f"已尝试在{site_name}搜索“{query}”，但没有读到搜索结果。"

    def _extract_prices(self, snapshot_text: str) -> list[str]:
        seen = set()
        prices = []
        for match in re.finditer(r"[¥￥]\s*\d+(?:\.\d+)?|\b\d{3,6}(?:\.\d{1,2})?\s*元", snapshot_text):
            price = re.sub(r"\s+", "", match.group(0))
            if price not in seen:
                seen.add(price)
                prices.append(price)
            if len(prices) >= 10:
                break
        return prices

    def _looks_login_required(self, snapshot_text: str) -> bool:
        return any(marker in snapshot_text for marker in {"请登录", "重新登录", "扫码登录", "密码登录"})

    def _default_shopping_screenshot_path(self, site: str) -> Path:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        return Path(__file__).resolve().parents[4] / ".run_logs" / "computer_control" / f"{site}-search-{timestamp}.png"

    def _browser_base(self, json_output: bool = False) -> list[str]:
        command = [self.command, "browser", "--browser-profile", self.browser_profile]
        if json_output:
            command.append("--json")
        return command

    def _resolve_command(self, command: str) -> str:
        return shutil.which(command) or command

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(args, self.timeout_seconds)
        except FileNotFoundError as exc:
            return subprocess.CompletedProcess(args, 127, stdout="", stderr=str(exc))
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(args, 124, stdout=exc.stdout or "", stderr=exc.stderr or "Timed out")

    def _ref(self, arguments: dict[str, Any]) -> str:
        ref = arguments.get("ref") or arguments.get("selector")
        if not ref:
            raise ValueError("Browser ref is required.")
        return str(ref)

    def _handle_screenshot_output(self, stdout: str, arguments: dict[str, Any]) -> dict[str, Any]:
        openclaw_path = self._extract_screenshot_path(stdout)
        payload: dict[str, Any] = {}
        if openclaw_path:
            payload["openclaw_screenshot_path"] = str(openclaw_path)

        requested_path = arguments.get("path") or arguments.get("output_path")
        if requested_path and openclaw_path and openclaw_path.exists():
            destination = Path(str(requested_path)).expanduser().resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(openclaw_path, destination)
            payload["screenshot_path"] = str(destination)
        elif requested_path:
            payload["screenshot_path_error"] = "OpenClaw screenshot path was not found in command output."
        return payload

    def _extract_screenshot_path(self, stdout: str) -> Path | None:
        for line in reversed(stdout.splitlines()):
            candidate = line.strip()
            if not re.search(r"\.(png|jpe?g)$", candidate, re.IGNORECASE):
                continue
            match = re.search(r"(~[\\/][^\s]+\.(?:png|jpe?g)|[A-Za-z]:[\\/][^\s]+\.(?:png|jpe?g))", candidate, re.IGNORECASE)
            if not match:
                continue
            value = match.group(1)
            return Path(value).expanduser().resolve()
        return None

    def _clean_output(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped in {"|"} or stripped.startswith(("+", "|")):
                continue
            if stripped.startswith("o  Config warnings"):
                continue
            if stripped.startswith("Config warnings:"):
                continue
            if stripped.startswith("- plugins.entries.openclaw-weixin"):
                continue
            if stripped.startswith("[channels] failed to load bundled channel setup entry"):
                continue
            lines.append(line)
        return "\n".join(lines) + ("\n" if lines else "")

    def _node_is_supported(self, version: str) -> bool:
        clean = version.strip().lstrip("v")
        parts = clean.split(".")
        try:
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
        except (IndexError, ValueError):
            return False
        return major > 22 or (major == 22 and minor >= 19)

    def _doctor_is_ok(self, stdout: str) -> bool:
        stripped = stdout.strip()
        if not stripped:
            return True
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return True
        return bool(payload.get("ok", True))

    def _sanitize_command(self, command: list[str], action: str) -> list[str]:
        sanitized = list(command)
        if action == "browser_type" and sanitized:
            sanitized[-1] = "[REDACTED]"
        for index, item in enumerate(sanitized[:-1]):
            if item in {"--text", "--password", "--token", "--credentials"}:
                sanitized[index + 1] = "[REDACTED]"
        return sanitized
