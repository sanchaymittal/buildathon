"""API Routes - Route modules for FastAPI.

The compose and agent routers are always importable. Legacy routers
(deployments, containers, github) depend on optional packages (``docker``,
``google-generativeai``, ``PyGithub``) and are imported defensively so the
server can still start in a minimal environment.
"""

from . import compose
from . import agent as agent_routes
from . import mcp

try:  # pragma: no cover - depends on optional deps
    from . import deployments, containers

    _LEGACY_DOCKER_ROUTES = True
except Exception:  # pragma: no cover
    deployments = None  # type: ignore[assignment]
    containers = None  # type: ignore[assignment]
    _LEGACY_DOCKER_ROUTES = False

try:  # pragma: no cover - depends on PyGithub
    from . import github as github_routes

    _GITHUB_ROUTES = True
except Exception:  # pragma: no cover
    github_routes = None  # type: ignore[assignment]
    _GITHUB_ROUTES = False

__all__ = ["compose", "agent_routes", "mcp"]
if _LEGACY_DOCKER_ROUTES:
    __all__.extend(["deployments", "containers"])
if _GITHUB_ROUTES:
    # Expose under the historical ``github`` name for callers that imported it.
    globals()["github"] = github_routes
    __all__.append("github")
