"""Axiom - orchestrator agent.

Receives a task, decomposes it into a Forge -> Warden -> Vector -> Sentry
pipeline, holds shared state across the team. Axiom never writes code
itself; it only calls handoff tools and integration adapters.
"""

from __future__ import annotations

from typing import Any, List, Optional

from ...gemini_agents import Agent, function_tool, RunContextWrapper
from ...integrations.github_pr import github_comment as _github_comment
from ...integrations.linear import linear_create_issue as _linear_create_issue
from ...integrations.slack import slack_post as _slack_post
from .context import TeamContext, TeamRunStatus

AXIOM_SYSTEM_PROMPT = """\
You are Axiom, the orchestrator of a five-agent DevOps team:

  - Forge:  staff engineer (writes the diff, runs tests, pushes branches)
  - Warden: security engineer (runs SAST / secrets / deps scans, blocks high-severity findings)
  - Vector: deployer (builds the image, rolls out blue/green, owns the deploy window)
  - Sentry: observer (watches service health; has rollback authority)

Your job is to decompose the user's task, delegate work to the right peer,
and keep the shared TeamContext up to date.

Pipeline (default):
  1. Delegate engineering to Forge with a concise task spec.
  2. Delegate security review to Warden.
  3. If Warden records any finding with severity >= high, stop and call
     request_approval("pre_deploy"). Do NOT deploy until the run is
     resumed with an approval.
  4. Delegate the rollout to Vector (blue/green on the local Docker daemon).
  5. Delegate the watch window to Sentry and wait for its recommendation
     (promote / hold / rollback). Sentry may already have rolled back on
     its own authority; respect that.

Ground rules
------------
- You do NOT write code. You call tools.
- You do NOT deploy or roll back directly. Those actions belong to Vector
  and Sentry respectively.
- You MAY update the team state (status, notes) via update_team_state so
  downstream tooling and operators see coherent progress.
- You MAY post to Linear / Slack / GitHub via the integration tools. They
  are stubs in MVP but the calls are audited.
- When blocking findings appear, call request_approval BEFORE any further
  handoff, and surface the reason.
- Final reply: a short structured summary of what was done, the status,
  and any human follow-up required.
"""


def _update_team_state_tool():
    @function_tool()
    async def update_team_state(
        ctx: RunContextWrapper[TeamContext],
        status: Optional[str] = None,
        note: Optional[str] = None,
    ) -> dict:
        """Update the shared team status and append an audit note.

        ``status`` must be one of the TeamRunStatus values or None to keep
        the current status. ``note`` is appended to the run's note trail.
        """
        team = ctx.context
        if status:
            try:
                team.set_status(TeamRunStatus(status), note=note)
            except ValueError as exc:
                return {"ok": False, "error": f"invalid status: {status}"}
        elif note:
            team.add_note(note)
        return {"ok": True, "status": team.status.value, "notes": list(team.notes)}

    return update_team_state


def _request_approval_tool():
    @function_tool()
    async def request_approval(
        ctx: RunContextWrapper[TeamContext], gate: str, reason: Optional[str] = None
    ) -> dict:
        """Pause the run until a caller approves or rejects ``gate``.

        Sets the team status to ``waiting_for_approval`` and records
        ``reason`` in ``blocking_reason``. The HTTP layer surfaces this
        state and resumes the run via /team/runs/{id}/approve.
        """
        team = ctx.context
        team.blocking_reason = reason
        team.set_status(
            TeamRunStatus.waiting_for_approval,
            note=f"waiting on approval gate '{gate}': {reason or '(no reason)'}",
        )
        return {
            "ok": True,
            "gate": gate,
            "status": team.status.value,
            "reason": reason,
        }

    return request_approval


def _linear_tool():
    @function_tool()
    async def linear_create_issue(
        ctx: RunContextWrapper[TeamContext],
        title: str,
        body: str = "",
        team: Optional[str] = None,
    ) -> dict:
        """Create a Linear issue (stub in MVP)."""
        return _linear_create_issue(title=title, body=body, team=team)

    return linear_create_issue


def _slack_tool():
    @function_tool()
    async def slack_post(
        ctx: RunContextWrapper[TeamContext], channel: str, message: str
    ) -> dict:
        """Post a Slack message (stub in MVP)."""
        return _slack_post(channel=channel, message=message)

    return slack_post


def _github_comment_tool():
    @function_tool()
    async def github_comment(
        ctx: RunContextWrapper[TeamContext], pr_ref: str, body: str
    ) -> dict:
        """Post a comment to a GitHub PR (stub in MVP)."""
        return _github_comment(pr_ref=pr_ref, body=body)

    return github_comment


def build_axiom(
    *, model: str = "gemini-2.5-pro", extra_tools: Optional[List[Any]] = None
) -> Agent:
    tools: List[Any] = [
        _update_team_state_tool(),
        _request_approval_tool(),
        _linear_tool(),
        _slack_tool(),
        _github_comment_tool(),
    ]
    if extra_tools:
        tools.extend(extra_tools)
    return Agent(
        name="Axiom",
        instructions=AXIOM_SYSTEM_PROMPT,
        tools=tools,
        model=model,
    )
