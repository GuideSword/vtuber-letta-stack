from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import PolicyDecision, PolicyResult


READ_ONLY_ACTIONS = {
    "preflight",
    "approval_status",
    "browser_snapshot",
    "browser_wait",
}

MUTATING_BROWSER_ACTIONS = {
    "browser_click",
    "browser_type",
}

APPROVAL_PURPOSES = {
    "checkout",
    "comment",
    "download",
    "email",
    "login",
    "payment",
    "post",
    "purchase",
    "send",
    "submit",
}

SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "password",
    "secret",
    "sessdata",
    "text",
    "token",
}

SECRET_VALUE_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._-]{8,}|[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})",
    re.IGNORECASE,
)

DESTRUCTIVE_COMMAND_WORDS = {
    "del",
    "erase",
    "format",
    "mkfs",
    "rd",
    "reg",
    "remove-item",
    "rm",
    "rmdir",
    "shutdown",
    "taskkill",
}

ALLOWED_SHELL_PREFIXES = (
    ("git", "status"),
    ("node", "-v"),
    ("openclaw", "--version"),
    ("where.exe", "openclaw"),
)


class ComputerControlPolicy:
    def __init__(self, allowed_roots: list[str] | None = None) -> None:
        roots = allowed_roots or [r"D:\ChatWithSmallC"]
        self.allowed_roots = [Path(root).resolve() for root in roots]

    def classify(self, action: str, arguments: dict[str, Any] | None = None) -> PolicyResult:
        args = arguments or {}
        sanitized = self.sanitize_arguments(args)

        if action in READ_ONLY_ACTIONS:
            return PolicyResult(PolicyDecision.ALLOW, f"{action} is read-only.", "low", sanitized)

        if action == "browser_screenshot":
            return self._classify_screenshot(args, sanitized)

        if action == "browser_open":
            return self._classify_browser_open(args, sanitized)

        if action in MUTATING_BROWSER_ACTIONS:
            return self._classify_browser_mutation(action, args, sanitized)

        if action in {"browser_eval", "browser_evaluate", "browser_cookies", "browser_storage"}:
            return PolicyResult(PolicyDecision.DENY, f"{action} can expose sensitive browser state.", "high", sanitized)

        if action in {"file_read", "file_write"}:
            return self._classify_file_action(action, args, sanitized)

        if action == "shell_run":
            return self._classify_shell(args, sanitized)

        return PolicyResult(PolicyDecision.DENY, f"Unsupported or unsafe action: {action}.", "high", sanitized)

    def sanitize_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in arguments.items():
            lowered = key.lower()
            if key == "approval_id":
                sanitized[key] = value
            elif any(secret_key in lowered for secret_key in SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_arguments(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_value(item) for item in value]
            else:
                sanitized[key] = self._sanitize_value(value)
        return sanitized

    def is_path_allowed(self, path_value: str) -> bool:
        try:
            candidate = Path(path_value).expanduser().resolve()
        except (OSError, RuntimeError):
            return False
        return any(candidate == root or root in candidate.parents for root in self.allowed_roots)

    def _classify_browser_open(self, arguments: dict[str, Any], sanitized: dict[str, Any]) -> PolicyResult:
        url = str(arguments.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return PolicyResult(PolicyDecision.ALLOW, "Safe browser navigation.", "low", sanitized)
        return PolicyResult(PolicyDecision.DENY, "Only http(s) browser navigation is allowed.", "high", sanitized)

    def _classify_screenshot(self, arguments: dict[str, Any], sanitized: dict[str, Any]) -> PolicyResult:
        output_path = arguments.get("path") or arguments.get("output_path")
        if output_path and not self.is_path_allowed(str(output_path)):
            return PolicyResult(PolicyDecision.DENY, "Screenshot output path is outside allowed roots.", "high", sanitized)
        return PolicyResult(PolicyDecision.ALLOW, "Browser screenshot is read-only.", "low", sanitized)

    def _classify_browser_mutation(
        self,
        action: str,
        arguments: dict[str, Any],
        sanitized: dict[str, Any],
    ) -> PolicyResult:
        purpose = str(arguments.get("purpose", "")).lower()
        ref = str(arguments.get("ref") or arguments.get("selector") or "").lower()
        if purpose in APPROVAL_PURPOSES or any(word in ref for word in APPROVAL_PURPOSES):
            return PolicyResult(
                PolicyDecision.APPROVAL_REQUIRED,
                "Browser action may submit data or trigger an external side effect.",
                "high",
                sanitized,
            )
        if action == "browser_type" and self._looks_sensitive(arguments):
            return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, "Typing may include sensitive text.", "high", sanitized)
        return PolicyResult(PolicyDecision.ALLOW, "Low-risk browser interaction.", "medium", sanitized)

    def _classify_file_action(
        self,
        action: str,
        arguments: dict[str, Any],
        sanitized: dict[str, Any],
    ) -> PolicyResult:
        path_value = str(arguments.get("path", ""))
        if not path_value:
            return PolicyResult(PolicyDecision.DENY, "File action requires a path.", "high", sanitized)
        if not self.is_path_allowed(path_value):
            return PolicyResult(PolicyDecision.DENY, "File path is outside allowed roots.", "high", sanitized)
        if action == "file_read":
            return PolicyResult(PolicyDecision.ALLOW, "File read is inside allowed roots.", "medium", sanitized)
        return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, "File write requires explicit approval.", "high", sanitized)

    def _classify_shell(self, arguments: dict[str, Any], sanitized: dict[str, Any]) -> PolicyResult:
        tokens = self._command_tokens(arguments.get("command"))
        if not tokens:
            return PolicyResult(PolicyDecision.DENY, "Shell command is empty or invalid.", "high", sanitized)
        if tokens[0].lower() in DESTRUCTIVE_COMMAND_WORDS or any(token.lower() in {">", ">>", "|"} for token in tokens):
            return PolicyResult(PolicyDecision.DENY, "Potentially destructive or piped shell command is not allowed.", "high", sanitized)
        lowered = tuple(token.lower() for token in tokens)
        if any(lowered[: len(prefix)] == prefix for prefix in ALLOWED_SHELL_PREFIXES):
            return PolicyResult(PolicyDecision.ALLOW, "Command is on the explicit allowlist.", "medium", sanitized)
        return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, "Command is not on the allowlist.", "high", sanitized)

    def _command_tokens(self, command: Any) -> list[str]:
        if isinstance(command, list):
            return [str(item) for item in command if str(item)]
        if isinstance(command, str):
            try:
                return shlex.split(command, posix=False)
            except ValueError:
                return []
        return []

    def _looks_sensitive(self, arguments: dict[str, Any]) -> bool:
        ref = str(arguments.get("ref") or arguments.get("selector") or "").lower()
        purpose = str(arguments.get("purpose", "")).lower()
        return any(word in f"{ref} {purpose}" for word in {"password", "token", "secret", "cookie", "credential"})

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return SECRET_VALUE_PATTERN.sub("[REDACTED]", value)
        if isinstance(value, dict):
            return self.sanitize_arguments(value)
        return value
