"""Handoff primitive: exposes a peer agent to its orchestrator as a tool.

This is the coordination primitive for the five-agent DevOps team. Axiom
(the orchestrator) sees each peer as an async function tool like
``handoff_to_forge(task_spec)``. Invoking the tool spawns a sub-run of
that peer with its own :class:`Agent`, tools, and tool-call budget, but
sharing the same :class:`TeamContext` so mutations are immediately visible
to the caller.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ...gemini_agents import Agent, function_tool
from .context import TeamRunStatus

logger = logging.getLogger(__name__)


class TeamPaused(RuntimeError):
    """Raised when a handoff detects the team is waiting for human approval."""

    def __init__(self, gate: str, reason: Optional[str] = None) -> None:
        super().__init__(
            f"team run paused at gate '{gate}'" + (f": {reason}" if reason else "")
        )
        self.gate = gate
        self.reason = reason


@dataclass
class HandoffResult:
    peer: str
    summary: str
    finish_reason: str
    iterations: int
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    status: str = ""
    paused_gate: Optional[str] = None


def handoff_tool(
    *,
    name: str,
    description: str,
    agent_factory: Callable[[], Agent],
    runner_factory: Optional[Callable[[], Any]] = None,
    max_tool_calls: int = 24,
):
    """Return a ``function_tool``-decorated coroutine for Axiom to call.

    The returned tool expects a single ``task_spec: str`` argument. It
    builds the peer agent via ``agent_factory``, then runs it with the
    shared ``TeamContext`` (taken from ``ctx.context``).
    """

    def _make_runner():
        if runner_factory is not None:
            return runner_factory()
        # Import here to avoid pulling google-generativeai at module-load time.
        from ...gemini_agents.runner import GeminiRunner

        return GeminiRunner(max_tool_calls=max_tool_calls)

    async def _impl(ctx, task_spec: str) -> HandoffResult:
        team_context = getattr(ctx, "context", None)
        runner = _make_runner()
        peer = agent_factory()

        # Pause-aware short circuit: if the team context is already waiting
        # for approval, don't bother spinning the peer up.
        if (
            team_context is not None
            and team_context.status == TeamRunStatus.waiting_for_approval
        ):
            return HandoffResult(
                peer=peer.name,
                summary=f"skipped ({peer.name}); team is waiting for approval",
                finish_reason="paused",
                iterations=0,
                status=team_context.status.value,
                paused_gate=team_context.blocking_reason or "unknown",
            )

        prompt = _compose_peer_prompt(peer.name, task_spec, team_context)
        logger.info("Handing off to %s (%s)", peer.name, name)

        try:
            result = await runner.run(peer, prompt, context=team_context)
        except TeamPaused as paused:
            return HandoffResult(
                peer=peer.name,
                summary=f"{peer.name} paused at gate '{paused.gate}'",
                finish_reason="paused",
                iterations=0,
                status=team_context.status.value if team_context else "unknown",
                paused_gate=paused.gate,
            )

        return HandoffResult(
            peer=peer.name,
            summary=result.output,
            finish_reason=result.finish_reason,
            iterations=result.iterations,
            tool_calls=[
                {
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": tc.result,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms,
                }
                for tc in result.tool_calls
            ],
            status=(team_context.status.value if team_context else "unknown"),
        )

    # Assign the right ``__name__`` / ``__doc__`` so the runner's signature
    # inspection produces the right Gemini function declaration.
    _impl.__name__ = name
    _impl.__doc__ = description
    _impl.__qualname__ = name

    decorated = function_tool()(_impl)
    return decorated


def _compose_peer_prompt(peer_name: str, task_spec: str, team_context: Any) -> str:
    ctx_summary = ""
    if team_context is not None:
        summary = team_context.summary()
        ctx_summary = "\n\nTeam context (read-only view):\n" + _render_dict(summary)
    return (
        f"You are {peer_name}. The orchestrator has delegated the following "
        f"work to you:\n\n{task_spec}\n"
        f"Complete it using your tools and return a concise final report.{ctx_summary}"
    )


def _render_dict(d: Dict[str, Any], indent: int = 2) -> str:
    import json

    try:
        return json.dumps(d, indent=indent, default=str)
    except Exception:
        return str(d)
