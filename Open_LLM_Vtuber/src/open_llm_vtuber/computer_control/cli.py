from __future__ import annotations

import argparse
import json
import re
import sys

from .approvals import ApprovalStore
from .bridge import ComputerControlBridge


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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

    try:
        payload = _handle_command(args)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "error", "message": f"Invalid arguments JSON: {exc}"}, ensure_ascii=True))
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "message": str(exc), "error_class": exc.__class__.__name__},
                ensure_ascii=True,
            )
        )
        return 1

    print(json.dumps(payload, ensure_ascii=True))
    return 0


def _handle_command(args: argparse.Namespace) -> dict:
    if args.command == "preflight":
        return ComputerControlBridge().preflight()

    if args.command == "execute":
        arguments = _load_arguments(args.arguments_json)
        result = ComputerControlBridge().execute(args.action, arguments, requested_by=args.requested_by)
        return result.to_dict()

    store = ApprovalStore()
    if args.command == "approval-status":
        return {"pending": [record.__dict__ for record in store.pending()]}

    if args.command == "approve":
        return store.set_status(args.approval_id, "approved").__dict__

    if args.command == "deny":
        return store.set_status(args.approval_id, "denied").__dict__

    raise ValueError(f"Unsupported command: {args.command}")


def _load_arguments(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        loose = _parse_loose_arguments(raw or "")
        if loose is None:
            raise exc
        return loose


def _parse_loose_arguments(raw: str) -> dict | None:
    text = raw.strip()
    if not text.startswith("{") or not text.endswith("}"):
        return None

    body = text[1:-1].strip()
    if not body:
        return {}

    parsed = {}
    for pair in _split_loose_pairs(body):
        key, separator, value = pair.partition(":")
        if not separator:
            return None
        key = key.strip().strip("\"'")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            return None
        parsed[key] = _coerce_loose_value(value.strip())
    return parsed


def _split_loose_pairs(body: str) -> list[str]:
    pairs = []
    current = []
    quote = None
    escape = False
    for character in body:
        if escape:
            current.append(character)
            escape = False
            continue
        if character == "\\":
            current.append(character)
            escape = True
            continue
        if quote:
            current.append(character)
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            current.append(character)
            quote = character
            continue
        if character == ",":
            pairs.append("".join(current).strip())
            current = []
            continue
        current.append(character)
    pairs.append("".join(current).strip())
    return pairs


def _coerce_loose_value(value: str) -> object:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]

    lowered = cleaned.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        return float(cleaned)
    return cleaned


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
