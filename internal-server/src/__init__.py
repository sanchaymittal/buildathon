"""
DevOps Agent Package - Provides functionality for DevOps operations with the Gemini Agents SDK.

This package includes modules for Docker container operations, GitHub integration,
and other DevOps tools, designed to be used with the Gemini Agents SDK.
"""

from .docker_svc import (
    # Models
    DeployRequest,
    Deployment,
    ContainerFilter,
    ContainerAction,
    ContainerLogRequest,
    
    # Services
    DockerService,
    DockerDeployService,
    
    # Tools
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

from .github import (
    # GitHub Models
    GitHubRepoRequest,
    GitHubIssueRequest,
    GitHubCreateIssueRequest,
    GitHubPRRequest,
    GitHubRepository,
    GitHubIssue,
    GitHubPullRequest,
    
    # GitHub Tools
    get_repository,
    list_issues,
    create_issue,
    list_pull_requests
)

from .core import (
    # Context
    DevOpsContext,
    
    # Config
    get_config,
    get_config_value,
    set_config_value,
    load_config,
    
    # Credentials
    DockerCredentials,
    GitHubCredentials,
    CredentialManager,
    get_credential_manager,
    set_credential_manager,
    
    # Guardrails
    security_guardrail,
    sensitive_info_guardrail,
    SecurityCheckOutput,
    SensitiveInfoOutput
)

__all__ = [
    # Docker
    'DeployRequest',
    'Deployment',
    'ContainerFilter',
    'ContainerAction',
    'ContainerLogRequest',
    'DockerService',
    'DockerDeployService',
    'deploy_repository',
    'list_deployments',
    'get_deployment',
    'stop_deployment',
    'start_deployment',
    'restart_deployment',
    'remove_deployment',
    'get_deployment_logs',
    'list_containers',
    'get_container',
    'stop_container',
    'start_container',
    'restart_container',
    'remove_container',
    'get_container_logs',
    'list_images',
    
    # GitHub
    'GitHubRepoRequest',
    'GitHubIssueRequest',
    'GitHubCreateIssueRequest',
    'GitHubPRRequest',
    'GitHubRepository',
    'GitHubIssue',
    'GitHubPullRequest',
    'get_repository',
    'list_issues',
    'create_issue',
    'list_pull_requests',
    
    # Core
    'DevOpsContext',
    'get_config',
    'get_config_value',
    'set_config_value',
    'load_config',
    'DockerCredentials',
    'GitHubCredentials',
    'CredentialManager',
    'get_credential_manager',
    'set_credential_manager',
    'security_guardrail',
    'sensitive_info_guardrail',
    'SecurityCheckOutput',
    'SensitiveInfoOutput'
]

__version__ = '0.2.0'
