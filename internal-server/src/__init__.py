"""
DevOps Agent Package - Provides functionality for DevOps operations with the Gemini Agents SDK.

This package includes modules for Docker container operations, GitHub integration,
and other DevOps tools, designed to be used with the Gemini Agents SDK.

The local Docker Compose deployment flow (``deploy_local_project`` and friends)
is dependency-light and is the primary path for the hackathon MVP. The legacy
single-container + GitHub-clone flow is exported conditionally; if the optional
``docker`` or ``agents`` packages are missing those symbols are simply omitted.
"""

from .docker_svc import (
    # Exceptions
    DockerServiceError,
    DockerDaemonError,
    ComposeDeployError,
    # Legacy models
    DeployRequest,
    DeployUserRequest,
    Deployment,
    ContainerFilter,
    ContainerAction,
    ContainerLogRequest,
    # Local Compose models
    DeployLocalRequest,
    DeployLocalResult,
    ComposeServiceStatus,
    ComposeLogsRequest,
    ComposeTargetRequest,
    # Local Compose service + tools
    ComposeDeployService,
    deploy_local_project,
    project_status,
    stop_local_project,
    project_logs,
)

from .docker_svc import _LEGACY_AVAILABLE as _DOCKER_LEGACY_AVAILABLE

if _DOCKER_LEGACY_AVAILABLE:  # pragma: no cover - depends on optional deps
    from .docker_svc import (
        DockerService,
        DockerDeployService,
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

try:
    from .github import (
        GitHubRepoRequest,
        GitHubIssueRequest,
        GitHubCreateIssueRequest,
        GitHubPRRequest,
        GitHubRepository,
        GitHubIssue,
        GitHubPullRequest,
        get_repository,
        list_issues,
        create_issue,
        list_pull_requests,
    )

    _GITHUB_AVAILABLE = True
except Exception:  # pragma: no cover - depends on optional deps (PyGithub, agents)
    _GITHUB_AVAILABLE = False

try:
    from .core import (
        DevOpsContext,
        get_config,
        get_config_value,
        set_config_value,
        load_config,
        DockerCredentials,
        GitHubCredentials,
        CredentialManager,
        get_credential_manager,
        set_credential_manager,
        security_guardrail,
        sensitive_info_guardrail,
        SecurityCheckOutput,
        SensitiveInfoOutput,
    )

    _CORE_AVAILABLE = True
except Exception:  # pragma: no cover - depends on optional deps
    _CORE_AVAILABLE = False

__all__ = [
    # Exceptions
    "DockerServiceError",
    "DockerDaemonError",
    "ComposeDeployError",
    # Legacy docker models
    "DeployRequest",
    "DeployUserRequest",
    "Deployment",
    "ContainerFilter",
    "ContainerAction",
    "ContainerLogRequest",
    # Local compose models
    "DeployLocalRequest",
    "DeployLocalResult",
    "ComposeServiceStatus",
    "ComposeLogsRequest",
    "ComposeTargetRequest",
    # Local compose service + tools
    "ComposeDeployService",
    "deploy_local_project",
    "project_status",
    "stop_local_project",
    "project_logs",
]

if _DOCKER_LEGACY_AVAILABLE:
    __all__.extend(
        [
            "DockerService",
            "DockerDeployService",
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

if _GITHUB_AVAILABLE:
    __all__.extend(
        [
            "GitHubRepoRequest",
            "GitHubIssueRequest",
            "GitHubCreateIssueRequest",
            "GitHubPRRequest",
            "GitHubRepository",
            "GitHubIssue",
            "GitHubPullRequest",
            "get_repository",
            "list_issues",
            "create_issue",
            "list_pull_requests",
        ]
    )

if _CORE_AVAILABLE:
    __all__.extend(
        [
            "DevOpsContext",
            "get_config",
            "get_config_value",
            "set_config_value",
            "load_config",
            "DockerCredentials",
            "GitHubCredentials",
            "CredentialManager",
            "get_credential_manager",
            "set_credential_manager",
            "security_guardrail",
            "sensitive_info_guardrail",
            "SecurityCheckOutput",
            "SensitiveInfoOutput",
        ]
    )

__version__ = "0.2.0"
