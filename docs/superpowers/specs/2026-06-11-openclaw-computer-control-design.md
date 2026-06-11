# OpenClaw Computer Control Design

## Context

The project is `D:\ChatWithSmallC`, with Open LLM Vtuber as the interaction layer and Letta as the active conversation agent. The current `conf.yaml` uses `conversation_agent_choice: letta_agent`, so the first version must preserve the Letta architecture instead of switching to `basic_memory_agent`.

The repo already contains an MCP client stack under `Open_LLM_Vtuber/src/open_llm_vtuber/mcpp`, but that stack is currently wired for `basic_memory_agent`. It is useful as a future integration pattern, not the shortest first path for the active Letta agent.

The local machine has an `openclaw` command installed, and `C:\Users\sword\AppData\Roaming\clawhub\config.json` exists. The active shell uses Node `v20.19.2`, while `openclaw` requires Node `v22.12+`. `nvm list` shows Node `22.22.1` and `24.14.0` are already installed, so this should be treated as a runtime selection/preflight issue, not as a project dependency to vendor.

OpenClaw official docs describe Browser as a managed Chromium tool with actions for navigation, tabs, screenshots, PDF generation, selectors, clicks, typing, key presses, wait operations, and optional local loopback API control. The docs also warn that browser profiles and JS evaluation can expose sensitive data, so the integration must default to a restricted profile and approval gates.

## User-Confirmed Boundaries

- Prefer OpenClaw existing tools over a custom Playwright implementation.
- First version focuses on browser control, approval, and audit logging.
- Full desktop GUI control is not enabled by default.
- File operations are limited to `D:\ChatWithSmallC` and directories manually authorized by the user.
- Shell commands use an allowlist plus high-risk approval.
- Later phases may add broader file control, shell control, Windows desktop GUI, multi-step task orchestration, and richer UI status.

## Options Considered

### Option A: Switch to `basic_memory_agent` and use existing MCP directly

This reuses the existing `mcpp` stack with minimal new infrastructure. It is not recommended for the first version because it drops the current Letta memory architecture and would move the real LLM path away from the already configured DeepSeek v4 Letta agent.

### Option B: Register OpenClaw tools directly inside Letta

This keeps Letta as the decision maker and exposes browser control as Letta tools. It is attractive, but raw tool functions inside Letta are a poor place for policy enforcement, audit persistence, OpenClaw runtime preflight, and future reuse by MCP or UI routes.

### Option C: OpenClaw safety bridge plus Letta tool registration

This is the recommended approach. Add a local `computer_control` bridge owned by this repo. The bridge is the only component allowed to invoke OpenClaw. It enforces policy, writes audit logs, provides preflight diagnostics, and exposes a stable API. A small Letta tool forwards approved requests to the bridge. Later, the same bridge can also be wrapped as an MCP server for `basic_memory_agent` or other agents.

## Recommended Architecture

```text
User voice/text
  -> Open_LLM_Vtuber
  -> Letta agent
  -> Letta tool: computer_control
  -> Local Computer Control Bridge
  -> OpenClaw Browser / future OpenClaw Windows Hub
  -> Browser state, screenshot, page text, result summary
```

The bridge owns all execution policy. Letta can propose an action, but the bridge decides whether it is allowed, denied, or requires approval.

## Components

### Computer Control Bridge

Create a small local service or stdio tool runner under `Open_LLM_Vtuber/src/open_llm_vtuber/computer_control`. It provides:

- `preflight`: checks Node version, `openclaw` availability, OpenClaw profile status, and whether Browser control is reachable.
- `browser_open`: opens a URL in the OpenClaw browser profile.
- `browser_snapshot`: returns visible page summary and metadata.
- `browser_screenshot`: captures a screenshot and returns a local path.
- `browser_click`: clicks a selector or coordinate after policy checks.
- `browser_type`: types text into a selector after policy checks.
- `browser_wait`: waits for navigation, selector, or timeout.
- `approval_status`: reports pending approval requests.

