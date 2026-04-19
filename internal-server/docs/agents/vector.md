# Vector — Deployer

> *"Rollback is only called by Sentry or on an explicit human instruction."*

Vector owns the deploy window. It builds the image, pushes it (stub in
MVP), rolls out blue/green on the local Docker daemon, and promotes the
candidate once Sentry signs off.

**Source:** `src/agent/team/vector.py`

## Role in the pipeline

Invoked by Axiom via `handoff_to_vector(task_spec)` **only after** any
`waiting_for_approval` state has been resumed. Vector:

1. Builds the candidate image (`build_image`).
2. Pushes to a registry (`push_image` — stub).
3. Brings up `<project_base>-<candidate_color>` via compose
   (`rollout_bluegreen`).
4. Waits for Sentry's watch window.
5. Promotes (`switch_active`) and tears down the previous color
   (`teardown_color`).

The blue/green project naming convention is handled by
`src/tooling/rollout.py::project_name_for` — `<basename>-<sha1[:6]>-<color>`.

## System prompt (summary)

Full text in `VECTOR_SYSTEM_PROMPT` (`vector.py:16`). Hard rules:

- Do not `switch_active` before the run resumes from `waiting_for_approval`.
- Do not invoke `rollback_to` autonomously — that's Sentry's authority.

## Tools

| Tool                 | Signature                                              | Effect                                       |
| -------------------- | ------------------------------------------------------ | -------------------------------------------- |
| `build_image`        | `(tag: str \| None) -> dict`                           | Records `image_tag` and `project_base` on context |
| `push_image`         | `(registry: str \| None) -> dict`                      | Stub; records an audit note                  |
| `rollout_bluegreen`  | `(color: "blue" \| "green" \| None) -> dict`          | `docker compose up -d` under `<base>-<color>` |
| `switch_active`      | `(color: "blue" \| "green") -> dict`                   | Promote candidate; flip status to `watching` |
| `teardown_color`     | `(color: "blue" \| "green") -> dict`                   | `docker compose down` for that color         |
| `rollback_to`        | `(color: "blue" \| "green") -> dict`                   | Tear candidate, restore color, flip status to `rolled_back` |

`rollout_bluegreen` is gated: if the team is currently
`waiting_for_approval`, the call short-circuits to
`{"ok": false, "reason": "...", "status": "waiting_for_approval"}`
without touching Docker.

## State it mutates

| Field                      | Via                                                  |
| -------------------------- | ---------------------------------------------------- |
| `rollout.image_tag`        | `build_image`                                         |
| `rollout.project_base`     | `build_image`                                         |
| `rollout.candidate_color`  | `rollout_bluegreen`, reset by `switch_active` / `rollback_to` |
| `rollout.active_color`     | `switch_active`, `rollback_to`                        |
| `rollout.rolled_back`      | `rollback_to`                                         |
| `status`                   | `rollout_bluegreen → deploying`, `switch_active → watching`, `rollback_to → rolled_back` |
| `notes`                    | via every status transition + `push_image` stub note  |

## Docker integration

Vector uses `ComposeDeployService(skip_verification=True)` — the pure
subprocess wrapper from `src/docker_svc/compose_service.py`. This means:

- No docker-py dependency.
- Tests patch `subprocess.run` and verify Vector without a live daemon.
- Compose file auto-detection order:
  `compose.yml` → `compose.yaml` → `docker-compose.yml` → `docker-compose.yaml`.

## Failure modes

- **Gated call while `waiting_for_approval`.** `rollout_bluegreen` returns
  `{"ok": false, "reason": "...gated"}` without side effects — safe.
- **Compose failure.** `deploy_candidate` surfaces `result.status`,
  `result.error`. Vector reports; Axiom decides whether to re-delegate or
  mark the run failed.
- **Rolled back without a prior `active_color`.** `rollback_to` still
  records `rolled_back=True`; operators should inspect the health samples
  to understand the trigger.

## Configuration

- **Model.** Inherits from credentials via `build_team(peer_model=...)`.
- **Tool-call budget.** 24 by default.
- **Compose project prefix.** `<basename(path)>-<sha1(abs_path)[:6]>`
  plus `-blue` / `-green`.
