# OpenClaw Computer Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give XiaoC first-version computer-control capability by safely routing Letta tool calls through a local OpenClaw-first browser control bridge with approvals and audit logs.

**Architecture:** Keep `letta_agent` as the active conversation agent. Add a small `open_llm_vtuber.computer_control` package that owns policy, approvals, audit logging, OpenClaw CLI execution, and a CLI entrypoint. Add a script that registers one Letta tool which calls this local bridge; the Letta database remains local state and is not committed.

**Tech Stack:** Python 3.10+, standard library `argparse`, `dataclasses`, `json`, `subprocess`, existing `requests`, existing `letta-client`, OpenClaw CLI, Node 22.19+ selected by `nvm`.

---

## Scope

This plan implements the first version from `docs/superpowers/specs/2026-06-11-openclaw-computer-control-design.md`.

Included:

- Preflight for Node/OpenClaw/browser profile readiness.
- Browser actions: `browser_open`, `browser_snapshot`, `browser_screenshot`, `browser_click`, `browser_type`, `browser_wait`.
- Deterministic policy classification: `allow`, `approval_required`, `deny`.
- JSONL approval store and JSONL audit log under `.run_logs/computer_control`.
- A CLI bridge that can be called by Letta tool source.
- A Letta tool installation script that creates or updates the tool and attaches it to the active agent.
- Unit tests that do not require OpenClaw.
- Optional integration smoke commands that run only after preflight succeeds.

Not included in this first implementation:

- Full Windows desktop GUI control.
- Web UI approval modal.
- Broad file-write tools.
- Shell execution beyond explicit policy classification and planned allowlist support.
- MCP wrapper for non-Letta agents.

## File Map

- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/__init__.py`
  - Package exports.
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/models.py`
  - Shared dataclasses and enums.
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/policy.py`
  - Deterministic policy classifier and argument sanitization.
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/audit.py`
  - JSONL audit writer.
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/approvals.py`
  - JSONL approval store.
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/openclaw_cli.py`
  - OpenClaw command wrapper and preflight.
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/bridge.py`
  - Public action execution orchestrator.
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/cli.py`
  - CLI entrypoint for Letta tool subprocess calls and local diagnostics.
- Create: `Open_LLM_Vtuber/scripts/install_letta_computer_control_tool.py`
  - Registers and attaches the local bridge tool in Letta.
- Create: `Open_LLM_Vtuber/tests/computer_control/test_policy.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_audit.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_approvals.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_openclaw_cli.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_bridge.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_cli.py`
- Modify: `Open_LLM_Vtuber/pyproject.toml`
  - Optional script entry is acceptable, but not required; the plan uses `python -m open_llm_vtuber.computer_control.cli`.
- Modify only if needed: `.gitignore`
  - `.run_logs/` is already ignored; verify before editing.

## Task 1: Environment Preflight Baseline

**Files:**
- No code changes.

- [ ] **Step 1: Confirm clean worktree**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## main
```

- [ ] **Step 2: Confirm design commit exists**

Run:

```powershell
git log --oneline -- docs/superpowers/specs/2026-06-11-openclaw-computer-control-design.md
```

Expected includes:

```text
38a86aa Document OpenClaw computer control design
```

- [ ] **Step 3: Record current Node/OpenClaw state**

Run:

```powershell
nvm list
node -v
Get-Command openclaw -ErrorAction SilentlyContinue | Select-Object Name,Source,Version
```

Expected current known state:

```text
Node 22.22.1 is installed.
The active Node may not be 22.22.1.
openclaw may be missing from the active Node PATH.
```

- [ ] **Step 4: Try Node 22 without changing repo files**

Run:

```powershell
nvm use 22.22.1
node -v
where.exe openclaw
```

Expected if ready:

```text
v22.22.1
<path to openclaw command>
```

Expected if not ready:

```text
openclaw is not found under the active Node 22 environment.
```

- [ ] **Step 5: Commit**

No commit for this task because it makes no repo changes.

## Task 2: Package Models

**Files:**
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/__init__.py`
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/models.py`
- Test: `Open_LLM_Vtuber/tests/computer_control/test_policy.py` in the next task

- [ ] **Step 1: Create package directory**

Run:

```powershell
New-Item -ItemType Directory -Force -Path Open_LLM_Vtuber/src/open_llm_vtuber/computer_control
```

Expected: directory exists.

- [ ] **Step 2: Add package exports**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/__init__.py`:

```python
"""Computer-control bridge for Open LLM Vtuber."""

from .models import ActionRequest, ActionResult, PolicyDecision

__all__ = [
    "ActionRequest",
    "ActionResult",
    "PolicyDecision",
]
```

- [ ] **Step 3: Add shared models**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    APPROVAL_REQUIRED = "approval_required"
    DENY = "deny"


