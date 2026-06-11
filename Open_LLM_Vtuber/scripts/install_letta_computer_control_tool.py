from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


TOOL_NAME = "computer_control"
TOOL_DESCRIPTION = (
    "Safely request local OpenClaw-first browser/computer control through "
    "ChatWithSmallC policy, approval, and audit layers."
)


def build_tool_source(python_exe: str, project_root: str) -> str:
    source_path = str(Path(project_root) / "src")
    return f'''
def computer_control(
    action: str,
    arguments_json: str = "{{}}",
    url: str = "",
    ref: str = "",
    text: str = "",
    path: str = "",
    output_path: str = "",
    seconds: int = 0,
    purpose: str = "",
    approval_id: str = "",
) -> str:
    """
    Safely request a local computer-control action through the ChatWithSmallC bridge.

    Supported first-version actions: preflight, approval_status, browser_open,
    browser_snapshot, browser_screenshot, browser_click, browser_type, browser_wait.
    Prefer explicit fields such as url, ref, text, path, and seconds over
    hand-written JSON. For click/type, prefer OpenClaw snapshot refs. If the result says
    approval_required, ask the user for approval instead of retrying.
    Never use this to extract credentials, cookies, tokens, or hidden browser state.
    """
    import json
    import os
    import subprocess

    explicit_arguments = {{}}
    for key, value in {{
        "url": url,
        "ref": ref,
        "text": text,
        "path": path,
        "output_path": output_path,
        "seconds": seconds,
        "purpose": purpose,
        "approval_id": approval_id,
    }}.items():
        if value not in (None, "", 0):
            explicit_arguments[key] = value

    command_arguments_json = arguments_json or "{{}}"
    if explicit_arguments:
        try:
            parsed_arguments = json.loads(command_arguments_json) if command_arguments_json else {{}}
        except Exception:
            parsed_arguments = {{}}
        parsed_arguments.update(explicit_arguments)
        command_arguments_json = json.dumps(parsed_arguments, ensure_ascii=False)

    env = dict(os.environ)
    env["PYTHONPATH"] = r"{source_path}" + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [
            r"{python_exe}",
            "-m",
            "open_llm_vtuber.computer_control.cli",
            "execute",
            action,
            "--arguments-json",
            command_arguments_json,
            "--requested-by",
            "letta",
        ],
        cwd=r"{project_root}",
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        return json.dumps(
            {{"status": "error", "message": result.stderr[-1000:] or result.stdout[-1000:]}},
            ensure_ascii=False,
        )
    return result.stdout
'''


def tool_payload(source_code: str) -> dict:
    return {
        "source_code": source_code,
        "source_type": "python",
        "description": TOOL_DESCRIPTION,
        "tags": ["chatwithsmallc", "computer_control", "openclaw"],
        "json_schema": {
            "name": TOOL_NAME,
            "description": TOOL_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": (
                            "Action to run. First-version actions are preflight, approval_status, "
                            "browser_open, browser_snapshot, browser_screenshot, browser_click, "
                            "browser_type, and browser_wait."
                        ),
                    },
                    "arguments_json": {
                        "type": "string",
                        "description": "Optional JSON object string with action arguments. Prefer explicit fields when possible.",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL for browser_open. Must be http or https.",
                    },
                    "ref": {
                        "type": "string",
                        "description": "OpenClaw snapshot ref for browser_click or browser_type.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type for browser_type.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Requested local destination path for browser_screenshot.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Alias for path when saving a browser_screenshot.",
                    },
                    "seconds": {
                        "type": "integer",
                        "description": "Seconds for browser_wait.",
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Short reason for risky actions such as payment, login, or submission.",
                    },
                    "approval_id": {
                        "type": "string",
                        "description": "Approval id supplied after the user approves a risky action.",
                    },
                },
                "required": ["action"],
            },
        },
        "return_char_limit": 6000,
    }


def upsert_tool(base_url: str, source_code: str) -> dict:
    response = requests.put(
        f"{base_url.rstrip('/')}/v1/tools/",
        json=tool_payload(source_code),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def attach_tool(base_url: str, agent_id: str, tool_id: str) -> None:
    response = requests.patch(
        f"{base_url.rstrip('/')}/v1/agents/{agent_id}/tools/attach/{tool_id}",
        timeout=30,
    )
    if response.status_code in {200, 201, 204, 409}:
        return
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
