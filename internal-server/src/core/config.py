"""
Configuration Module - Provides configuration management for DevOps operations.

This module defines functions for loading, accessing, and managing configuration
settings from various sources including environment variables, config files, and
command-line arguments.
"""

import os
import json
import logging
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


# Custom exceptions
class ConfigError(Exception):
    """Exception raised for configuration errors."""

    pass


# Default configuration
DEFAULT_CONFIG = {
    "docker": {
        "base_url": None,
        "workspace_dir": "/tmp/devops-deploys",
        "default_network": "bridge",
        "default_restart_policy": "unless-stopped",
    },
    "github": {"organization": None, "api_url": "https://api.github.com"},
    "gemini": {
        "model": "gemini-2.5-flash",
        "temperature": 0.2,
        "max_tool_calls": 16,
        "api_base": None,
    },
    "agent": {
        "log_file": "~/.devops/agent.log",
        "session_ttl_seconds": 3600,
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
}

# Global configuration
_config: Dict[str, Any] = {}
_config_loaded = False


def load_config(
    config_file: Optional[str] = None,
    env_prefix: str = "DEVOPS",
    merge_defaults: bool = True,
) -> Dict[str, Any]:
    """
    Load configuration from file and environment variables.

    Args:
        config_file: Path to configuration file
        env_prefix: Prefix for environment variables
        merge_defaults: Whether to merge with default configuration

    Returns:
        Loaded configuration dictionary
    """
    global _config, _config_loaded

    # Start with default configuration if requested
    if merge_defaults:
        _config = DEFAULT_CONFIG.copy()
    else:
        _config = {}

    # Load from configuration file if provided
    if config_file:
        file_config = _load_config_file(config_file)
        _deep_merge(_config, file_config)

    # Load from environment variables
    env_config = _load_from_env(env_prefix)
    _deep_merge(_config, env_config)

    _config_loaded = True
    return _config


def _load_config_file(config_file: str) -> Dict[str, Any]:
    """
    Load configuration from file.

    Args:
        config_file: Path to configuration file

    Returns:
        Configuration dictionary from file

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If configuration file format is not supported
    """
    config_path = Path(config_file).expanduser()

    if not config_path.exists():
        logger.warning(f"Configuration file {config_file} not found")
        return {}

    try:
        with open(config_path, "r") as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                return yaml.safe_load(f) or {}
            elif config_path.suffix.lower() == ".json":
                return json.load(f)
            else:
                raise ValueError(
                    f"Unsupported configuration file format: {config_path.suffix}"
                )
    except Exception as e:
        logger.error(f"Failed to load configuration file: {e}")
        return {}


def _load_from_env(prefix: str) -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Environment variables are converted to nested dictionaries based on double underscore
    separators. For example, DEVOPS_DOCKER__BASE_URL becomes
    {'docker': {'base_url': value}}.

    Args:
        prefix: Prefix for environment variables

    Returns:
        Configuration dictionary from environment variables
    """
    config = {}

    for key, value in os.environ.items():
        # Check if the environment variable has the correct prefix
        if not key.startswith(f"{prefix}_"):
            continue

        # Remove prefix and split by double underscore
        key_without_prefix = key[len(prefix) + 1 :]
        parts = key_without_prefix.split("__")

        # Convert value to appropriate type
        typed_value = _convert_value(value)

        # Build nested dictionary
        current = config
        for i, part in enumerate(parts):
            part = part.lower()
            if i == len(parts) - 1:
                # Last part is the actual key
                current[part] = typed_value
            else:
                # Create nested dictionary if it doesn't exist
                if part not in current:
                    current[part] = {}
                current = current[part]

    return config


def _convert_value(value: str) -> Union[str, int, float, bool, List[str], None]:
    """
    Convert string value to appropriate type.

    Args:
        value: String value to convert

    Returns:
        Converted value
    """
    # Check for None/null
    if value.lower() in ["none", "null"]:
        return None

    # Check for boolean
    if value.lower() in ["true", "yes", "y", "1"]:
        return True
    if value.lower() in ["false", "no", "n", "0"]:
        return False

    # Check for integer
    try:
        return int(value)
    except ValueError:
        pass

    # Check for float
    try:
        return float(value)
    except ValueError:
        pass

    # Check for list (comma-separated values)
    if "," in value:
        return [item.strip() for item in value.split(",")]

    # Default to string
    return value


def _deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        target: Target dictionary to merge into
        source: Source dictionary to merge from

    Returns:
        Merged dictionary
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            _deep_merge(target[key], value)
        else:
            # Replace or add value
            target[key] = value

    return target


def get_config() -> Dict[str, Any]:
    """
    Get the current configuration.

    Returns:
        Current configuration dictionary
    """
    global _config, _config_loaded

    if not _config_loaded:
        # Load configuration with default settings
        config_file = os.environ.get("DEVOPS_CONFIG_FILE", "~/.devops/config.yaml")
        load_config(config_file)

    return _config


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Get a configuration value by key path.

    Args:
        key_path: Dot-separated path to the configuration value
        default: Default value if key doesn't exist

    Returns:
        Configuration value or default
    """
    config = get_config()
    keys = key_path.split(".")

    # Navigate through the nested dictionaries
    current = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]

    return current


def set_config_value(key_path: str, value: Any) -> None:
    """
    Set a configuration value by key path.

    Args:
        key_path: Dot-separated path to the configuration value
        value: Value to set
    """
    config = get_config()
    keys = key_path.split(".")

    # Navigate through the nested dictionaries
    current = config
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            # Last key, set the value
            current[key] = value
        else:
            # Create nested dictionary if it doesn't exist
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
