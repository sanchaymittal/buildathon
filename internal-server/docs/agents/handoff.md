# Handoff Primitive

The team has **no shared message bus**. Coordination happens through
`handoff_tool()` — each peer is exposed to Axiom as a Gemini function
tool named `handoff_to_<peer>`. Calling that tool spawns a sub-run of
the peer with its own tool set and budget, but sharing the same
`TeamContext`.

**Source:** `src/agent/team/handoff.py`

## Signature

```python
def handoff_tool(
    *,
    name: str,                                 # e.g. "handoff_to_forge"
    description: str,                          # shown to the LLM
    agent_factory: Callable[[], Agent],        # builds the peer fresh per call
    runner_factory: Optional[Callable[[], Any]] = None,
    max_tool_calls: int = 24,
) -> FunctionTool:
    ...
```

The returned tool expects a single argument:

```python
async def handoff_to_xxx(task_spec: str) -> HandoffResult
```

## `HandoffResult`

```python
@dataclass
class HandoffResult:
    peer: str                             # "Forge" | "Warden" | ...
    summary: str                          # peer's final text reply
    finish_reason: str                    # "stop" | "paused" | "max_tool_calls" | ...
    iterations: int                       # Gemini turns the peer took
    tool_calls: List[Dict[str, Any]]      # full trace with arguments/result/error/duration_ms
    status: str                           # TeamContext.status at return
    paused_gate: Optional[str] = None     # set when paused
```

## Pause semantics

`handoff_tool` is **pause-aware**:

1. Before spinning up the peer, it checks
   `team_context.status == TeamRunStatus.waiting_for_approval`. If so,
   it short-circuits with `finish_reason="paused"` — no LLM call, no
   Gemini quota burned.
2. If the peer's inner runner raises `TeamPaused`, the handoff returns
   with `finish_reason="paused"` and `paused_gate=<gate>`.
3. Axiom inspects `finish_reason` and must stop delegating. The outer
   `TeamExecutor.drive()` then returns to the HTTP layer, which marks
   the run as `waiting_for_approval`.

## Prompt injection

When a handoff fires, the peer is invoked with:

```
You are {peer}. The orchestrator has delegated the following work to you:

{task_spec}
Complete it using your tools and return a concise final report.

Team context (read-only view):
{json.dumps(team_context.summary(), indent=2)}
```

The peer sees the full context snapshot but is instructed that it's
read-only advisory — the only durable mutations go through the tools it
owns.

## Why "handoff-as-tool"?

- **Works within Gemini's function-calling model.** No need for a
  scheduler or agent runtime on top of the SDK.
- **Budget is scoped.** Axiom's 16 calls are hers; each handoff spawns a
  fresh runner with its own `max_tool_calls`.
- **Peers are stateless instances.** `agent_factory` creates a fresh
  `Agent` per call — no state leakage between consecutive handoffs to
  the same peer.
- **Tests can inject a fake runner.** `runner_factory` is threaded
  through `build_team(runner_factory=...)`, so scripted integration
  tests (see `tests/team/test_flow_*`) never touch Gemini.

## Failure modes

- **Peer exhausts its budget.** `finish_reason="max_tool_calls"`. Axiom
  should inspect `tool_calls` and decide whether to retry or fail.
- **Peer crashes.** Exception bubbles up to `TeamExecutor._run_axiom`,
  which marks the run `failed` and emits `team_run_failed`.
- **Infinite handoff loop.** Prevented structurally — peers have no
  handoff tools of their own. Only Axiom can hand off.
