"""
Tests for error handling functionality in the DevOps Agent.

This module exercises error-handling behavior in a generic cloud service,
the GitHub service, and credential management utilities.
"""

import unittest
from unittest.mock import MagicMock
import sys
import io


class CloudServiceError(Exception):
    """Base exception for cloud service errors."""

    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion or "Review your cloud configuration and try again."


class ResourceNotFoundError(CloudServiceError):
    """Raised when an expected resource cannot be located."""

    def __init__(self, message, resource_type=None, resource_id=None):
        suggestion = (
            f"Confirm the {resource_type} '{resource_id}' exists in your cloud environment."
            if resource_type and resource_id
            else "Confirm the resource exists in your cloud environment."
        )
        super().__init__(message, suggestion)
        self.resource_type = resource_type
        self.resource_id = resource_id


class PermissionDeniedError(CloudServiceError):
    """Raised when permission is denied."""

    def __init__(self, message):
        suggestion = "Verify role permissions and ensure the account has the required access."
        super().__init__(message, suggestion)


class ValidationError(CloudServiceError):
    """Raised when validation fails."""

    def __init__(self, message):
        suggestion = "Inspect the supplied parameters and confirm they meet service requirements."
        super().__init__(message, suggestion)


class RateLimitError(CloudServiceError):
    """Raised when a service throttles requests."""

    def __init__(self, message, wait_time=None):
        suggestion = (
            f"Wait for {wait_time} seconds and retry."
            if wait_time
            else "Wait briefly before retrying."
        )
        super().__init__(message, suggestion)
        self.wait_time = wait_time


class ResourceLimitError(CloudServiceError):
    """Raised when a quota or resource ceiling is exceeded."""

    def __init__(self, message):
        suggestion = "Request a quota increase or free unused capacity."
        super().__init__(message, suggestion)


class GitHubError(Exception):
    """Base exception for GitHub service errors."""

    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion or "Check your GitHub configuration and try again."


class AuthenticationError(GitHubError):
    """Raised when GitHub authentication fails."""

    def __init__(self, message):
        suggestion = "Confirm your GitHub token is valid and has the required scopes."
        super().__init__(message, suggestion)


class CredentialError(Exception):
    """Raised when credential retrieval fails."""

    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion or "Review your credential configuration."


class CloudCredentials:
    """Simple credentials container used by the tests."""

    def __init__(self, access_key_id, secret_key, region):
        self.access_key_id = access_key_id
        self.secret_key = secret_key
        self.region = region


class GitHubCredentials:
    """Simple GitHub credentials container."""

    def __init__(self, token):
        self.token = token


def print_error(error_type, message, suggestion=None):
    """Print an error message with an optional suggestion."""

    print(f"ERROR: {error_type}")
    print(message)
    if suggestion:
        print(f"SUGGESTION: {suggestion}")


def handle_cli_error(error):
    """Handle CLI errors and standardise exit codes."""

    if isinstance(error, CredentialError):
        print_error("Credential Error", str(error), error.suggestion)
    elif isinstance(error, CloudServiceError):
        print_error("Cloud Error", str(error), error.suggestion)
    elif isinstance(error, GitHubError):
        print_error("GitHub Error", str(error), error.suggestion)
    else:
        print_error("Unexpected Error", str(error))

    return 1


class CloudBaseService:
    """Minimal base service that wraps error translation logic."""

    SERVICE_NAME = "base"

    def __init__(self, credentials):
        self.credentials = credentials

    def handle_error(self, error, operation_name):
        """Translate service responses into explicit error types."""

        if hasattr(error, "response") and "error" in error.response:
            info = error.response["error"]
            code = info.get("code", "")
            message = info.get("message", str(error))

            if code == "ResourceMissing":
                raise ResourceNotFoundError(message)
            if code == "AccessDenied":
                raise PermissionDeniedError(message)
            if code == "ValidationFailed":
                raise ValidationError(message)
            if code == "Throttled":
                raise RateLimitError(message)
            if code == "QuotaExceeded":
                raise ResourceLimitError(message)

        raise CloudServiceError(f"Error in {operation_name}: {error}")


