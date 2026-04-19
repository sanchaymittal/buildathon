"""
API Dependencies - Dependency injection for FastAPI routes.

The local-compose flow (``ComposeDeployService``) is dependency-light and
always available. The legacy ``DockerService`` / ``DockerDeployService`` /
``GitHubService`` getters depend on optional packages (``docker`` /
``agents`` / ``PyGithub``); their imports are guarded so this module stays
importable in minimal environments. When a legacy service is requested but
unavailable, the getter raises a clear ``HTTPException``.
"""

from functools import lru_cache

from fastapi import HTTPException, status

from ..core.credentials import get_credential_manager
from ..docker_svc.compose_service import ComposeDeployService

try:  # pragma: no cover - depends on optional deps
    from ..docker_svc.service import DockerService  # type: ignore
    from ..docker_svc.deploy import DockerDeployService  # type: ignore

    _LEGACY_DOCKER_AVAILABLE = True
except Exception:  # pragma: no cover
    DockerService = None  # type: ignore[assignment]
    DockerDeployService = None  # type: ignore[assignment]
    _LEGACY_DOCKER_AVAILABLE = False

try:  # pragma: no cover - depends on PyGithub + agents
    from ..github.github import GitHubService  # type: ignore

    _GITHUB_AVAILABLE = True
except Exception:  # pragma: no cover
    GitHubService = None  # type: ignore[assignment]
    _GITHUB_AVAILABLE = False


@lru_cache()
def get_compose_service() -> ComposeDeployService:
    """Lazily build a ComposeDeployService instance (no daemon ping)."""
    return ComposeDeployService(skip_verification=True)


@lru_cache()
def get_docker_service():
    """Get or create the legacy DockerService instance."""
    if not _LEGACY_DOCKER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Legacy Docker flow unavailable. Install 'docker' and "
                "'openai-agents' or use the /compose/* endpoints."
            ),
        )
    return DockerService()  # type: ignore[misc]


@lru_cache()
def get_deploy_service():
    """Get or create the legacy DockerDeployService instance."""
    if not _LEGACY_DOCKER_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Legacy deployment flow unavailable. Install 'docker' and "
                "'openai-agents' or use the /compose/* endpoints."
            ),
        )
    return DockerDeployService()  # type: ignore[misc]


def get_github_service():
    """Get or create a GitHubService with credentials from the manager."""
    if not _GITHUB_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub integration unavailable. Install 'PyGithub'.",
        )
    cred_manager = get_credential_manager()
    creds = cred_manager.get_github_credentials()
    return GitHubService(token=creds.token)  # type: ignore[misc]


def get_deployment_service():
    """Alias for ``get_deploy_service`` (backward-compat)."""
    return get_deploy_service()
