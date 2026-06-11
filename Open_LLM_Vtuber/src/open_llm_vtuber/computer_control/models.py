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


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


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
