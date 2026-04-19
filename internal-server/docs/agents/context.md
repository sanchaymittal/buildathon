# `TeamContext` — Shared State

Every tool call across every agent in a team run sees **the same**
`TeamContext` instance, threaded through via Gemini's
`RunContextWrapper`. Mutations happen only inside declared tools, so the
full trajectory of a run is auditable.

**Source:** `src/agent/team/context.py`

## Schema

```python
class TeamContext(BaseModel):
    # identity
    run_id: str
    user_id: str = "anonymous"
    task: str
    project_path: str

    # engineering outputs
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    pr_ref: Optional[str] = None

    # security outputs
    findings: List[SecurityFinding] = []

    # deploy / watch outputs
    rollout: RolloutState = RolloutState()
    health_samples: List[dict] = []

    # orchestration
    status: TeamRunStatus = TeamRunStatus.planning
    approvals: Dict[str, bool] = {}
    blocking_reason: Optional[str] = None
    notes: List[str] = []

    created_at: float
    updated_at: float
```

## `TeamRunStatus`

```
planning
  └─ engineering  (Forge recorded a commit)
      └─ security_review     (Warden approved)
      └─ waiting_for_approval (Warden blocked ↑  OR  Axiom requested gate)
          └─ deploying       (gate approved → Vector)
              └─ watching    (Vector promoted → Sentry)
                  ├─ succeeded
                  ├─ rolled_back
                  └─ failed
```

`.is_terminal` returns `True` for `succeeded`, `rolled_back`, `failed`.

## Ownership of mutations

| Field                        | Owner          | Tool(s)                                       |
| ---------------------------- | -------------- | --------------------------------------------- |
| `status`, `notes`            | Axiom + peers  | `update_team_state`, `set_status` transitions |
| `blocking_reason`            | Axiom, Warden  | `request_approval`, `block_or_approve`        |
| `branch`, `commit_sha`       | Forge          | `create_branch`, `commit_all`, `record_commit` |
| `findings`                   | Warden         | `record_findings`                              |
| `rollout.*`                  | Vector, Sentry | `build_image`, `rollout_bluegreen`, `switch_active`, `rollback_to`, `trigger_rollback` |
| `health_samples`             | Sentry         | `watch`                                        |
| `approvals`                  | `TeamRunStore` | `record_approval` (HTTP layer)                 |

## Helpers

```python
team.set_status(TeamRunStatus.deploying, note="...")
team.add_note("free-form note")
team.record_finding(finding)
team.record_findings([f1, f2, ...])
team.has_blocking_findings()      # any severity >= high
team.highest_severity()           # "critical" | "high" | ... | None
team.summary()                    # serialisable dict for HTTP/CLI
```

## `SecurityFinding`

See [warden.md](./warden.md#securityfinding-schema).

## `RolloutState`

```python
class RolloutState(BaseModel):
    active_color:    Literal["blue", "green", "none"] = "none"
    candidate_color: Optional[Literal["blue", "green"]] = None
    image_tag:       Optional[str] = None
    project_base:    Optional[str] = None
    rolled_back:     bool = False

    def next_candidate_color(self) -> "blue" | "green":
        return "green" if self.active_color == "blue" else "blue"
```

## Why a single shared context?

- **Auditable.** Every mutation is a tool call; every tool call is logged
  to `~/.devops/agent.log`.
- **Deterministic gates.** `Warden.block_or_approve` and
  `Sentry.watch` / `trigger_rollback` make their decisions from fields
  any component can inspect.
- **Resumable pauses.** When Axiom calls `request_approval`, the HTTP
  layer stores `approvals[gate] = True/False` and `TeamExecutor.resume`
  reads it back — no out-of-band channel needed.
