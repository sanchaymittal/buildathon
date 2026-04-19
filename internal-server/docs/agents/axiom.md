# Axiom — Orchestrator

> *"You do not write code. You call tools."*

Axiom is the only agent that sees the whole pipeline. It receives the
user's task, decomposes it into Forge → Warden → Vector → Sentry handoffs,
maintains the shared `TeamContext`, and pauses the run when an approval
gate is hit.

**Source:** `src/agent/team/orchestrator.py`

## Role in the pipeline

1. Receive a task spec and project path (from `TeamExecutor._axiom_prompt`).
2. Delegate engineering to **Forge** via `handoff_to_forge`.
3. Delegate security review to **Warden** via `handoff_to_warden`.
4. If Warden records any finding with severity ≥ `high`, stop and call
   `request_approval("pre_deploy")`. **Do not deploy** until the HTTP layer
   records an approval and `TeamExecutor.resume` fires.
5. Delegate the rollout to **Vector** via `handoff_to_vector`.
6. Delegate the watch window to **Sentry** via `handoff_to_sentry`.
7. Emit a concise structured summary as the final reply.

## System prompt (summary)

Full text lives in `AXIOM_SYSTEM_PROMPT` (`orchestrator.py:18`). Key
constraints:

- Axiom **never** writes code. Only tool calls.
- Axiom **never** deploys or rolls back directly.
- Axiom **may** update team state via `update_team_state`.
- Axiom **may** post to Linear / Slack / GitHub (stubs in MVP).
- When blocking findings appear, call `request_approval` **before** any
  further handoff.

## Tools

| Tool                      | Signature                                                      | Purpose                                   |
| ------------------------- | -------------------------------------------------------------- | ----------------------------------------- |
| `update_team_state`       | `(status: str \| None, note: str \| None) -> dict`             | Flip `TeamRunStatus` and/or append a note |
| `request_approval`        | `(gate: str, reason: str \| None) -> dict`                     | Pause the run at the named gate           |
| `linear_create_issue`     | `(title: str, body: str, team: str \| None) -> dict`           | Create a Linear issue (stub)              |
| `slack_post`              | `(channel: str, message: str) -> dict`                         | Post to Slack (stub)                      |
| `github_comment`          | `(pr_ref: str, body: str) -> dict`                             | Comment on a GitHub PR (stub)             |
| `handoff_to_forge`        | `(task_spec: str) -> HandoffResult`                            | Spawn Forge sub-run                       |
| `handoff_to_warden`       | `(task_spec: str) -> HandoffResult`                            | Spawn Warden sub-run                      |
| `handoff_to_vector`       | `(task_spec: str) -> HandoffResult`                            | Spawn Vector sub-run                      |
| `handoff_to_sentry`       | `(task_spec: str) -> HandoffResult`                            | Spawn Sentry sub-run                      |

The four `handoff_to_*` tools are added by `build_team()` via
`handoff_tool()` (see [handoff.md](./handoff.md)). The rest are defined
inline in `orchestrator.py`.

## State it mutates

| Field                     | Via                                   |
| ------------------------- | ------------------------------------- |
| `status`                  | `update_team_state`, `request_approval` |
| `notes`                   | `update_team_state`, `request_approval` |
| `blocking_reason`         | `request_approval`                      |
| `approvals` (read)        | —                                       |

Axiom does not touch `findings`, `rollout`, `commit_sha`, or
`health_samples` directly — those are owned by the peer agents.

## Failure modes

- **Peer crashes.** The `HandoffResult` carries `finish_reason` and the
  full tool-call trace; Axiom should surface it in the final summary and
  set the status to `failed` via `update_team_state`.
- **Peer pauses.** `HandoffResult.finish_reason == "paused"` — Axiom must
  stop delegating. The executor unwinds to the HTTP layer.
- **Rate-limited by Gemini.** Gemini errors bubble up through the runner.
  The run is marked `failed` with a `team_run_failed` event.

## Configuration

- **Model.** Inherits from `CredentialManager.get_gemini_credentials().model`
  (default `gemini-2.5-flash`). Overridable via
  `build_team(orchestrator_model=...)`.
- **Tool-call budget.** 16 by default (see `GeminiRunner(max_tool_calls=16)`).
  Counts handoffs as single calls regardless of how many sub-tool-calls
  Forge / Warden / Vector / Sentry make internally.
