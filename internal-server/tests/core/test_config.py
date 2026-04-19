"""Tests for configuration management helpers."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.core import config as config_module


def reset_config_state():
    """Helper to reset module globals between tests."""
    config_module._config = {}
    config_module._config_loaded = False


@pytest.fixture(autouse=True)
def _reset_config():
    reset_config_state()
    yield
    reset_config_state()


def test_load_config_merges_defaults_and_env(monkeypatch):
    monkeypatch.setenv("DEVOPS_DOCKER__BASE_URL", "unix:///tmp/docker.sock")
    monkeypatch.setenv("DEVOPS_GITHUB__ORGANIZATION", "my-org")

    cfg = config_module.load_config(merge_defaults=True)

    assert cfg["docker"]["base_url"] == "unix:///tmp/docker.sock"
    assert cfg["github"]["organization"] == "my-org"
    assert cfg["docker"]["workspace_dir"] == "/tmp/devops-deploys"


def test_get_config_value(monkeypatch):
    config_module._config = {
        "docker": {"base_url": "unix:///var/run/docker.sock"},
        "github": {"organization": "agentics"},
    }
    config_module._config_loaded = True

    assert config_module.get_config_value("docker.base_url") == "unix:///var/run/docker.sock"
    assert config_module.get_config_value("github.organization") == "agentics"
    assert config_module.get_config_value("logging.level", default="INFO") == "INFO"
    assert config_module.get_config_value("missing.path") is None


def test_set_config_value_creates_nested(monkeypatch):
    config_module._config = {}
    config_module._config_loaded = True

    config_module.set_config_value("docker.base_url", "unix:///var/run/docker.sock")
    config_module.set_config_value("github.organization", "agentics")

    assert config_module._config["docker"]["base_url"] == "unix:///var/run/docker.sock"
    assert config_module._config["github"]["organization"] == "agentics"


def test_load_config_reads_file(monkeypatch):
    config_file = Path("/tmp/config.json")
    monkeypatch.setenv("DEVOPS_CONFIG_FILE", str(config_file))

    file_data = json.dumps({"github": {"organization": "file-org"}})

    with patch("builtins.open", mock_open(read_data=file_data)), patch(
        "pathlib.Path.exists", return_value=True
    ):
        cfg = config_module.load_config(merge_defaults=True)

    assert cfg["github"]["organization"] == "file-org"