The bridge should prefer OpenClaw Browser commands/API. It may use Playwright only as an internal fallback when OpenClaw is unavailable, and that fallback must be clearly reported in preflight and logs.

### Policy Engine

Policy is a small deterministic layer, not an LLM judgment. It classifies actions:

- `allow`: read-only browser state, screenshot, open non-sensitive URL, wait.
- `approval_required`: form submit, checkout/payment, email/post/comment send, login submission, downloads, file writes, shell commands, cross-site credential actions.
- `deny`: destructive file operations outside allowed roots, silent credential extraction, arbitrary JS execution against authenticated sites, background desktop control, unapproved shell commands.

The first implementation should include the policy in code and make the reasons visible in tool results and audit logs.

### Approval Store

Approval is represented as a pending request record. First version can use a JSONL file and CLI/log-based confirmation; later versions can surface it in the web UI.

Pending approval fields:

- `approval_id`
- `created_at`
- `requested_by`
- `action`
- `target`
- `risk_level`
- `reason`
- `expires_at`
- `status`

No action that requires approval is executed until the approval status is explicitly accepted.

### Audit Log

Write JSONL audit entries under `.run_logs/computer_control/audit.jsonl`, which is ignored by Git.

Each entry contains:

- timestamp
- request id
- tool/action name
- policy decision
- sanitized arguments
- result status
- output summary
- screenshot path if generated
- error class and message if failed

The audit log must not store API keys, cookies, passwords, full page HTML from authenticated sessions, or raw user secrets.

### Letta Integration

Register a Letta tool named `computer_control` or a small family of browser tools that call the local bridge. The tool description must tell the agent:

- use browser tools only when the user asks for computer/browser operation;
- explain the intended action before high-risk actions;
- when a tool returns `approval_required`, ask the user to approve instead of retrying;
- never attempt credential extraction or hidden background operation.

Tool installation should be scripted so local Letta state can be restored without committing the Letta SQLite database.

## Data Flow

1. User asks小C to do a browser task.
2. Letta decides whether a browser tool is needed.
3. Letta calls `computer_control` with an action and arguments.
4. Bridge performs policy classification.
5. If allowed, bridge invokes OpenClaw and returns a concise result.
6. If approval is needed, bridge records a pending approval and returns an approval prompt.
7. Open LLM Vtuber speaks the result or asks for approval.
8. Audit log records the sanitized event.

## Error Handling

- If Node is below `22.12`, preflight fails with a clear remediation: switch to Node `22.22.1` or `24.14.0` through `nvm`.
- If OpenClaw Browser is not available, the bridge returns `unavailable` and does not silently fall back unless fallback mode is explicitly enabled.
- If a selector is missing, browser tools return an actionable message and a fresh snapshot or screenshot path.
- If an action is blocked by policy, the bridge returns `denied` with the policy reason.
- If an approval expires, the bridge requires a new request.

## Testing Strategy

First version tests should cover policy and audit logic without requiring OpenClaw:

- read-only browser actions are allowed;
- submit/send/payment actions require approval;
- file and shell actions are denied unless explicitly allowlisted;
- audit events redact sensitive fields;
- approval-required actions are not executed.

Integration smoke tests should run only when OpenClaw preflight passes:

- Node/OpenClaw preflight reports ready;
- open a safe URL;
- take a screenshot;
- get a page snapshot;
- attempt a risky action and verify `approval_required`.

## First-Version Acceptance Criteria

- The project has a documented OpenClaw-first computer control design.
- Preflight can detect the current Node/OpenClaw state without leaking secrets.
- Browser actions are reachable through the bridge when OpenClaw is ready.
- Letta has a scripted way to call the bridge as a tool.
- High-risk actions produce `approval_required` and do not execute.
- Audit logs are written under ignored `.run_logs`.
- No API keys, cookies, browser profile contents, or Letta database files are committed.

## Deferred Work

- Native web UI approval modal.
- Full Windows desktop GUI control through OpenClaw Windows Hub.
- Shell command execution beyond strict allowlists.
- File write tools outside approved roots.
- Multi-step planner with retry/recovery state.
- MCP wrapper for non-Letta agents.

