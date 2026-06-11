from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_audit_path() -> Path:
    return Path(__file__).resolve().parents[4] / ".run_logs" / "computer_control" / "audit.jsonl"


class AuditLogger:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_audit_path()

    def write_event(
        self,
        request_id: str,
        action: str,
        policy_decision: str,
        sanitized_arguments: dict[str, Any],
        result_status: str,
        output_summary: str,
        approval_id: str | None = None,
        screenshot_path: str | None = None,
        error_class: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "action": action,
            "policy_decision": policy_decision,
            "sanitized_arguments": sanitized_arguments,
            "result_status": result_status,
            "approval_id": approval_id,
            "output_summary": output_summary[:1000],
            "screenshot_path": screenshot_path,
            "error_class": error_class,
            "error_message": error_message,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
