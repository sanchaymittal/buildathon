"""
Credentials Module - Provides secure credential management for DevOps operations.

This module defines credential models and a credential manager for securely accessing
and managing GitHub and Docker credentials.
"""

import os
import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """Exception raised for credential-related errors."""
    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion or "Check your credential configuration."


class DockerCredentials(BaseModel):
    """Docker credentials model for remote Docker daemon."""
    base_url: Optional[str] = Field(None, description="Docker daemon URL")
    tls_verify: bool = Field(False, description="Verify TLS certificates")
    cert_path: Optional[str] = Field(None, description="Path to TLS certificate")


class GitHubCredentials(BaseModel):
    """GitHub credentials model."""
    token: str = Field(..., description="GitHub Personal Access Token")
    api_url: str = Field("https://api.github.com", description="GitHub API URL")


class CredentialManager:
    """
    Credential Manager for securely accessing and managing service credentials.
    """
    
    def __init__(self):
        """Initialize the credential manager."""
        self._docker_credentials: Optional[DockerCredentials] = None
        self._github_credentials: Optional[GitHubCredentials] = None
    
    def get_docker_credentials(self) -> DockerCredentials:
        """
        Get Docker credentials.
        
        Returns:
            DockerCredentials object
        """
        if self._docker_credentials is None:
            self._load_docker_credentials()
        return self._docker_credentials
    
    def get_github_credentials(self) -> GitHubCredentials:
        """
        Get GitHub credentials.
        
        Returns:
            GitHubCredentials object
        
        Raises:
            CredentialError: If GitHub credentials cannot be loaded
        """
        if self._github_credentials is None:
            self._load_github_credentials()
        return self._github_credentials
    
    def _load_docker_credentials(self) -> None:
        """
        Load Docker credentials from environment variables.
        """
        base_url = os.environ.get('DOCKER_BASE_URL')
        tls_verify = os.environ.get('DOCKER_TLS_VERIFY', 'false').lower() == 'true'
        cert_path = os.environ.get('DOCKER_CERT_PATH')

        self._docker_credentials = DockerCredentials(
            base_url=base_url,
            tls_verify=tls_verify,
            cert_path=cert_path,
        )
        logger.info("Docker credentials loaded")
    
    def _load_github_credentials(self) -> None:
        """
        Load GitHub credentials from environment variables.
        
        Raises:
            CredentialError: If GitHub credentials cannot be loaded
        """
        token = os.environ.get('GITHUB_TOKEN')
        api_url = os.environ.get('GITHUB_API_URL', 'https://api.github.com')
        
        if not token:
            credentials_file = os.path.expanduser('~/.devops/credentials.json')
            if os.path.exists(credentials_file):
                try:
                    with open(credentials_file, 'r') as f:
                        credentials = json.load(f)
                        if 'github' in credentials and 'token' in credentials['github']:
                            token = credentials['github']['token']
                            logger.info("GitHub credentials loaded from credentials file")
                except Exception as e:
                    logger.warning(f"Failed to load GitHub credentials from file: {e}")
        
        if not token:
            raise CredentialError(
                "No GitHub token found",
                "Set the GITHUB_TOKEN environment variable or add it to ~/.devops/credentials.json"
            )
        
        self._github_credentials = GitHubCredentials(
            token=token,
            api_url=api_url
        )
        logger.info("GitHub credentials loaded")


_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance."""
    global _credential_manager
    
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    
    return _credential_manager


def set_credential_manager(manager: CredentialManager) -> None:
    """Set the global credential manager instance."""
    global _credential_manager
    _credential_manager = manager