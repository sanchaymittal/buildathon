"""Unit tests for credential management."""

import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from src.core.credentials import (
    CredentialManager,
    CredentialError,
    DockerCredentials,
    GitHubCredentials,
    get_credential_manager,
)


def test_docker_credentials_from_env(monkeypatch):
    """Docker credentials should read environment variables."""
    monkeypatch.setenv("DOCKER_BASE_URL", "unix:///var/run/docker.sock")
    monkeypatch.setenv("DOCKER_TLS_VERIFY", "true")
    monkeypatch.setenv("DOCKER_CERT_PATH", "/tmp/certs")

    manager = CredentialManager()
    creds = manager.get_docker_credentials()

    assert isinstance(creds, DockerCredentials)
    assert creds.base_url == "unix:///var/run/docker.sock"
    assert creds.tls_verify is True
    assert creds.cert_path == "/tmp/certs"


def test_docker_credentials_default(monkeypatch):
    """Docker credentials default to None values when env not set."""
    monkeypatch.delenv("DOCKER_BASE_URL", raising=False)
    monkeypatch.delenv("DOCKER_TLS_VERIFY", raising=False)
    monkeypatch.delenv("DOCKER_CERT_PATH", raising=False)

    manager = CredentialManager()
    creds = manager.get_docker_credentials()

    assert creds.base_url is None
    assert creds.tls_verify is False
    assert creds.cert_path is None


def test_github_credentials_from_env(monkeypatch):
    """GitHub credentials should load from environment variables."""
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    monkeypatch.setenv("GITHUB_API_URL", "https://example.com/api")

    manager = CredentialManager()
    creds = manager.get_github_credentials()

    assert isinstance(creds, GitHubCredentials)
    assert creds.token == "env-token"
    assert creds.api_url == "https://example.com/api"


def test_github_credentials_from_file(monkeypatch):
    """GitHub credentials fall back to credentials file."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    credentials_data = {"github": {"token": "file-token"}}
    fake_path = Path("/home/user/.devops/credentials.json")

    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", mock_open(read_data=json.dumps(credentials_data))
    ):
        manager = CredentialManager()
        with patch("os.path.expanduser", return_value=str(fake_path)):
            creds = manager.get_github_credentials()

    assert creds.token == "file-token"


def test_github_credentials_missing(monkeypatch):
    """Missing GitHub credentials should raise CredentialError."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with patch("os.path.exists", return_value=False):
        manager = CredentialManager()
        with pytest.raises(CredentialError):
            manager.get_github_credentials()


def test_get_credential_manager_singleton():
    """Global credential manager should behave as singleton."""
    manager1 = get_credential_manager()
    manager2 = get_credential_manager()

    assert manager1 is manager2
