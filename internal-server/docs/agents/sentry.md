# Sentry — Observer

> *"Never fabricate samples."*

Sentry is the last agent in the pipeline and the only one with
autonomous **rollback authority**. It watches the candidate stack for a
bounded window and either recommends `promote`, holds, or rolls back
directly.

**Source:** `src/agent/team/sentry.py`

## Role in the pipeline

Invoked by Axiom via `handoff_to_sentry(task_spec)` after Vector has
brought up the candidate color. Sentry:

1. Calls `watch` for the agreed window (default 60s at 5s intervals).
2. If the recommendation is `rollback`, calls `trigger_rollback` **directly
   — it does not re-prompt Axiom**.
3. If `promote`, returns a summary; Axiom finalises via
   `update_team_state`.
4. If `hold`, keeps watching or reports inconclusive.

## System prompt (summary)

Full text in `SENTRY_SYSTEM_PROMPT` (`sentry.py:19`). Hard rules:

- Never fabricate samples. The recommendation is a deterministic function
  of actual observations.
- Has rollback authority and should use it without asking Axiom when
  samples trip the threshold.

## Tools

| Tool                | Signature                                                                            | Effect                                                                   |
| ------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `poll_services`     | `(color: str \| None) -> dict`                                                       | Snapshot of compose services for the current or named color              |
| `http_probe`        | `(url: str, timeout_s: int = 5) -> dict`                                             | One-shot HTTP probe with status code, latency, body preview               |
| `watch`             | `(window_s: int = 60, interval_s: int = 5, healthcheck_url: str \| None, color: str \| None) -> dict` | Sampled health watch; returns `recommendation` and `unhealthy_streak`    |
| `trigger_rollback`  | `(reason: str) -> dict`                                                              | Tear candidate → restore previous active → PagerDuty (stub) → status=`rolled_back` |

`watch` is the core tool. It delegates to `src/tooling/health.py::watch`,
which collects samples of container state + optional HTTP probe and
returns a recommendation:

| `recommendation` | meaning                                    |
| ---------------- | ------------------------------------------ |
| `promote`        | Samples look clean for the full window     |
| `rollback`       | Unhealthy streak crossed the threshold     |
| `hold`           | Inconclusive; caller should decide         |

## State it mutates

| Field                      | Via                                 |
| -------------------------- | ----------------------------------- |
| `health_samples`           | `watch` (extends the list)          |
| `status`                   | `watch → watching`, `trigger_rollback → rolled_back` |
| `rollout.active_color`     | `trigger_rollback` (restores previous) |
| `rollout.candidate_color`  | `trigger_rollback` (clears)          |
| `rollout.rolled_back`      | `trigger_rollback`                   |
| `notes`                    | via every status transition          |

## Rollback flow

```python
candidate = team.rollout.candidate_color
if candidate:
    rollout_tools.teardown(service, project_path, color=candidate)
previous = team.rollout.active_color if active != "none" else "blue"
team.rollout.active_color = previous
team.rollout.candidate_color = None
team.rollout.rolled_back = True
team.set_status(TeamRunStatus.rolled_back, note=f"Sentry rolled back: {reason}")
_pagerduty_trigger(summary=f"Rollback: {reason}", severity="error")
```

PagerDuty goes through the `NullAdapter` stub in MVP — the call is
audited but nothing pages.

## Failure modes

- **No candidate to rollback to.** `trigger_rollback` defaults `previous`
  to `"blue"` if nothing was ever active. This is a crude fallback; in
  production we'd refuse and mark the run failed instead.
- **HTTP probe timeout.** Captured in the sample; contributes to the
  `unhealthy_streak` counter.
- **Docker daemon unavailable.** `poll_services` surfaces the error in
  the snapshot. Sentry should treat this as an unhealthy sample.

## Configuration

- **Model.** Inherits from credentials via `build_team(peer_model=...)`.
- **Tool-call budget.** 24 by default.
- **Default watch window.** 60s / 5s interval. Tunable per call.
