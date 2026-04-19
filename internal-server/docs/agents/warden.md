# Warden — Security Engineer

> *"Never invent findings. Never rewrite severities."*

Warden runs SAST, secrets, and dependency scanners on the current project
and makes a **deterministic** block/approve decision based on the
findings. Warden does not argue: severity ≥ `high` blocks the run and
requests an approval gate.

**Source:** `src/agent/team/warden.py`

## Role in the pipeline

Invoked by Axiom via `handoff_to_warden(task_spec)` after Forge has
pushed a commit. Warden:

1. Runs `run_semgrep`, `run_gitleaks`, `run_trivy` (order-insensitive).
2. Calls `record_findings` to merge scanner JSON into `TeamContext.findings`.
3. Calls `block_or_approve` — the final verdict.

## System prompt (summary)

Full text in `WARDEN_SYSTEM_PROMPT` (`warden.py:15`). Hard rules:

- Trust the scanners. No fabrication, no severity rewriting.
- The final decision is a pure function of `TeamContext.findings`.

## Tools

| Tool                | Signature                                   | Purpose                                              |
| ------------------- | ------------------------------------------- | ---------------------------------------------------- |
| `run_semgrep`       | `() -> dict`                                 | Runs semgrep (or the deterministic stub)             |
| `run_trivy`         | `() -> dict`                                 | Runs trivy (or the deterministic stub)               |
| `run_gitleaks`      | `() -> dict`                                 | Runs gitleaks (or the deterministic stub)            |
| `record_findings`   | `(findings: list[dict]) -> dict`             | Validates and merges findings into `TeamContext`     |
| `block_or_approve`  | `() -> dict`                                 | Deterministic verdict based on current findings      |

All three scanners return `{scanner, findings: [...], summary: {...}}`.
The scanners live in `src/tooling/scanners.py` and fall back to
deterministic stubs when the real binaries aren't on PATH — good for
CI, tests, and airgapped demos.

## The `block_or_approve` contract

```python
if team.has_blocking_findings():   # any finding severity in {high, critical}
    team.blocking_reason = f"Warden found N blocking finding(s); highest={...}"
    team.set_status(TeamRunStatus.waiting_for_approval, ...)
    return {"decision": "block", "gate": "pre_deploy", ...}
else:
    team.set_status(TeamRunStatus.security_review, ...)
    return {"decision": "approve", ...}
```

Severity ranking (`context.py:38`):

| severity   | rank | blocking? |
| ---------- | ---- | --------- |
| `critical` | 4    | yes       |
| `high`     | 3    | yes       |
| `medium`   | 2    | no        |
| `low`      | 1    | no        |
| `info`     | 0    | no        |

## State it mutates

| Field              | Via                                |
| ------------------ | ---------------------------------- |
| `findings`         | `record_findings`                   |
| `status`           | `block_or_approve` → `waiting_for_approval` or `security_review` |
| `blocking_reason`  | `block_or_approve` (when blocking)  |
| `notes`            | `block_or_approve` (both branches)  |
| `notes`            | `record_findings` (on malformed input) |

## SecurityFinding schema

```python
class SecurityFinding(BaseModel):
    scanner: Literal["semgrep", "trivy", "gitleaks", "stub"]
    severity: Literal["info", "low", "medium", "high", "critical"]
    title: str
    file:   Optional[str] = None
    line:   Optional[int] = None
    details: Optional[str] = None
```

Malformed findings are dropped with a note on the team context — they
never silently fail.

## Failure modes

- **Scanner binary missing.** Returns stubbed findings; the run continues.
  The scanner type is recorded as `stub` so downstream consumers can tell.
- **Malformed finding from an LLM.** Dropped; a note is appended to
  `team.notes` so operators can see what was skipped.
- **Warden skips `block_or_approve`.** The executor does not auto-promote
  to `deploying` — Axiom will either re-delegate or the run will end at
  `security_review` status. Production would want a guardrail here; for
  MVP this is an acceptable loose contract.

## Configuration

- **Model.** Inherits from credentials via `build_team(peer_model=...)`.
- **Tool-call budget.** 24 by default when spawned via `handoff_tool`.
