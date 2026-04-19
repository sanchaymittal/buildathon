"""
Core Package - Provides core functionality for DevOps operations.

This package includes modules for configuration, credentials, context management,
and guardrails, with integration for the OpenAI Agents SDK.
"""

from .config import (
    get_config,
    get_config_value,
    set_config_value,
    load_config
)

from .credentials import (
    DockerCredentials,
    GitHubCredentials,
    CredentialManager,
    get_credential_manager,
    set_credential_manager
)

from .context import (
    DevOpsContext
)

from .guardrails import (
    security_guardrail,
    sensitive_info_guardrail,
    SecurityCheckOutput,
    SensitiveInfoOutput
)

__all__ = [
    # Config
    'get_config',
    'get_config_value',
    'set_config_value',
    'load_config',
    
    # Credentials
    'DockerCredentials',
    'GitHubCredentials',
    'CredentialManager',
    'get_credential_manager',
    'set_credential_manager',
    
    # Context
    'DevOpsContext',
    
    # Guardrails
    'security_guardrail',
    'sensitive_info_guardrail',
    'SecurityCheckOutput',
    'SensitiveInfoOutput'
]