class TestErrorHandling(unittest.TestCase):
    """Test error handling functionality."""

    def setUp(self):
        self.stdout_capture = io.StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_capture

    def tearDown(self):
        sys.stdout = self.original_stdout

    def test_cloud_service_error_with_suggestion(self):
        error = CloudServiceError("Test error message", "Test suggestion")
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.suggestion, "Test suggestion")

    def test_resource_not_found_error(self):
        error = ResourceNotFoundError(
            "Resource not found",
            resource_type="container",
            resource_id="container-1234",
        )
        self.assertEqual(str(error), "Resource not found")
        self.assertEqual(error.resource_type, "container")
        self.assertEqual(error.resource_id, "container-1234")
        self.assertIn("cloud environment", error.suggestion)

    def test_permission_denied_error(self):
        error = PermissionDeniedError("Permission denied")
        self.assertEqual(str(error), "Permission denied")
        self.assertIn("role permissions", error.suggestion)

    def test_validation_error(self):
        error = ValidationError("Invalid parameters")
        self.assertEqual(str(error), "Invalid parameters")
        self.assertIn("supplied parameters", error.suggestion)

    def test_rate_limit_error(self):
        error = RateLimitError("Rate limit exceeded", 30)
        self.assertEqual(str(error), "Rate limit exceeded")
        self.assertIn("Wait for 30 seconds", error.suggestion)

    def test_resource_limit_error(self):
        error = ResourceLimitError("Resource limit exceeded")
        self.assertEqual(str(error), "Resource limit exceeded")
        self.assertIn("quota increase", error.suggestion)

    def test_credential_error(self):
        error = CredentialError("No cloud credentials found", "Set CLOUD_ACCESS_KEY")
        self.assertEqual(str(error), "No cloud credentials found")
        self.assertEqual(error.suggestion, "Set CLOUD_ACCESS_KEY")

    def test_print_error(self):
        print_error("Test Error", "Error details", "Try this solution")
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: Test Error", output)
        self.assertIn("Error details", output)
        self.assertIn("SUGGESTION: Try this solution", output)

    def test_handle_cli_error_credential_error(self):
        error = CredentialError("No cloud credentials found", "Set CLOUD_ACCESS_KEY")
        result = handle_cli_error(error)
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: Credential Error", output)
        self.assertIn("No cloud credentials found", output)
        self.assertIn("SUGGESTION: Set CLOUD_ACCESS_KEY", output)
        self.assertEqual(result, 1)

    def test_handle_cli_error_cloud_error(self):
        error = ResourceNotFoundError("Resource not found", "container", "container-1")
        result = handle_cli_error(error)
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: Cloud Error", output)
        self.assertIn("Resource not found", output)
        self.assertIn("SUGGESTION:", output)
        self.assertEqual(result, 1)

    def test_handle_cli_error_github_error(self):
        error = AuthenticationError("GitHub authentication failed")
        result = handle_cli_error(error)
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: GitHub Error", output)
        self.assertIn("GitHub authentication failed", output)
        self.assertIn("SUGGESTION:", output)
        self.assertEqual(result, 1)

    def test_cloud_base_service_handle_error(self):
        service = CloudBaseService(
            credentials=CloudCredentials(
                access_key_id="key", secret_key="secret", region="local"
            )
        )

        error_response = {
            "error": {
                "code": "ResourceMissing",
                "message": "Container container-1234 not found",
            }
        }
        client_error = MagicMock()
        client_error.response = error_response

        with self.assertRaises(ResourceNotFoundError):
            service.handle_error(client_error, "test_operation")

        error_response = {
            "error": {
                "code": "AccessDenied",
                "message": "Caller not authorised",
            }
        }
        client_error = MagicMock()
        client_error.response = error_response

        with self.assertRaises(PermissionDeniedError):
            service.handle_error(client_error, "test_operation")


if __name__ == "__main__":
    unittest.main()
