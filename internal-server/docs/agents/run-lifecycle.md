# Run Lifecycle & Approvals

This doc traces a single team run from HTTP request to terminal state,
including the pause/resume path for approval gates.

**Source:**
`src/agent/team/runs.py`, `src/agent/team/executor.py`,
`src/api/routes/team.py`.

## Components

| Component        | Responsibility                                                 |
| ---------------- | -------------------------------------------------------------- |
| `TeamRunStore`   | In-memory registry of `TeamRun` objects; records events + approvals |
| `TeamRun`        | One run: `run_id`, `TeamContext`, event log, `asyncio.Task`    |
| `TeamEvent`      | `{event, run_id, timestamp, payload}`; also flushed to `~/.devops/agent.log` |
| `TeamExecutor`   | Builds the team, runs Axiom, handles pause/resume              |
| `/team/*` routes | HTTP layer                                                     |

## Happy path

```
POST /team/runs
  └─ TeamRunStore.create(task, project_path)
      └─ TeamEvent("team_run_created")
  └─ execute_in_background(executor, run)
      └─ TeamExecutor.drive(run)
          └─ TeamEvent("team_run_started")
          └─ build_team()                       # Axiom + 4 handoff tools
          └─ GeminiRunner.run(axiom, prompt, context=run.context)
              └─ Axiom calls handoff_to_forge(...)      # Forge sub-run
              └─ Axiom calls handoff_to_warden(...)     # Warden sub-run; approve
              └─ Axiom calls handoff_to_vector(...)     # Vector sub-run
              └─ Axiom calls handoff_to_sentry(...)     # Sentry sub-run; promote
              └─ Axiom returns final summary
          └─ TeamEvent("team_run_finished", {status: "succeeded", ...})
          └─ If status still non-terminal → set_status(succeeded)
```

Terminal status: `succeeded`.

## Blocking path

```
... as above through handoff_to_warden ...
  Warden calls block_or_approve()
    └─ has_blocking_findings() == True
    └─ team.set_status(waiting_for_approval)
    └─ team.blocking_reason = "Warden found N blocking finding(s)..."
  Handoff returns with finish_reason="paused", paused_gate="pre_deploy"
  Axiom sees paused result → does NOT call handoff_to_vector
  Axiom returns final summary describing the block
TeamExecutor.drive returns
  └─ run.context.status == waiting_for_approval  (not promoted)
  └─ HTTP layer returns 202 with the run summary
```

At this point the caller does one of:

**Approve:**

```
POST /team/runs/{id}/approve  {"gate":"pre_deploy"}
  └─ TeamRunStore.record_approval(run_id, "pre_deploy", approved=True)
      └─ team.set_status(deploying, note="gate 'pre_deploy' approved")
      └─ TeamEvent("team_approval", {gate, approved: true})
  └─ execute_in_background(executor.resume, run)
      └─ TeamExecutor.resume(run)
          └─ TeamEvent("team_run_resumed")
          └─ Axiom restarts with a resume-prompt that lists approved/rejected gates
          └─ Axiom calls handoff_to_vector(...), handoff_to_sentry(...)
          └─ Normal completion → succeeded
```

**Reject:**

```
POST /team/runs/{id}/reject  {"gate":"pre_deploy","reason":"..."}
  └─ TeamRunStore.record_approval(run_id, "pre_deploy", approved=False, reason=...)
      └─ team.set_status(failed, note="gate 'pre_deploy' rejected: ...")
      └─ team.blocking_reason = reason
      └─ TeamEvent("team_approval", {approved: false})
  └─ No resume; run is terminal.
```

## Rollback path

Sentry autonomously rolls back during its watch:

```
Axiom → handoff_to_sentry → Sentry.watch → recommendation="rollback"
  └─ Sentry calls trigger_rollback(reason)
      └─ rollout_tools.teardown(candidate)
      └─ team.rollout.active_color = previous
      └─ team.rollout.rolled_back = True
      └─ team.set_status(rolled_back, note=f"Sentry rolled back: {reason}")
      └─ pagerduty_trigger(...)   # stub
  Handoff returns normally
Axiom sees terminal status → final summary
TeamEvent("team_run_finished", {status: "rolled_back"})
```

## Event log

Every state change is recorded twice:

1. In-memory on `run.events` (visible via `GET /team/runs/{id}/events`
   and `team events <id>`).
2. JSONL-appended to `~/.devops/agent.log` via `AuditLogger`.

Event types:

- `team_run_created`
- `team_run_started`
- `team_run_finished`
- `team_run_failed`
- `team_run_resumed`
- `team_approval`

Each event carries a `run_id`, timestamp, and event-specific payload.

## HTTP surface

| Method | Path                              | Body                                           | Returns              |
| ------ | --------------------------------- | ---------------------------------------------- | -------------------- |
| POST   | `/team/runs`                      | `{task, project_path, user_id?}`                | `run_id`, initial summary |
| GET    | `/team/runs`                      | —                                              | list of summaries    |
| GET    | `/team/runs/{id}`                 | —                                              | summary              |
| GET    | `/team/runs/{id}/events`          | —                                              | event log            |
| POST   | `/team/runs/{id}/approve`         | `{gate, reason?}`                               | updated summary      |
| POST   | `/team/runs/{id}/reject`          | `{gate, reason?}`                               | updated summary      |

## CLI surface

```bash
python -m src.cli team run     --path ./repo --task "ship the thing"
python -m src.cli team status  <run-id>
python -m src.cli team events  <run-id>
python -m src.cli team approve <run-id> --gate pre_deploy
python -m src.cli team reject  <run-id> --gate pre_deploy --reason "needs review"
```

## Persistence

None beyond the audit log. `TeamRunStore` is process-memory — if the
FastAPI server restarts, in-flight runs are lost. Terminal runs can be
reconstructed from `~/.devops/agent.log` but that's manual work today.
