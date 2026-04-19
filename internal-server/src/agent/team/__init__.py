"""
Five-agent DevOps team: Axiom / Forge / Warden / Vector / Sentry.

Public entry points:

- :func:`build_team` - assembles the orchestrator + peer agents and wires
  handoff tools.
- :class:`TeamContext` - pydantic shared state passed into every
  ``RunContextWrapper`` during a team run.
- :class:`TeamRunStore` - in-memory registry of team runs and their
  approval gates.
"""

from .context import (
    RolloutState,
    SecurityFinding,
    TeamContext,
    TeamRunStatus,
)
from .runs import TeamEvent, TeamRun, TeamRunStore, get_team_run_store
from .orchestrator import AXIOM_SYSTEM_PROMPT, build_axiom
from .forge import FORGE_SYSTEM_PROMPT, build_forge
from .warden import WARDEN_SYSTEM_PROMPT, build_warden
from .vector import VECTOR_SYSTEM_PROMPT, build_vector
from .sentry import SENTRY_SYSTEM_PROMPT, build_sentry
from .handoff import TeamPaused, handoff_tool
from .build import Team, build_team
from .executor import TeamExecutor, execute_in_background

__all__ = [
    "RolloutState",
    "SecurityFinding",
    "TeamContext",
    "TeamRunStatus",
    "TeamEvent",
    "TeamRun",
    "TeamRunStore",
    "get_team_run_store",
    "TeamPaused",
    "handoff_tool",
    "AXIOM_SYSTEM_PROMPT",
    "FORGE_SYSTEM_PROMPT",
    "WARDEN_SYSTEM_PROMPT",
    "VECTOR_SYSTEM_PROMPT",
    "SENTRY_SYSTEM_PROMPT",
    "build_axiom",
    "build_forge",
    "build_warden",
    "build_vector",
    "build_sentry",
    "build_team",
    "Team",
    "TeamExecutor",
    "execute_in_background",
]
