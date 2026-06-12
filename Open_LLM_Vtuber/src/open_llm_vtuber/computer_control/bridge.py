from __future__ import annotations

import uuid
from typing import Any

from .approvals import ApprovalStore
from .audit import AuditLogger
from .models import ActionResult, PolicyDecision, ResultStatus
from .openclaw_cli import OpenClawCLI
from .policy import ComputerControlPolicy


BROWSER_ACTIONS = {
    "browser_open",
    "browser_snapshot",
    "browser_screenshot",
    "browser_click",
    "browser_type",
    "browser_wait",
}

SHOPPING_ACTIONS = {"shopping_search"}


class ComputerControlBridge:
    def __init__(
        self,
        policy: ComputerControlPolicy | None = None,
        audit_logger: AuditLogger | None = None,
        approval_store: ApprovalStore | None = None,
        openclaw: OpenClawCLI | None = None,
    ) -> None:
        self.policy = policy or ComputerControlPolicy()
        self.audit_logger = audit_logger or AuditLogger()
        self.approval_store = approval_store or ApprovalStore()
        self.openclaw = openclaw or OpenClawCLI()

    def preflight(self) -> dict[str, Any]:
        return self.openclaw.preflight().to_dict()

    def execute(self, action: str, arguments: dict[str, Any] | None = None, requested_by: str = "letta") -> ActionResult:
        args = dict(arguments or {})
        request_id = f"cc-{uuid.uuid4()}"

        if action == "preflight":
            result = ActionResult(ResultStatus.OK, action, "Preflight completed.", request_id, data=self.preflight())
            self._audit(request_id, action, PolicyDecision.ALLOW.value, {}, result)
            return result

        if action == "approval_status":
            pending = [record.__dict__ for record in self.approval_store.pending()]
            result = ActionResult(ResultStatus.OK, action, "Approval status loaded.", request_id, data={"pending": pending})
            self._audit(request_id, action, PolicyDecision.ALLOW.value, {}, result)
            return result

        policy_result = self.policy.classify(action, args)

        if policy_result.decision == PolicyDecision.DENY:
            result = ActionResult(ResultStatus.DENIED, action, policy_result.reason, request_id)
            self._audit(request_id, action, policy_result.decision.value, policy_result.sanitized_arguments, result)
            return result

        approved = self._has_approval(action, args)
        if policy_result.decision == PolicyDecision.APPROVAL_REQUIRED and not approved:
            approval = self.approval_store.create_request(
                requested_by=requested_by,
                action=action,
                target=self._target(action, args),
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
            self._audit(request_id, action, policy_result.decision.value, policy_result.sanitized_arguments, result)
            return result

        if action not in BROWSER_ACTIONS and action not in SHOPPING_ACTIONS:
            result = ActionResult(
                ResultStatus.UNAVAILABLE,
                action,
                f"{action} is policy-classified but not executable in this first browser-focused bridge.",
                request_id,
            )
            self._audit(request_id, action, policy_result.decision.value, policy_result.sanitized_arguments, result)
            return result

        try:
            if action in SHOPPING_ACTIONS:
                output = self.openclaw.run_shopping_search(args)
            else:
                output = self.openclaw.run_browser_action(action, args)
            if output["returncode"] == 0:
                result = ActionResult(ResultStatus.OK, action, output["stdout"] or "Action completed.", request_id, data=output)
            else:
                result = ActionResult(ResultStatus.ERROR, action, output["stderr"] or "OpenClaw command failed.", request_id, data=output)
        except Exception as exc:
            result = ActionResult(
                ResultStatus.ERROR,
                action,
                str(exc),
                request_id,
                data={"error_class": exc.__class__.__name__},
            )

        self._audit(request_id, action, policy_result.decision.value, policy_result.sanitized_arguments, result)
        return result

    def _has_approval(self, action: str, arguments: dict[str, Any]) -> bool:
        approval_id = arguments.get("approval_id")
        if not approval_id:
            return False
        return self.approval_store.is_approved_for(str(approval_id), action, self._target(action, arguments))

    def _target(self, action: str, arguments: dict[str, Any]) -> str:
        return str(
            arguments.get("url")
            or arguments.get("ref")
            or arguments.get("selector")
            or arguments.get("path")
            or arguments.get("command")
            or action
        )

    def _audit(
        self,
        request_id: str,
        action: str,
        policy_decision: str,
        sanitized_arguments: dict[str, Any],
        result: ActionResult,
    ) -> None:
        self.audit_logger.write_event(
            request_id=request_id,
            action=action,
            policy_decision=policy_decision,
            sanitized_arguments=sanitized_arguments,
            result_status=result.status.value,
            output_summary=result.message,
            approval_id=result.approval_id,
            screenshot_path=result.data.get("screenshot_path") if result.data else None,
            error_class=result.data.get("error_class") if result.data else None,
            error_message=result.message if result.status == ResultStatus.ERROR else None,
        )