class ResultStatus(str, Enum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"
    ERROR = "error"


@dataclass(frozen=True)
class ActionRequest:
    action: str
    arguments: dict[str, Any] = field(default_factory=dict)
    requested_by: str = "letta"
    request_id: str | None = None


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str
    risk_level: str = "low"
    sanitized_arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    created_at: str
    requested_by: str
    action: str
    target: str
    risk_level: str
    reason: str
    expires_at: str
    status: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    status: ResultStatus
    action: str
    message: str
    request_id: str
    data: dict[str, Any] = field(default_factory=dict)
    approval_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass(frozen=True)
class PreflightResult:
    ready: bool
    node_version: str | None
    openclaw_available: bool
    browser_available: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 4: Run import check**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -c "from open_llm_vtuber.computer_control.models import ActionRequest, PolicyDecision; print(ActionRequest('preflight').action, PolicyDecision.ALLOW.value)"
```

Expected:

```text
preflight allow
```

- [ ] **Step 5: Commit**

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/__init__.py Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/models.py
git commit -m "Add computer control model types"
```

## Task 3: Deterministic Policy Engine

**Files:**
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/policy.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_policy.py`

- [ ] **Step 1: Create test package**

Run:

```powershell
New-Item -ItemType Directory -Force -Path Open_LLM_Vtuber/tests/computer_control
New-Item -ItemType File -Force -Path Open_LLM_Vtuber/tests/__init__.py
New-Item -ItemType File -Force -Path Open_LLM_Vtuber/tests/computer_control/__init__.py
```

Expected: test package files exist.

- [ ] **Step 2: Create failing tests**

Create `Open_LLM_Vtuber/tests/computer_control/test_policy.py`:

```python
import unittest

from open_llm_vtuber.computer_control.models import PolicyDecision
from open_llm_vtuber.computer_control.policy import ComputerControlPolicy


class ComputerControlPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = ComputerControlPolicy(allowed_roots=[r"D:\ChatWithSmallC"])

    def test_read_only_browser_actions_are_allowed(self):
        result = self.policy.classify("browser_snapshot", {"include_html": False})
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_open_safe_url_is_allowed(self):
        result = self.policy.classify("browser_open", {"url": "https://example.com"})
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_login_submit_requires_approval(self):
        result = self.policy.classify("browser_click", {"selector": "button[type=submit]", "purpose": "login"})
        self.assertEqual(result.decision, PolicyDecision.APPROVAL_REQUIRED)
        self.assertEqual(result.risk_level, "high")

    def test_payment_requires_approval(self):
        result = self.policy.classify("browser_click", {"selector": "#pay-now", "purpose": "payment"})
        self.assertEqual(result.decision, PolicyDecision.APPROVAL_REQUIRED)

    def test_arbitrary_js_is_denied(self):
        result = self.policy.classify("browser_eval", {"script": "document.cookie"})
        self.assertEqual(result.decision, PolicyDecision.DENY)

    def test_secret_values_are_redacted(self):
        result = self.policy.classify("browser_type", {"selector": "#password", "text": "secret-value"})
        self.assertEqual(result.decision, PolicyDecision.APPROVAL_REQUIRED)
        self.assertEqual(result.sanitized_arguments["text"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_policy -v
```

Expected: import failure because `policy.py` does not exist.

- [ ] **Step 4: Implement policy**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/policy.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import PolicyDecision, PolicyResult


READ_ONLY_ACTIONS = {
    "preflight",
    "browser_snapshot",
    "browser_screenshot",
    "browser_wait",
    "approval_status",
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
    "file_write",
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


class ComputerControlPolicy:
    def __init__(self, allowed_roots: list[str] | None = None) -> None:
        self.allowed_roots = [Path(root).resolve() for root in (allowed_roots or [])]

    def classify(self, action: str, arguments: dict[str, Any] | None = None) -> PolicyResult:
        args = arguments or {}
        sanitized = self.sanitize_arguments(args)

        if action in READ_ONLY_ACTIONS:
            return PolicyResult(
                decision=PolicyDecision.ALLOW,
                reason=f"{action} is read-only.",
                risk_level="low",
                sanitized_arguments=sanitized,
            )

        if action == "browser_open":
            url = str(args.get("url", ""))
            if self._is_safe_url(url):
                return PolicyResult(PolicyDecision.ALLOW, "Safe browser navigation.", "low", sanitized)
            return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, "Navigation target is not a normal http(s) URL.", "medium", sanitized)

        if action in MUTATING_BROWSER_ACTIONS:
            purpose = str(args.get("purpose", "")).lower()
            selector = str(args.get("selector", "")).lower()
            if purpose in APPROVAL_PURPOSES or any(word in selector for word in APPROVAL_PURPOSES):
                return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, "Browser action may submit data or trigger an external side effect.", "high", sanitized)
            if action == "browser_type" and self._looks_sensitive(args):
                return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, "Typing may include sensitive text.", "high", sanitized)
            return PolicyResult(PolicyDecision.ALLOW, "Low-risk browser interaction.", "medium", sanitized)

        if action in {"file_write", "shell_run"}:
            return PolicyResult(PolicyDecision.APPROVAL_REQUIRED, f"{action} requires explicit approval.", "high", sanitized)

        return PolicyResult(PolicyDecision.DENY, f"Unsupported or unsafe action: {action}.", "high", sanitized)

    def sanitize_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in arguments.items():
            lowered = key.lower()
            if any(secret_key in lowered for secret_key in SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_arguments(value)
            else:
                sanitized[key] = value
        return sanitized

    def _is_safe_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _looks_sensitive(self, arguments: dict[str, Any]) -> bool:
        selector = str(arguments.get("selector", "")).lower()
        return any(word in selector for word in {"password", "token", "secret", "cookie"})
```

- [ ] **Step 5: Run policy tests**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_policy -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/policy.py Open_LLM_Vtuber/tests/__init__.py Open_LLM_Vtuber/tests/computer_control/__init__.py Open_LLM_Vtuber/tests/computer_control/test_policy.py
git commit -m "Add computer control policy engine"
```

## Task 4: Audit Log

**Files:**
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/audit.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_audit.py`

- [ ] **Step 1: Create failing tests**

Create `Open_LLM_Vtuber/tests/computer_control/test_audit.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.audit import AuditLogger


class AuditLoggerTests(unittest.TestCase):
    def test_write_jsonl_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audit.jsonl"
            logger = AuditLogger(path)
            logger.write_event(
                request_id="req-1",
                action="browser_open",
                policy_decision="allow",
                sanitized_arguments={"url": "https://example.com"},
                result_status="ok",
                output_summary="opened",
            )

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            event = json.loads(lines[0])
            self.assertEqual(event["request_id"], "req-1")
            self.assertEqual(event["action"], "browser_open")
            self.assertEqual(event["sanitized_arguments"]["url"], "https://example.com")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_audit -v
```

Expected: import failure because `audit.py` does not exist.

- [ ] **Step 3: Implement audit logger**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/audit.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_PATH = Path("..") / ".run_logs" / "computer_control" / "audit.jsonl"


class AuditLogger:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else (Path(__file__).resolve().parents[4] / ".run_logs" / "computer_control" / "audit.jsonl")

    def write_event(
        self,
        request_id: str,
        action: str,
        policy_decision: str,
        sanitized_arguments: dict[str, Any],
        result_status: str,
        output_summary: str,
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
            "output_summary": output_summary[:1000],
            "screenshot_path": screenshot_path,
            "error_class": error_class,
            "error_message": error_message,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run audit tests**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_audit -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/audit.py Open_LLM_Vtuber/tests/computer_control/test_audit.py
git commit -m "Add computer control audit log"
```

## Task 5: Approval Store

**Files:**
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/approvals.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_approvals.py`

- [ ] **Step 1: Create failing tests**

Create `Open_LLM_Vtuber/tests/computer_control/test_approvals.py`:

```python
import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.approvals import ApprovalStore


class ApprovalStoreTests(unittest.TestCase):
    def test_create_and_approve_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalStore(Path(temp_dir) / "approvals.jsonl")
            record = store.create_request(
                requested_by="letta",
                action="browser_click",
                target="#pay-now",
                risk_level="high",
                reason="payment",
                arguments={"selector": "#pay-now"},
            )
            self.assertEqual(record.status, "pending")
            approved = store.set_status(record.approval_id, "approved")
            self.assertEqual(approved.status, "approved")
            self.assertEqual(store.get(record.approval_id).status, "approved")

    def test_pending_only_returns_pending_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ApprovalStore(Path(temp_dir) / "approvals.jsonl")
            first = store.create_request("letta", "browser_click", "#send", "high", "send", {})
            second = store.create_request("letta", "browser_type", "#q", "medium", "type", {})
            store.set_status(first.approval_id, "denied")
            pending_ids = [record.approval_id for record in store.pending()]
            self.assertEqual(pending_ids, [second.approval_id])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_approvals -v
```

Expected: import failure because `approvals.py` does not exist.

- [ ] **Step 3: Implement approval store**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/approvals.py`:

```python
from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import ApprovalRecord


VALID_STATUSES = {"pending", "approved", "denied", "expired"}


class ApprovalStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else (Path(__file__).resolve().parents[4] / ".run_logs" / "computer_control" / "approvals.jsonl")

    def create_request(
        self,
        requested_by: str,
        action: str,
        target: str,
        risk_level: str,
        reason: str,
        arguments: dict[str, Any],
        ttl_minutes: int = 15,
    ) -> ApprovalRecord:
        now = datetime.now(timezone.utc)
        record = ApprovalRecord(
            approval_id=f"approval-{uuid.uuid4()}",
            created_at=now.isoformat(),
            requested_by=requested_by,
            action=action,
            target=target,
            risk_level=risk_level,
            reason=reason,
            expires_at=(now + timedelta(minutes=ttl_minutes)).isoformat(),
            status="pending",
            arguments=arguments,
        )
        self._append(record)
        return record

    def get(self, approval_id: str) -> ApprovalRecord:
        for record in reversed(self._load()):
            if record.approval_id == approval_id:
                return record
        raise KeyError(f"Approval not found: {approval_id}")

    def pending(self) -> list[ApprovalRecord]:
        latest: dict[str, ApprovalRecord] = {}
        for record in self._load():
            latest[record.approval_id] = record
        return [record for record in latest.values() if record.status == "pending"]

    def set_status(self, approval_id: str, status: str) -> ApprovalRecord:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid approval status: {status}")
        current = self.get(approval_id)
        updated = ApprovalRecord(
            approval_id=current.approval_id,
            created_at=current.created_at,
            requested_by=current.requested_by,
            action=current.action,
            target=current.target,
            risk_level=current.risk_level,
            reason=current.reason,
            expires_at=current.expires_at,
            status=status,
            arguments=current.arguments,
        )
        self._append(updated)
        return updated

    def _append(self, record: ApprovalRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def _load(self) -> list[ApprovalRecord]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(ApprovalRecord(**json.loads(line)))
        return records
```

- [ ] **Step 4: Run approval tests**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_approvals -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/approvals.py Open_LLM_Vtuber/tests/computer_control/test_approvals.py
git commit -m "Add computer control approval store"
```

## Task 6: OpenClaw CLI Wrapper

**Files:**
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/openclaw_cli.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_openclaw_cli.py`

- [ ] **Step 1: Create failing tests with fake runner**

Create `Open_LLM_Vtuber/tests/computer_control/test_openclaw_cli.py`:

```python
import subprocess
import unittest

from open_llm_vtuber.computer_control.openclaw_cli import OpenClawCLI


class OpenClawCLITests(unittest.TestCase):
    def test_preflight_ready_with_node_22_and_browser_doctor(self):
        calls = []

        def runner(args, timeout):
            calls.append(args)
            if args[0] == "node":
                return subprocess.CompletedProcess(args, 0, stdout="v22.22.1\n", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout='{"ok":true}', stderr="")

        cli = OpenClawCLI(command="openclaw", runner=runner)
        result = cli.preflight()
        self.assertTrue(result.ready)
        self.assertTrue(result.openclaw_available)
        self.assertTrue(result.browser_available)

    def test_preflight_rejects_old_node(self):
        def runner(args, timeout):
            if args[0] == "node":
                return subprocess.CompletedProcess(args, 0, stdout="v20.19.2\n", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        cli = OpenClawCLI(command="openclaw", runner=runner)
        result = cli.preflight()
        self.assertFalse(result.ready)
        self.assertIn("Node 22.19+", result.message)

    def test_browser_open_command_shape(self):
        calls = []

        def runner(args, timeout):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, stdout="opened", stderr="")

        cli = OpenClawCLI(command="openclaw", browser_profile="openclaw", runner=runner)
        output = cli.run_browser_action("browser_open", {"url": "https://example.com"})
        self.assertEqual(output["returncode"], 0)
        self.assertEqual(calls[0][:4], ["openclaw", "browser", "open", "--browser-profile"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_openclaw_cli -v
```

Expected: import failure because `openclaw_cli.py` does not exist.

- [ ] **Step 3: Implement OpenClaw wrapper**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/openclaw_cli.py`:

```python
from __future__ import annotations

import os
import subprocess
from typing import Any, Callable

from .models import PreflightResult


Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def _default_runner(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


class OpenClawCLI:
    def __init__(
        self,
        command: str | None = None,
        browser_profile: str | None = None,
        timeout_seconds: int | None = None,
        runner: Runner | None = None,
    ) -> None:
        self.command = command or os.environ.get("OPENCLAW_COMMAND", "openclaw")
        self.browser_profile = browser_profile or os.environ.get("OPENCLAW_BROWSER_PROFILE", "openclaw")
        self.timeout_seconds = int(timeout_seconds or os.environ.get("OPENCLAW_TIMEOUT_SECONDS", "30"))
        self.runner = runner or _default_runner

    def preflight(self) -> PreflightResult:
        node = self.runner(["node", "-v"], self.timeout_seconds)
        node_version = node.stdout.strip() if node.returncode == 0 else None
        if not node_version or not self._node_is_supported(node_version):
            return PreflightResult(
                ready=False,
                node_version=node_version,
                openclaw_available=False,
                browser_available=False,
                message=f"OpenClaw requires Node 22.19+; current node is {node_version or 'unavailable'}.",
            )

        doctor = self._run(self._browser_base(json_output=True) + ["doctor"])
        if doctor.returncode != 0:
            return PreflightResult(
                ready=False,
                node_version=node_version,
                openclaw_available=False,
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
            details={"stdout": doctor.stdout[-1000:]},
        )

    def run_browser_action(self, action: str, arguments: dict[str, Any]) -> dict[str, Any]:
        command = self._build_browser_command(action, arguments)
        result = self.runner(command, self.timeout_seconds)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": self._sanitize_command(command),
        }

    def _build_browser_command(self, action: str, arguments: dict[str, Any]) -> list[str]:
        base = [self.command, "browser"]
        profile = ["--browser-profile", self.browser_profile]
        if action == "browser_open":
            return base + ["open"] + profile + [str(arguments["url"])]
        if action == "browser_snapshot":
            return base + ["snapshot"] + profile + ["--json"]
        if action == "browser_screenshot":
            return base + ["screenshot"] + profile
        if action == "browser_click":
            return base + ["click"] + profile + ["--selector", str(arguments["selector"])]
        if action == "browser_type":
            return base + ["type"] + profile + ["--selector", str(arguments["selector"]), "--text", str(arguments["text"])]
        if action == "browser_wait":
            seconds = str(arguments.get("seconds", "1"))
            return base + ["wait"] + profile + ["--seconds", seconds]
        raise ValueError(f"Unsupported browser action: {action}")

    def _node_is_supported(self, version: str) -> bool:
        clean = version.strip().lstrip("v")
        parts = clean.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        return major > 22 or (major == 22 and minor >= 12)

    def _sanitize_command(self, command: list[str]) -> list[str]:
        sanitized = []
        redact_next = False
        for item in command:
            if redact_next:
                sanitized.append("[REDACTED]")
                redact_next = False
            elif item in {"--text", "--password", "--token"}:
                sanitized.append(item)
                redact_next = True
            else:
                sanitized.append(item)
        return sanitized
```

- [ ] **Step 4: Run OpenClaw wrapper tests**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_openclaw_cli -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/openclaw_cli.py Open_LLM_Vtuber/tests/computer_control/test_openclaw_cli.py
git commit -m "Add OpenClaw CLI wrapper"
```

## Task 7: Bridge Orchestrator

**Files:**
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/bridge.py`
- Modify: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/__init__.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_bridge.py`

- [ ] **Step 1: Create failing bridge tests**

Create `Open_LLM_Vtuber/tests/computer_control/test_bridge.py`:

```python
import tempfile
import unittest
from pathlib import Path

from open_llm_vtuber.computer_control.approvals import ApprovalStore
from open_llm_vtuber.computer_control.audit import AuditLogger
from open_llm_vtuber.computer_control.bridge import ComputerControlBridge
from open_llm_vtuber.computer_control.models import ResultStatus


class FakeOpenClaw:
    def preflight(self):
        raise AssertionError("preflight is not used in this test")

    def run_browser_action(self, action, arguments):
        return {"returncode": 0, "stdout": "opened", "stderr": "", "command": ["openclaw"]}


class ComputerControlBridgeTests(unittest.TestCase):
    def test_allowed_action_executes_and_audits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bridge = ComputerControlBridge(
                openclaw=FakeOpenClaw(),
                audit_logger=AuditLogger(Path(temp_dir) / "audit.jsonl"),
                approval_store=ApprovalStore(Path(temp_dir) / "approvals.jsonl"),
            )
            result = bridge.execute("browser_open", {"url": "https://example.com"})
            self.assertEqual(result.status, ResultStatus.OK)
            self.assertIn("opened", result.message)
            self.assertTrue((Path(temp_dir) / "audit.jsonl").exists())

    def test_risky_action_creates_approval_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bridge = ComputerControlBridge(
                openclaw=FakeOpenClaw(),
                audit_logger=AuditLogger(Path(temp_dir) / "audit.jsonl"),
                approval_store=ApprovalStore(Path(temp_dir) / "approvals.jsonl"),
            )
            result = bridge.execute("browser_click", {"selector": "#pay-now", "purpose": "payment"})
            self.assertEqual(result.status, ResultStatus.APPROVAL_REQUIRED)
            self.assertTrue(result.approval_id)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_bridge -v
```

Expected: import failure because `bridge.py` does not exist.

- [ ] **Step 3: Implement bridge**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/bridge.py`:

```python
from __future__ import annotations

import uuid
from typing import Any

from .approvals import ApprovalStore
from .audit import AuditLogger
from .models import ActionResult, PolicyDecision, ResultStatus
from .openclaw_cli import OpenClawCLI
from .policy import ComputerControlPolicy


class ComputerControlBridge:
    def __init__(
        self,
        policy: ComputerControlPolicy | None = None,
        audit_logger: AuditLogger | None = None,
        approval_store: ApprovalStore | None = None,
        openclaw: OpenClawCLI | None = None,
    ) -> None:
        self.policy = policy or ComputerControlPolicy(allowed_roots=[r"D:\ChatWithSmallC"])
        self.audit_logger = audit_logger or AuditLogger()
        self.approval_store = approval_store or ApprovalStore()
        self.openclaw = openclaw or OpenClawCLI()

    def preflight(self) -> dict[str, Any]:
        return self.openclaw.preflight().to_dict()

    def execute(self, action: str, arguments: dict[str, Any] | None = None, requested_by: str = "letta") -> ActionResult:
        args = arguments or {}
        request_id = f"cc-{uuid.uuid4()}"
        policy_result = self.policy.classify(action, args)

        if policy_result.decision == PolicyDecision.DENY:
            result = ActionResult(ResultStatus.DENIED, action, policy_result.reason, request_id)
            self._audit(request_id, action, policy_result, result)
            return result

        if policy_result.decision == PolicyDecision.APPROVAL_REQUIRED:
            approval = self.approval_store.create_request(
                requested_by=requested_by,
                action=action,
                target=str(args.get("url") or args.get("selector") or action),
                risk_level=policy_result.risk_level,
                reason=policy_result.reason,
                arguments=policy_result.sanitized_arguments,
            )
            result = ActionResult(
                ResultStatus.APPROVAL_REQUIRED,
                action,
                f"Approval required before executing {action}: {policy_result.reason}",
                request_id,
                data={"approval": approval.__dict__},
                approval_id=approval.approval_id,
            )
            self._audit(request_id, action, policy_result, result)
            return result

        try:
            output = self.openclaw.run_browser_action(action, args)
            if output["returncode"] == 0:
                result = ActionResult(ResultStatus.OK, action, output["stdout"] or "Action completed.", request_id, data=output)
            else:
                result = ActionResult(ResultStatus.ERROR, action, output["stderr"] or "OpenClaw command failed.", request_id, data=output)
        except Exception as exc:
            result = ActionResult(ResultStatus.ERROR, action, str(exc), request_id, data={"error_class": exc.__class__.__name__})

        self._audit(request_id, action, policy_result, result)
        return result

    def _audit(self, request_id: str, action: str, policy_result, result: ActionResult) -> None:
        self.audit_logger.write_event(
            request_id=request_id,
            action=action,
            policy_decision=policy_result.decision.value,
            sanitized_arguments=policy_result.sanitized_arguments,
            result_status=result.status.value,
            output_summary=result.message,
            error_class=result.data.get("error_class") if result.data else None,
            error_message=result.message if result.status == ResultStatus.ERROR else None,
        )
```

- [ ] **Step 4: Export bridge from package**

Modify `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/__init__.py`:

```python
"""Computer-control bridge for Open LLM Vtuber."""

from .bridge import ComputerControlBridge
from .models import ActionRequest, ActionResult, PolicyDecision

__all__ = [
    "ActionRequest",
    "ActionResult",
    "ComputerControlBridge",
    "PolicyDecision",
]
```

- [ ] **Step 5: Run bridge tests**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_bridge -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/__init__.py Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/bridge.py Open_LLM_Vtuber/tests/computer_control/test_bridge.py
git commit -m "Add computer control bridge"
```

## Task 8: CLI Entrypoint

**Files:**
- Create: `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/cli.py`
- Create: `Open_LLM_Vtuber/tests/computer_control/test_cli.py`

- [ ] **Step 1: Create CLI tests**

Create `Open_LLM_Vtuber/tests/computer_control/test_cli.py`:

```python
import json
import subprocess
import sys
import unittest


class ComputerControlCLITests(unittest.TestCase):
    def test_approval_status_outputs_json(self):
        result = subprocess.run(
            [sys.executable, "-m", "open_llm_vtuber.computer_control.cli", "approval-status"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn("pending", payload)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_cli -v
```

Expected: module failure because `cli.py` does not exist.

- [ ] **Step 3: Implement CLI**

Create `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/cli.py`:

```python
from __future__ import annotations

import argparse
import json
import sys

from .approvals import ApprovalStore
from .bridge import ComputerControlBridge


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="computer-control")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("preflight")

    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("action")
    execute_parser.add_argument("--arguments-json", default="{}")
    execute_parser.add_argument("--requested-by", default="letta")

    subparsers.add_parser("approval-status")

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("approval_id")

    deny_parser = subparsers.add_parser("deny")
    deny_parser.add_argument("approval_id")

    args = parser.parse_args(argv)
    bridge = ComputerControlBridge()

    if args.command == "preflight":
        print(json.dumps(bridge.preflight(), ensure_ascii=False))
        return 0

    if args.command == "execute":
        arguments = json.loads(args.arguments_json)
        result = bridge.execute(args.action, arguments, requested_by=args.requested_by)
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        return 0

    store = ApprovalStore()
    if args.command == "approval-status":
        print(json.dumps({"pending": [record.__dict__ for record in store.pending()]}, ensure_ascii=False))
        return 0

    if args.command == "approve":
        record = store.set_status(args.approval_id, "approved")
        print(json.dumps(record.__dict__, ensure_ascii=False))
        return 0

    if args.command == "deny":
        record = store.set_status(args.approval_id, "denied")
        print(json.dumps(record.__dict__, ensure_ascii=False))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest tests.computer_control.test_cli -v
```

Expected: all tests pass.

- [ ] **Step 5: Run CLI manual checks**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m open_llm_vtuber.computer_control.cli approval-status
.\.venv\Scripts\python.exe -m open_llm_vtuber.computer_control.cli execute browser_click --arguments-json '{"selector":"#pay-now","purpose":"payment"}'
```

Expected:

```text
The first command prints {"pending": [...]}.
The second command prints status "approval_required" and does not call OpenClaw.
```

- [ ] **Step 6: Commit**

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/cli.py Open_LLM_Vtuber/tests/computer_control/test_cli.py
git commit -m "Add computer control CLI"
```

## Task 9: Letta Tool Installer

**Files:**
- Create: `Open_LLM_Vtuber/scripts/install_letta_computer_control_tool.py`

- [ ] **Step 1: Implement installer script**

Create `Open_LLM_Vtuber/scripts/install_letta_computer_control_tool.py`:

```python
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import requests


TOOL_NAME = "computer_control"


def build_tool_source(python_exe: str, project_root: str) -> str:
    return f'''
def computer_control(action: str, arguments_json: str = "{{}}") -> str:
    """
    Safely request a local computer-control action through the ChatWithSmallC bridge.

    Use this only when the user asks for browser or computer operation. If the result
    says approval_required, ask the user for approval instead of retrying.
    Never use this to extract credentials, cookies, tokens, or hidden browser state.
    """
    import json
    import subprocess

    result = subprocess.run(
        [
            r"{python_exe}",
            "-m",
            "open_llm_vtuber.computer_control.cli",
            "execute",
            action,
            "--arguments-json",
            arguments_json,
            "--requested-by",
            "letta",
        ],
        cwd=r"{project_root}",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        return json.dumps(
            {{"status": "error", "message": result.stderr[-1000:]}},
            ensure_ascii=False,
        )
    return result.stdout
'''


def upsert_tool(base_url: str, source_code: str) -> dict:
    response = requests.put(
        f"{base_url.rstrip('/')}/v1/tools/",
        json={
            "source_code": source_code,
            "source_type": "python",
            "description": "Safely request local OpenClaw-first browser/computer control through ChatWithSmallC policy, approval, and audit layers.",
            "tags": ["chatwithsmallc", "computer_control", "openclaw"],
            "json_schema": {
                "name": TOOL_NAME,
                "description": "Safely request local OpenClaw-first browser/computer control through ChatWithSmallC policy, approval, and audit layers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to run, such as preflight, approval_status, or a browser_* action.",
                        },
                        "arguments_json": {
                            "type": "string",
                            "description": "JSON object string with action arguments. Use OpenClaw snapshot refs for click/type.",
                        },
                    },
                    "required": ["action"],
                },
            },
            "return_char_limit": 6000,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def attach_tool(base_url: str, agent_id: str, tool_id: str) -> None:
    response = requests.patch(
        f"{base_url.rstrip('/')}/v1/agents/{agent_id}/tools/attach/{tool_id}",
        timeout=30,
    )
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:9000")
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--python-exe", default=str(Path(".venv") / "Scripts" / "python.exe"))
    args = parser.parse_args()

    project_root = str(Path(__file__).resolve().parents[1])
    python_exe = str((Path(project_root) / args.python_exe).resolve())
    source_code = build_tool_source(python_exe, project_root)
    tool = upsert_tool(args.base_url, source_code)
    tool_id = tool.get("id") or tool.get("tool_id")
    if not tool_id:
        raise RuntimeError(f"Letta did not return a tool id: {json.dumps(tool)[:1000]}")
    attach_tool(args.base_url, args.agent_id, tool_id)
    print(json.dumps({"status": "ok", "tool_id": tool_id, "tool_name": TOOL_NAME}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Syntax-check installer**

Run:

```powershell
cd Open_LLM_Vtuber
.\.venv\Scripts\python.exe -m py_compile scripts/install_letta_computer_control_tool.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Install against local Letta**

Run only after Letta is running on `localhost:9000`:

```powershell
cd Open_LLM_Vtuber
.\.venv\Scripts\python.exe scripts/install_letta_computer_control_tool.py --agent-id agent-e75b6e5f-0222-47f7-99da-3fdddea7cbe1
```

Expected:

```json
{"status":"ok","tool_id":"...","tool_name":"computer_control"}
```

- [ ] **Step 4: Verify tool is attached**

Run:

```powershell
Invoke-RestMethod -Uri "http://localhost:9000/v1/agents/agent-e75b6e5f-0222-47f7-99da-3fdddea7cbe1/tools" | ConvertTo-Json -Depth 5
```

Expected: response includes a tool named `computer_control`.

- [ ] **Step 5: Commit**

```powershell
git add Open_LLM_Vtuber/scripts/install_letta_computer_control_tool.py
git commit -m "Add Letta computer control tool installer"
```

## Task 10: Unit Test Sweep

**Files:**
- All computer control package and tests.

- [ ] **Step 1: Run all computer-control tests**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest discover -s tests/computer_control -v
```

Expected: all tests pass.

- [ ] **Step 2: Run compile checks**

Run:

```powershell
cd Open_LLM_Vtuber
.\.venv\Scripts\python.exe -m py_compile `
  src/open_llm_vtuber/computer_control/models.py `
  src/open_llm_vtuber/computer_control/policy.py `
  src/open_llm_vtuber/computer_control/audit.py `
  src/open_llm_vtuber/computer_control/approvals.py `
  src/open_llm_vtuber/computer_control/openclaw_cli.py `
  src/open_llm_vtuber/computer_control/bridge.py `
  src/open_llm_vtuber/computer_control/cli.py `
  scripts/install_letta_computer_control_tool.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Confirm audit logs are ignored**

Run:

```powershell
git status --ignored --short .run_logs
```

Expected includes ignored `.run_logs/` and no staged log files.

- [ ] **Step 4: Commit**

No commit if Tasks 2-9 already committed and this task only verifies.

## Task 11: OpenClaw Runtime Smoke

**Files:**
- No code changes unless the CLI command names differ from installed OpenClaw help.

- [ ] **Step 1: Select compatible Node**

Run:

```powershell
nvm use 22.22.1
node -v
```

Expected:

```text
v22.22.1
```

- [ ] **Step 2: Ensure OpenClaw CLI is installed in Node 22**

Run:

```powershell
where.exe openclaw
openclaw --version
```

Expected: both commands succeed.

If `openclaw` is missing, install the official OpenClaw CLI following the current OpenClaw docs for Node 22. Do not install or vendor OpenClaw inside the repo.

- [ ] **Step 3: Run bridge preflight**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m open_llm_vtuber.computer_control.cli preflight
```

Expected ready state:

```json
{"ready":true,"openclaw_available":true,"browser_available":true}
```

If OpenClaw Browser is unavailable, capture the error in final notes and do not claim runtime browser control works.

- [ ] **Step 4: Open a safe page**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m open_llm_vtuber.computer_control.cli execute browser_open --arguments-json '{"url":"https://example.com"}'
```

Expected:

```json
{"status":"ok","action":"browser_open"}
```

- [ ] **Step 5: Verify risky action is gated**

Run:

```powershell
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m open_llm_vtuber.computer_control.cli execute browser_click --arguments-json '{"selector":"#pay-now","purpose":"payment"}'
```

Expected:

```json
{"status":"approval_required","action":"browser_click","approval_id":"approval-..."}
```

- [ ] **Step 6: Commit command-map fix if needed**

If OpenClaw help shows different subcommands than the wrapper uses, adjust only `openclaw_cli.py`, rerun unit tests, rerun smoke, and commit:

```powershell
git add Open_LLM_Vtuber/src/open_llm_vtuber/computer_control/openclaw_cli.py
git commit -m "Align OpenClaw browser command mapping"
```

## Task 12: Letta End-to-End Smoke

**Files:**
- Local Letta state only; no repo changes expected.

- [ ] **Step 1: Confirm Letta and Open LLM Vtuber are running**

Run:

```powershell
(Invoke-WebRequest -Uri 'http://localhost:9000' -UseBasicParsing -TimeoutSec 5).StatusCode
(Invoke-WebRequest -Uri 'http://localhost:12393' -UseBasicParsing -TimeoutSec 5).StatusCode
```

Expected:

```text
200
200
```

- [ ] **Step 2: Install or refresh Letta tool**

Run:

```powershell
cd Open_LLM_Vtuber
.\.venv\Scripts\python.exe scripts/install_letta_computer_control_tool.py --agent-id agent-e75b6e5f-0222-47f7-99da-3fdddea7cbe1
```

Expected: script prints `status: ok`.

- [ ] **Step 3: Ask Letta for a low-risk browser action**

Use the existing `letta-client` pattern from prior smoke tests to send a message:

```powershell
cd Open_LLM_Vtuber
@'
from letta_client import Letta

client = Letta(base_url="http://localhost:9000")
stream = client.agents.messages.create_stream(
    agent_id="agent-e75b6e5f-0222-47f7-99da-3fdddea7cbe1",
    messages=[{"role": "user", "content": "Use your computer_control tool to run preflight only, then summarize the result in one sentence."}],
    stream_tokens=False,
)
for event in stream:
    print(event)
'@ | .\.venv\Scripts\python.exe -
```

Expected: the agent calls the tool or reports the preflight result. The output must not expose keys, cookies, or browser profile contents.

- [ ] **Step 4: Ask Letta for a risky action**

Run the same smoke pattern with this message:

```text
Use your computer_control tool to click a payment button with selector #pay-now for purpose payment.
```

Expected: tool result is `approval_required`, and XiaoC asks for approval instead of claiming it clicked.

- [ ] **Step 5: Confirm logs and Git cleanliness**

Run:

```powershell
git status --short --branch
git grep -n -E "sk-[A-Za-z0-9_-]{20,}|sessdata|cookie" -- .
```

Expected:

```text
## main
```

The secret scan may find benign documentation words such as `cookie`; it must not find actual secret values.

## Task 13: Final Verification and Handoff

**Files:**
- No code changes expected.

- [ ] **Step 1: Summarize verification evidence**

Collect these outputs for final response:

```powershell
git log -5 --oneline
git status --short --branch
cd Open_LLM_Vtuber
$env:PYTHONPATH='D:\ChatWithSmallC\Open_LLM_Vtuber\src'
.\.venv\Scripts\python.exe -m unittest discover -s tests/computer_control -v
.\.venv\Scripts\python.exe -m open_llm_vtuber.computer_control.cli preflight
```

- [ ] **Step 2: State runtime limitations clearly**

Final response must distinguish:

- code implemented and tested;
- OpenClaw runtime ready or not ready;
- Letta tool installed or not installed;
- browser smoke passed or skipped;
- high-risk approval gate verified or not verified.

- [ ] **Step 3: Do not mark the long-running goal complete unless all first-version acceptance criteria pass**

The goal can be marked complete only if:

- unit tests pass;
- preflight works without leaking secrets;
- at least one safe browser action reaches OpenClaw;
- risky action returns `approval_required`;
- Letta tool is attached and can call the bridge;
- audit log is produced under ignored `.run_logs`;
- Git tracked files are clean and contain no secrets.
