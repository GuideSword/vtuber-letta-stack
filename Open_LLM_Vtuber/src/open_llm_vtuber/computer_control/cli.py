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

    try:
        payload = _handle_command(args)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "error", "message": f"Invalid arguments JSON: {exc}"}, ensure_ascii=False))
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "message": str(exc), "error_class": exc.__class__.__name__},
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _handle_command(args: argparse.Namespace) -> dict:
    if args.command == "preflight":
        return ComputerControlBridge().preflight()

    if args.command == "execute":
        arguments = json.loads(args.arguments_json)
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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
