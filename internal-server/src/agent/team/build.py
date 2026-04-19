"""build_team() - assemble the five-agent DevOps team.

Returned object holds the orchestrator :class:`Agent` (Axiom) with handoff
tools bound for each peer. Callers pass this into ``GeminiRunner.run``
along with a :class:`TeamContext`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from ...gemini_agents import Agent
from .forge import build_forge
from .handoff import handoff_tool
from .orchestrator import build_axiom
from .sentry import build_sentry
from .vector import build_vector
from .warden import build_warden


@dataclass
class Team:
    axiom: Agent
    forge_factory: Callable[[], Agent]
    warden_factory: Callable[[], Agent]
    vector_factory: Callable[[], Agent]
    sentry_factory: Callable[[], Agent]


def _default_model() -> str:
    """Pick the default model from the credential manager, falling back.

    This lets ``DEVOPS_GEMINI__MODEL`` / the credentials file route every
    team agent without having to override kwargs everywhere.
    """
    try:
        from ...core.credentials import get_credential_manager

        return get_credential_manager().get_gemini_credentials().model
    except Exception:
        return "gemini-2.5-pro"


def build_team(
    *,
    orchestrator_model: Optional[str] = None,
    peer_model: Optional[str] = None,
    runner_factory: Optional[Callable[[], Any]] = None,
) -> Team:
    """Return a :class:`Team` whose Axiom agent has handoff tools wired.

    When ``orchestrator_model`` / ``peer_model`` are ``None`` the default
    model from :class:`GeminiCredentials` is used. ``runner_factory`` is
    forwarded to each handoff tool so tests can inject a fake runner for
    every peer without monkey-patching.
    """
    default = _default_model()
    orchestrator_model = orchestrator_model or default
    peer_model = peer_model or default

    forge_factory = lambda: build_forge(model=peer_model)
    warden_factory = lambda: build_warden(model=peer_model)
    vector_factory = lambda: build_vector(model=peer_model)
    sentry_factory = lambda: build_sentry(model=peer_model)

    handoffs = [
        handoff_tool(
            name="handoff_to_forge",
            description=(
                "Delegate an engineering task to Forge. Provide a concise "
                "task specification (what to change and how to verify it)."
            ),
            agent_factory=forge_factory,
            runner_factory=runner_factory,
        ),
        handoff_tool(
            name="handoff_to_warden",
            description=(
                "Ask Warden to run security scans and record findings. "
                "Provide the PR or branch reference and any focus areas."
            ),
            agent_factory=warden_factory,
            runner_factory=runner_factory,
        ),
        handoff_tool(
            name="handoff_to_vector",
            description=(
                "Ask Vector to build and roll out the new revision "
                "(blue/green). Provide the desired image tag and target color."
            ),
            agent_factory=vector_factory,
            runner_factory=runner_factory,
        ),
        handoff_tool(
            name="handoff_to_sentry",
            description=(
                "Ask Sentry to watch the rollout for a bounded window and "
                "decide whether to promote or roll back."
            ),
            agent_factory=sentry_factory,
            runner_factory=runner_factory,
        ),
    ]

    axiom = build_axiom(model=orchestrator_model, extra_tools=handoffs)
    return Team(
        axiom=axiom,
        forge_factory=forge_factory,
        warden_factory=warden_factory,
        vector_factory=vector_factory,
        sentry_factory=sentry_factory,
    )
