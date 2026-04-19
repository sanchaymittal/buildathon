"""
Base Docker Service - Provides common functionality for Docker service operations.

This module defines the base class and exception hierarchy for Docker operations.
"""

import logging
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class DockerServiceError(Exception):
    """Base exception for Docker service errors."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class ContainerNotFoundError(DockerServiceError):
    """Exception raised when a container is not found."""

    def __init__(self, container_id: str):
        suggestion = f"Check if the container '{container_id}' exists. Use 'docker ps -a' to list all containers."
        super().__init__(f"Container '{container_id}' not found", suggestion)
        self.container_id = container_id


class ImageNotFoundError(DockerServiceError):
    """Exception raised when an image is not found."""

    def __init__(self, image: str):
        suggestion = f"Check if the image '{image}' exists. Use 'docker images' to list all images."
        super().__init__(f"Image '{image}' not found", suggestion)
        self.image = image


class ImageBuildError(DockerServiceError):
    """Exception raised when image build fails."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        suggestion = suggestion or "Check the Dockerfile and build logs for errors."
        super().__init__(message, suggestion)


class ContainerStartError(DockerServiceError):
    """Exception raised when container start fails."""

    def __init__(self, container_id: str, message: str):
        suggestion = f"Check if the image exists and container logs for errors: docker logs {container_id}"
        super().__init__(f"Failed to start container '{container_id}': {message}", suggestion)
        self.container_id = container_id


class ContainerStopError(DockerServiceError):
    """Exception raised when container stop fails."""

    def __init__(self, container_id: str, message: str):
        suggestion = f"Check if the container is running: docker inspect {container_id}"
        super().__init__(f"Failed to stop container '{container_id}': {message}", suggestion)
        self.container_id = container_id


class DockerDaemonError(DockerServiceError):
    """Exception raised when Docker daemon is unreachable."""

    def __init__(self, message: str):
        suggestion = "Ensure Docker daemon is running: docker info"
        super().__init__(f"Docker daemon error: {message}", suggestion)


class PortAllocationError(DockerServiceError):
    """Exception raised when port allocation fails."""

    def __init__(self, message: str):
        suggestion = "Try a different host port or release conflicting ports."
        super().__init__(message, suggestion)


class RepositoryError(DockerServiceError):
    """Exception raised when repository operations fail."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        suggestion = suggestion or "Check the repository URL and your GitHub token."
        super().__init__(message, suggestion)


def docker_operation(operation_name: Optional[str] = None):
    """
    Decorator for Docker operations that handles common errors.

    Args:
        operation_name: Name of the operation, defaults to the function name.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = operation_name or func.__name__
            try:
                return func(*args, **kwargs)
            except DockerServiceError:
                raise
            except Exception as e:
                error_msg = str(e)
                if "docker" in error_msg.lower() or "connection" in error_msg.lower():
                    raise DockerDaemonError(error_msg)
                elif "not found" in error_msg.lower():
                    if "container" in error_msg.lower():
                        raise ContainerNotFoundError(error_msg)
                    elif "image" in error_msg.lower():
                        raise ImageNotFoundError(error_msg)
                raise DockerServiceError(f"{op_name} failed: {error_msg}")
        return wrapper
    return decorator