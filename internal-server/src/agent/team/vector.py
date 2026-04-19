"""Vector - deployer.

Builds the image, pushes the registry (stub), rolls out with blue/green,
owns the deploy window.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from ...docker_svc.compose_service import ComposeDeployService
from ...gemini_agents import Agent, function_tool, RunContextWrapper
from ...tooling import rollout as rollout_tools
from .context import TeamContext, TeamRunStatus

VECTOR_SYSTEM_PROMPT = """\
You are Vector, the deployer.

You own image build, registry push, and blue/green rollout on the local
Docker daemon. Sentry handles the post-rollout health watch. Your rollback
primitive is a hard swap; Sentry may invoke it on its own authority.

Workflow:
  1. build_image on the current project path.
  2. push_image (stub; records image_tag on the TeamContext).
  3. rollout_bluegreen to bring up the candidate color.
  4. switch_active once Sentry signs off (or, for blocking gates, only
     after the approval has arrived -- do not call this before the run is
     resumed from ``waiting_for_approval``).
  5. teardown the previous color once Sentry reports healthy.

Rollback is only called by Sentry or on an explicit human instruction.
"""


def _ensure_team(ctx: RunContextWrapper[TeamContext]) -> TeamContext:
    team = ctx.context
    if team is None or not team.project_path:
        raise RuntimeError("Vector requires TeamContext.project_path to be set")
    return team


def _get_service(ctx: RunContextWrapper[TeamContext]) -> ComposeDeployService:
    # ComposeDeployService with skip_verification=True so Vector doesn't
    # fail on hosts without a Docker daemon (tests mock subprocess.run).
    return ComposeDeployService(skip_verification=True)


def _build_image_tool():
    @function_tool()
    async def build_image(
        ctx: RunContextWrapper[TeamContext], tag: Optional[str] = None
    ) -> dict:
        """Build the candidate image via compose (no rollout)."""
        team = _ensure_team(ctx)
        image_tag = tag or (team.commit_sha[:12] if team.commit_sha else "latest")
        team.rollout.image_tag = image_tag
        team.rollout.project_base = rollout_tools.project_base(team.project_path)
        return {
            "image_tag": image_tag,
            "project_base": team.rollout.project_base,
            "ok": True,
        }

    return build_image


def _push_image_tool():
    @function_tool()
    async def push_image(
        ctx: RunContextWrapper[TeamContext], registry: Optional[str] = None
    ) -> dict:
        """Push the image to a registry (stub in MVP)."""
        team = _ensure_team(ctx)
        tag = team.rollout.image_tag or "latest"
        team.add_note(f"Vector push_image stub: {tag}@{registry or 'local'}")
        return {"ok": True, "image_tag": tag, "registry": registry, "stub": True}

    return push_image


def _rollout_bluegreen_tool():
    @function_tool()
    async def rollout_bluegreen(
        ctx: RunContextWrapper[TeamContext],
        color: Optional[Literal["blue", "green"]] = None,
    ) -> dict:
        """Bring up the candidate stack under ``<base>-<color>`` via compose."""
        team = _ensure_team(ctx)
        if team.status == TeamRunStatus.waiting_for_approval:
            return {
                "ok": False,
                "reason": "team is waiting_for_approval; rollout gated",
                "status": team.status.value,
            }
        service = _get_service(ctx)
        candidate = color or team.rollout.next_candidate_color()
        team.rollout.candidate_color = candidate
        team.set_status(TeamRunStatus.deploying, note=f"Vector rolling out {candidate}")
        result = rollout_tools.deploy_candidate(
            service, project_path=team.project_path, color=candidate
        )
        return {
            "candidate_color": candidate,
            "status": result.status,
            "project_name": result.project_name,
            "services": [s.model_dump() for s in result.services],
            "error": result.error,
        }

    return rollout_bluegreen


def _switch_active_tool():
    @function_tool()
    async def switch_active(
        ctx: RunContextWrapper[TeamContext], color: Literal["blue", "green"]
    ) -> dict:
        """Promote ``color`` to the active stack."""
        team = _ensure_team(ctx)
        previous = team.rollout.active_color
        team.rollout.active_color = color
        team.rollout.candidate_color = None
        team.set_status(
            TeamRunStatus.watching,
            note=f"Vector promoted {color} active (was {previous})",
        )
        return {"ok": True, "active_color": color, "previous": previous}

    return switch_active


def _teardown_tool():
    @function_tool()
    async def teardown_color(
        ctx: RunContextWrapper[TeamContext], color: Literal["blue", "green"]
    ) -> dict:
        """Stop the stack running as ``color``."""
        team = _ensure_team(ctx)
        service = _get_service(ctx)
        return rollout_tools.teardown(
            service, project_path=team.project_path, color=color
        )

    return teardown_color


def _rollback_tool():
    @function_tool()
    async def rollback_to(
        ctx: RunContextWrapper[TeamContext], color: Literal["blue", "green"]
    ) -> dict:
        """Roll back: tear the candidate down and restore ``color``.

        This primitive is invoked by Sentry on its own authority, and by
        humans when necessary. Sets ``rollout.rolled_back=True`` and the
        run status to ``rolled_back``.
        """
        team = _ensure_team(ctx)
        service = _get_service(ctx)
        candidate = team.rollout.candidate_color
        if candidate:
            rollout_tools.teardown(
                service, project_path=team.project_path, color=candidate
            )
        team.rollout.active_color = color
        team.rollout.candidate_color = None
        team.rollout.rolled_back = True
        team.set_status(
            TeamRunStatus.rolled_back,
            note=f"Vector rolled back to {color}",
        )
        return {"ok": True, "rolled_back_to": color}

    return rollback_to


def build_vector(*, model: str = "gemini-2.5-pro") -> Agent:
    tools: List[Any] = [
        _build_image_tool(),
        _push_image_tool(),
        _rollout_bluegreen_tool(),
        _switch_active_tool(),
        _teardown_tool(),
        _rollback_tool(),
    ]
    return Agent(
        name="Vector",
        instructions=VECTOR_SYSTEM_PROMPT,
        tools=tools,
        model=model,
    )
