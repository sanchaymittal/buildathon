"""
API Dependencies - Dependency injection for FastAPI routes.
"""

from functools import lru_cache

from ..docker_svc.service import DockerService
from ..docker_svc.deploy import DockerDeployService
from ..github.github import GitHubService
from ..core.credentials import get_credential_manager


@lru_cache()
def get_docker_service() -> DockerService:
    """Get or create the DockerService instance."""
    return DockerService()


@lru_cache()
def get_deploy_service() -> DockerDeployService:
    """Get or create the DockerDeployService instance."""
    return DockerDeployService()


def get_github_service() -> GitHubService:
    """Get or create the GitHubService instance."""
    cred_manager = get_credential_manager()
    creds = cred_manager.get_github_credentials()
    return GitHubService(token=creds.token)


def get_deployment_service() -> DockerDeployService:
    """Get the deployment service instance."""
    return get_deploy_service()