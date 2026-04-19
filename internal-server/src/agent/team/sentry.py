"""Sentry - observer.

Watches the candidate rollout for a bounded window. Has rollback authority
and calls Vector's rollback primitive directly when samples cross the
unhealthy threshold.
"""

from __future__ import annotations

from typing import Any, List, Optional

from ...docker_svc.compose_service import ComposeDeployService
from ...gemini_agents import Agent, function_tool, RunContextWrapper
from ...integrations.pagerduty import pagerduty_trigger as _pagerduty_trigger
from ...tooling import health as health_tools
from ...tooling import rollout as rollout_tools
from .context import TeamContext, TeamRunStatus

SENTRY_SYSTEM_PROMPT = """\
You are Sentry, the observer.

You watch pod / container health and an optional HTTP probe for the
rollout window. You have rollback authority: if samples trip the
unhealthy threshold, call trigger_rollback directly (do not ask Axiom).

Workflow:
  1. watch for the agreed window. Default window is 60 seconds at a 5s
     interval.
  2. If the recommendation is "rollback", call trigger_rollback with the
     previous active color.
  3. If "promote", leave Vector to finalise; report "promote".
  4. If "hold", keep watching or report that more data is needed.

Never fabricate samples. Your recommendation is a deterministic function
of the samples you actually observed.
"""


def _ensure_team(ctx: RunContextWrapper[TeamContext]) -> TeamContext:
    team = ctx.context
    if team is None or not team.project_path:
        raise RuntimeError("Sentry requires TeamContext.project_path to be set")
    return team


def _get_service(ctx: RunContextWrapper[TeamContext]) -> ComposeDeployService:
    return ComposeDeployService(skip_verification=True)


def _poll_services_tool():
    @function_tool()
    async def poll_services(
        ctx: RunContextWrapper[TeamContext], color: Optional[str] = None
    ) -> dict:
        team = _ensure_team(ctx)
        service = _get_service(ctx)
        project_name = (
            rollout_tools.project_name_for(team.project_path, color) if color else None
        )
        snapshot = health_tools.poll_services(
            service, project_path=team.project_path, project_name=project_name
        )
        return {"project_name": project_name, "services": snapshot}

    return poll_services


def _http_probe_tool():
    @function_tool()
    async def http_probe(
        ctx: RunContextWrapper[TeamContext], url: str, timeout_s: int = 5
    ) -> dict:
        return health_tools.http_probe(url, timeout_s=timeout_s)

    return http_probe


def _watch_tool():
    @function_tool()
    async def watch(
        ctx: RunContextWrapper[TeamContext],
        window_s: int = 60,
        interval_s: int = 5,
        healthcheck_url: Optional[str] = None,
        color: Optional[str] = None,
    ) -> dict:
        team = _ensure_team(ctx)
        service = _get_service(ctx)
        project_name = (
            rollout_tools.project_name_for(team.project_path, color)
            if color
            else (
                rollout_tools.project_name_for(
                    team.project_path, team.rollout.candidate_color
                )
                if team.rollout.candidate_color
                else None
            )
        )
        team.set_status(
            TeamRunStatus.watching,
            note=f"Sentry watching {project_name or '(active)'} for {window_s}s",
        )
        report = health_tools.watch(
            project_path=team.project_path,
            service=service,
            project_name=project_name,
            window_s=window_s,
            interval_s=interval_s,
            healthcheck_url=healthcheck_url,
        )
        team.health_samples.extend(report["samples"])
        return {
            "project_name": project_name,
            "recommendation": report["recommendation"],
            "unhealthy_streak": report["unhealthy_streak"],
            "sample_count": len(report["samples"]),
        }

    return watch


def _trigger_rollback_tool():
    @function_tool()
    async def trigger_rollback(
        ctx: RunContextWrapper[TeamContext], reason: str
    ) -> dict:
        """Roll back to the previously active color.

        This is Sentry's autonomous authority. It tears down the candidate,
        flips the active color back, and pings PagerDuty (stub) with the
        reason.
        """
        team = _ensure_team(ctx)
        service = _get_service(ctx)
        candidate = team.rollout.candidate_color
        if candidate:
            rollout_tools.teardown(
                service, project_path=team.project_path, color=candidate
            )
        # Restore whatever colour was active before, defaulting to "blue" if
        # the run never promoted anything.
        previous = (
            team.rollout.active_color if team.rollout.active_color != "none" else "blue"
        )
        team.rollout.candidate_color = None
        team.rollout.active_color = previous
        team.rollout.rolled_back = True
        team.set_status(
            TeamRunStatus.rolled_back,
            note=f"Sentry rolled back: {reason}",
        )
        _pagerduty_trigger(summary=f"Rollback: {reason}", severity="error")
        return {"ok": True, "rolled_back_to": previous, "reason": reason}

    return trigger_rollback


def build_sentry(*, model: str = "gemini-2.5-pro") -> Agent:
    tools: List[Any] = [
        _poll_services_tool(),
        _http_probe_tool(),
        _watch_tool(),
        _trigger_rollback_tool(),
    ]
    return Agent(
        name="Sentry",
        instructions=SENTRY_SYSTEM_PROMPT,
        tools=tools,
        model=model,
    )
