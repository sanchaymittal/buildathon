"""
Docker Package - Provides functionality for Docker container operations.

This package includes modules for building images, running containers,
deploying from GitHub, and orchestration.
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
    # Models
    "DeployRequest",
    "Deployment",
    "ContainerFilter",
    "ContainerAction",
    "ContainerLogRequest",
    "BuildRequest",
    "RunContainerRequest",
    "ImageFilter",
    # Services
    "DockerService",
    "DockerDeployService",
    # Tools
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