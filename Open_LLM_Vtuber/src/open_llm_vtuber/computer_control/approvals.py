from __future__ import annotations

import json
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import ApprovalRecord, ApprovalStatus


def default_approval_path() -> Path:
    return Path(__file__).resolve().parents[4] / ".run_logs" / "computer_control" / "approvals.jsonl"


class ApprovalStore:
    def __init__(self, path: str | Path | None = None, ttl_minutes: int = 15) -> None:
        self.path = Path(path) if path else default_approval_path()
        self.ttl_minutes = ttl_minutes

    def create_request(
        self,
        requested_by: str,
        action: str,
        target: str,
        risk_level: str,
        reason: str,
        arguments: dict[str, Any] | None = None,
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
            expires_at=(now + timedelta(minutes=self.ttl_minutes)).isoformat(),
            status=ApprovalStatus.PENDING.value,
            arguments=arguments or {},
        )
        self._append(record)
        return record

    def set_status(self, approval_id: str, status: str) -> ApprovalRecord:
        if status not in {ApprovalStatus.APPROVED.value, ApprovalStatus.DENIED.value}:
            raise ValueError(f"Unsupported approval status: {status}")
        record = self.get_latest(approval_id)
        if record is None:
            raise KeyError(f"Approval not found: {approval_id}")
        updated = replace(record, status=status)
        self._append(updated)
        return updated

    def get_latest(self, approval_id: str) -> ApprovalRecord | None:
        latest: ApprovalRecord | None = None
        for record in self._load():
            if record.approval_id == approval_id:
                latest = record
        return latest

    def pending(self) -> list[ApprovalRecord]:
        now = datetime.now(timezone.utc)
        return [
            record
            for record in self._latest_by_id().values()
            if record.status == ApprovalStatus.PENDING.value and self._parse_time(record.expires_at) > now
        ]

    def is_approved_for(self, approval_id: str, action: str, target: str | None = None) -> bool:
        record = self.get_latest(approval_id)
        if record is None or record.status != ApprovalStatus.APPROVED.value:
            return False
        if self._parse_time(record.expires_at) <= datetime.now(timezone.utc):
            return False
        if record.action != action:
            return False
        return target is None or record.target == target

    def _latest_by_id(self) -> dict[str, ApprovalRecord]:
        latest: dict[str, ApprovalRecord] = {}
        for record in self._load():
            latest[record.approval_id] = record
        return latest

    def _append(self, record: ApprovalRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def _load(self) -> list[ApprovalRecord]:
        if not self.path.exists():
            return []
        records: list[ApprovalRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            records.append(ApprovalRecord(**payload))
        return records

    def _parse_time(self, value: str) -> datetime:
        return datetime.fromisoformat(value)
