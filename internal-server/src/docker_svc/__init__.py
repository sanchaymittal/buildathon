"""
Docker Package - Provides functionality for Docker container operations.

This package includes modules for building images, running containers,
deploying from GitHub, and orchestrating local Docker Compose projects.

Note: the legacy GitHub-clone + single-container deploy flow lives in
``service.py`` / ``deploy.py`` / ``tools.py`` and depends on the optional
``docker`` and ``agents`` packages. The local Docker Compose flow
(``compose_service.py`` / ``compose_models.py`` / ``compose_tools.py``) is
dependency-light (stdlib + pydantic) and is the default path for the
hackathon MVP. The heavy imports are guarded so this package stays importable
even when the optional packages are missing.
"""

from .base import (
    DockerServiceError,
    ContainerNotFoundError,
    ImageNotFoundError,
    ImageBuildError,
    ContainerStartError,
    ContainerStopError,
    DockerDaemonError,
    PortAllocationError,
    RepositoryError,
)

from .models import (
    DeployRequest,
    Deployment,
    ContainerFilter,
    ContainerAction,
    ContainerLogRequest,
    BuildRequest,
    RunContainerRequest,
    ImageFilter,
)

# Local Compose flow (no heavy deps).
from .compose_models import (
    DeployLocalRequest,
    DeployLocalResult,
    ComposeServiceStatus,
    ComposeLogsRequest,
    ComposeTargetRequest,
)
from .compose_service import ComposeDeployService, ComposeDeployError
from .compose_tools import (
    deploy_local_project,
    project_status,
    stop_local_project,
    project_logs,
)

# Optional: legacy docker-py + GitHub-clone flow. Import lazily so that
# consumers who only want the Compose flow don't need ``docker`` or
# ``agents`` installed.
try:  # pragma: no cover - exercised only when optional deps are installed
    from .service import DockerService
    from .deploy import DockerDeployService
    from .tools import (
        deploy_repository,
        list_deployments,
        get_deployment,
        stop_deployment,
        start_deployment,
        restart_deployment,
        remove_deployment,
        get_deployment_logs,
        list_containers,
        get_container,
        stop_container,
        start_container,
        restart_container,
        remove_container,
        get_container_logs,
        list_images,
    )

    _LEGACY_AVAILABLE = True
except Exception:  # pragma: no cover
    _LEGACY_AVAILABLE = False

__all__ = [
    # Exceptions
    "DockerServiceError",
    "ContainerNotFoundError",
    "ImageNotFoundError",
    "ImageBuildError",
    "ContainerStartError",
    "ContainerStopError",
    "DockerDaemonError",
    "PortAllocationError",
    "RepositoryError",
    "ComposeDeployError",
    # Models (legacy)
    "DeployRequest",
    "Deployment",
    "ContainerFilter",
    "ContainerAction",
    "ContainerLogRequest",
    "BuildRequest",
    "RunContainerRequest",
    "ImageFilter",
    # Models (compose)
    "DeployLocalRequest",
    "DeployLocalResult",
    "ComposeServiceStatus",
    "ComposeLogsRequest",
    "ComposeTargetRequest",
    # Services (compose)
    "ComposeDeployService",
    # Tools (compose)
    "deploy_local_project",
    "project_status",
    "stop_local_project",
    "project_logs",
]

if _LEGACY_AVAILABLE:
    __all__.extend(
        [
            # Services (legacy)
            "DockerService",
            "DockerDeployService",
            # Tools (legacy)
            "deploy_repository",
            "list_deployments",
            "get_deployment",
            "stop_deployment",
            "start_deployment",
            "restart_deployment",
            "remove_deployment",
            "get_deployment_logs",
            "list_containers",
            "get_container",
            "stop_container",
            "start_container",
            "restart_container",
            "remove_container",
            "get_container_logs",
            "list_images",
        ]
    )
