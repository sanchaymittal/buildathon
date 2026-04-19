"""
Script to test CLI error handling.
"""

import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Define error classes
class AWSServiceError(Exception):
    """Base exception for AWS service errors."""
    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion or "Check your AWS configuration and try again."

class ResourceNotFoundError(AWSServiceError):
    """Exception raised when a resource is not found."""
    def __init__(self, message, resource_type=None, resource_id=None):
        suggestion = f"Check if the {resource_type} '{resource_id}' exists in your AWS account."
        super().__init__(message, suggestion)
        self.resource_type = resource_type
        self.resource_id = resource_id

class PermissionDeniedError(AWSServiceError):
    """Exception raised when permission is denied."""
    def __init__(self, message):
        suggestion = "Check your IAM permissions and ensure you have the necessary access."
        super().__init__(message, suggestion)

class ValidationError(AWSServiceError):
    """Exception raised when input validation fails."""
    def __init__(self, message):
        suggestion = "Check the input parameters and ensure they meet the requirements."
        super().__init__(message, suggestion)

class GitHubError(Exception):
    """Base exception for GitHub service errors."""
    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion or "Check your GitHub configuration and try again."

class AuthenticationError(GitHubError):
    """Exception raised when authentication fails."""
    def __init__(self, message):
        suggestion = "Check your GitHub token and ensure it has the necessary permissions."
        super().__init__(message, suggestion)

class CredentialError(Exception):
    """Exception raised when there's an issue with credentials."""
    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion or "Check your credential configuration."

# Error handling functions
def print_error(error_type, message, suggestion=None):
    """Print an error message with optional suggestion."""
    print(f"ERROR: {error_type}")
    print(f"{message}")
    if suggestion:
        print(f"SUGGESTION: {suggestion}")

def handle_cli_error(error):
    """Handle CLI errors and return appropriate exit code."""
    if isinstance(error, CredentialError):
        print_error("Credential Error", str(error), error.suggestion)
    elif isinstance(error, AWSServiceError):
        print_error("AWS Error", str(error), error.suggestion)
    elif isinstance(error, GitHubError):
        print_error("GitHub Error", str(error), error.suggestion)
    else:
        print_error("Unexpected Error", str(error))
    
    return 1

# Mock CLI functions that raise errors
def ec2_command_with_error():
    """EC2 command that raises an error."""
    raise ResourceNotFoundError(
        "Instance not found",
        resource_type="instance",
        resource_id="i-1234567890abcdef0"
    )

def github_command_with_error():
    """GitHub command that raises an error."""
    raise AuthenticationError("GitHub authentication failed")

def credential_command_with_error():
    """Credential command that raises an error."""
    raise CredentialError(
        "No AWS credentials found",
        "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
    )

# Test classes
class TestCLIErrorHandling(unittest.TestCase):
    """Tests for CLI error handling."""
    
    def test_handle_resource_not_found_error(self):
        """Test handling ResourceNotFoundError."""
        with patch('sys.stdout'):
            error = ResourceNotFoundError(
                "Instance not found",
                resource_type="instance",
                resource_id="i-1234567890abcdef0"
            )
            result = handle_cli_error(error)
            self.assertEqual(result, 1)
    
    def test_handle_permission_denied_error(self):
        """Test handling PermissionDeniedError."""
        with patch('sys.stdout'):
            error = PermissionDeniedError("Permission denied")
            result = handle_cli_error(error)
            self.assertEqual(result, 1)
    
    def test_handle_validation_error(self):
        """Test handling ValidationError."""
        with patch('sys.stdout'):
            error = ValidationError("Invalid parameters")
            result = handle_cli_error(error)
            self.assertEqual(result, 1)
    
    def test_handle_github_authentication_error(self):
        """Test handling AuthenticationError."""
        with patch('sys.stdout'):
            error = AuthenticationError("GitHub authentication failed")
            result = handle_cli_error(error)
            self.assertEqual(result, 1)
    
    def test_handle_credential_error(self):
        """Test handling CredentialError."""
        with patch('sys.stdout'):
            error = CredentialError(
                "No AWS credentials found",
                "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
            )
            result = handle_cli_error(error)
            self.assertEqual(result, 1)
    
    def test_ec2_command_error(self):
        """Test EC2 command that raises an error."""
        with patch('sys.stdout'), self.assertRaises(ResourceNotFoundError):
            ec2_command_with_error()
    
    def test_github_command_error(self):
        """Test GitHub command that raises an error."""
        with patch('sys.stdout'), self.assertRaises(AuthenticationError):
            github_command_with_error()
    
    def test_credential_command_error(self):
        """Test credential command that raises an error."""
        with patch('sys.stdout'), self.assertRaises(CredentialError):
            credential_command_with_error()

if __name__ == "__main__":
    # Run the tests
    unittest.main()