# The Five-Agent DevOps Team

A Gemini-driven team of five specialised agents that takes a local repository
from "change request" to "deployed blue/green stack" on the local Docker
daemon.

| Agent                    | Role              | Authority                                       |
| ------------------------ | ----------------- | ----------------------------------------------- |
| [Axiom](./axiom.md)      | Orchestrator      | Decomposes task, delegates, pauses for approval |
| [Forge](./forge.md)      | Staff engineer    | Writes the diff, tests, pushes the branch       |
| [Warden](./warden.md)    | Security engineer | Runs scanners; blocks on severity ≥ high        |
| [Vector](./vector.md)    | Deployer          | Builds image, rolls out blue/green              |
| [Sentry](./sentry.md)    | Observer          | Watches health; can roll back autonomously      |

Supporting references:

- [Shared state — `TeamContext`](./context.md)
- [Handoff primitive](./handoff.md)
- [Run lifecycle & approvals](./run-lifecycle.md)

## At a glance

```
          ┌──────────┐  handoff_to_forge     ┌───────┐
  task ─▶ │  Axiom   │ ───────────────────▶  │ Forge │
          │ (orch.)  │                       └───┬───┘
          │          │  handoff_to_warden        │ commit_sha
          │          │ ───────────────────▶  ┌───▼────┐
          │          │                       │ Warden │
          │          │  ◀── block_or_approve └───┬────┘
          │          │                           │ findings
          │ (pause on waiting_for_approval)      │
          │          │  handoff_to_vector    ┌───▼────┐
          │          │ ───────────────────▶  │ Vector │
          │          │                       └───┬────┘
          │          │  handoff_to_sentry        │ rollout
          │          │ ───────────────────▶  ┌───▼────┐
          │          │                       │ Sentry │
          └──────────┘                       └────────┘
```

## Design invariants

1. **One shared state.** Every tool receives the same `TeamContext` via
   `RunContextWrapper`. Mutations are only made through declared tool
   functions so the full run is auditable.
2. **Handoff-as-tool.** Peers are exposed to Axiom as async function tools
   (`handoff_to_forge`, `handoff_to_warden`, …). This is the only
   coordination primitive; there is no shared message bus.
3. **Deterministic gates.** Warden's `block_or_approve` is a pure function
   of `TeamContext.findings`. Sentry's rollback recommendation is a pure
   function of the samples it actually observed.
4. **Rollback authority sits with Sentry.** Axiom never rolls back;
   Vector's `rollback_to` is a primitive that both Sentry and humans can
   invoke.
5. **MVP is local-only.** No cloud, no registry push, no auth. Integrations
   (Linear/Slack/PagerDuty/GitHub PR) ship as `NullAdapter` stubs.
6. **Tool-call budget is per-agent** (default 16–24 calls). There is no
   global run budget; pausing is the flow-control mechanism.

## Quick reference

**Start a run:**

```bash
python -m src.cli team run --path ./path/to/repo --task "ship the thing"
```

**Inspect:**

```bash
python -m src.cli team status <run-id>
python -m src.cli team events <run-id>
```

**Resume after a block:**

```bash
python -m src.cli team approve <run-id> --gate pre_deploy
# or
curl -XPOST :8000/team/runs/<run-id>/approve -d '{"gate":"pre_deploy"}'
```

## Source layout

```
src/agent/team/
├── build.py            # build_team() – wires handoffs on Axiom
├── context.py          # TeamContext, TeamRunStatus, SecurityFinding, RolloutState
├── executor.py         # TeamExecutor.drive() / .resume()
├── handoff.py          # handoff_tool() primitive, TeamPaused, HandoffResult
├── orchestrator.py     # Axiom
├── forge.py            # Forge
├── warden.py           # Warden
├── vector.py           # Vector
├── sentry.py           # Sentry
└── runs.py             # TeamRun, TeamRunStore, TeamEvent
```
