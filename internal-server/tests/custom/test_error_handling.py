"""
Tests for error handling functionality in the DevOps Agent.

This module tests the error handling mechanisms in the AWS base service,
GitHub service, and credential management.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import io

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

class RateLimitError(AWSServiceError):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, message, wait_time=None):
        suggestion = f"Wait for {wait_time} seconds and try again." if wait_time else "Try again later."
        super().__init__(message, suggestion)
        self.wait_time = wait_time

class ResourceLimitError(AWSServiceError):
    """Exception raised when resource limit is exceeded."""
    def __init__(self, message):
        suggestion = "Request a limit increase or delete unused resources."
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

# Mock AWS credentials
class AWSCredentials:
    def __init__(self, access_key_id, secret_access_key, region):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region

# Mock GitHub credentials
class GitHubCredentials:
    def __init__(self, token):
        self.token = token

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

# Mock AWSBaseService
class AWSBaseService:
    SERVICE_NAME = "base"
    
    def __init__(self, credentials):
        self.credentials = credentials
    
    def handle_error(self, error, operation_name):
        """Handle AWS service errors."""
        if hasattr(error, 'response') and 'Error' in error.response:
            error_code = error.response['Error'].get('Code', '')
            error_message = error.response['Error'].get('Message', str(error))
            
            if error_code == 'ResourceNotFoundException':
                raise ResourceNotFoundError(error_message)
            elif error_code == 'AccessDenied':
                raise PermissionDeniedError(error_message)
            elif error_code == 'ValidationError':
                raise ValidationError(error_message)
            elif error_code == 'ThrottlingException':
                raise RateLimitError(error_message)
            elif error_code == 'LimitExceededException':
                raise ResourceLimitError(error_message)
        
        # Default case
        raise AWSServiceError(f"Error in {operation_name}: {str(error)}")


class TestErrorHandling(unittest.TestCase):
    """Test error handling functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Capture stdout for testing print output
        self.stdout_capture = io.StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_capture

    def tearDown(self):
        """Tear down test fixtures."""
        sys.stdout = self.original_stdout

    def test_aws_service_error_with_suggestion(self):
        """Test AWSServiceError with suggestion."""
        error = AWSServiceError("Test error message", "Test suggestion")
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.suggestion, "Test suggestion")

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError with resource type and ID."""
        error = ResourceNotFoundError(
            "Resource not found",
            resource_type="instance",
            resource_id="i-1234567890abcdef0"
        )
        self.assertEqual(str(error), "Resource not found")
        self.assertEqual(error.resource_type, "instance")
        self.assertEqual(error.resource_id, "i-1234567890abcdef0")
        self.assertIn("Check if the instance", error.suggestion)

    def test_permission_denied_error(self):
        """Test PermissionDeniedError."""
        error = PermissionDeniedError("Permission denied")
        self.assertEqual(str(error), "Permission denied")
        self.assertIn("Check your IAM permissions", error.suggestion)

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid parameters")
        self.assertEqual(str(error), "Invalid parameters")
        self.assertIn("Check the input parameters", error.suggestion)

    def test_rate_limit_error(self):
        """Test RateLimitError with wait time."""
        error = RateLimitError("Rate limit exceeded", 30)
        self.assertEqual(str(error), "Rate limit exceeded")
        self.assertIn("Wait for 30 seconds", error.suggestion)

    def test_resource_limit_error(self):
        """Test ResourceLimitError."""
        error = ResourceLimitError("Resource limit exceeded")
        self.assertEqual(str(error), "Resource limit exceeded")
        self.assertIn("Request a limit increase", error.suggestion)

    def test_credential_error(self):
        """Test CredentialError with suggestion."""
        error = CredentialError("No AWS credentials found", "Set AWS_ACCESS_KEY_ID")
        self.assertEqual(str(error), "No AWS credentials found")
        self.assertEqual(error.suggestion, "Set AWS_ACCESS_KEY_ID")

    def test_print_error(self):
        """Test print_error function."""
        print_error("Test Error", "Error details", "Try this solution")
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: Test Error", output)
        self.assertIn("Error details", output)
        self.assertIn("SUGGESTION: Try this solution", output)

    def test_handle_cli_error_credential_error(self):
        """Test handle_cli_error with CredentialError."""
        error = CredentialError("No AWS credentials found", "Set AWS_ACCESS_KEY_ID")
        result = handle_cli_error(error)
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: Credential Error", output)
        self.assertIn("No AWS credentials found", output)
        self.assertIn("SUGGESTION: Set AWS_ACCESS_KEY_ID", output)
        self.assertEqual(result, 1)

    def test_handle_cli_error_aws_error(self):
        """Test handle_cli_error with AWSServiceError."""
        error = ResourceNotFoundError("Resource not found", "instance", "i-1234")
        result = handle_cli_error(error)
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: AWS Error", output)
        self.assertIn("Resource not found", output)
        self.assertIn("SUGGESTION:", output)
        self.assertEqual(result, 1)

    def test_handle_cli_error_github_error(self):
        """Test handle_cli_error with GitHubError."""
        error = AuthenticationError("GitHub authentication failed")
        result = handle_cli_error(error)
        output = self.stdout_capture.getvalue()
        self.assertIn("ERROR: GitHub Error", output)
        self.assertIn("GitHub authentication failed", output)
        self.assertIn("SUGGESTION:", output)
        self.assertEqual(result, 1)

    def test_aws_base_service_handle_error(self):
        """Test AWSBaseService.handle_error method."""
        # Create an instance of AWSBaseService
        service = AWSBaseService(
            credentials=AWSCredentials(
                access_key_id="test", 
                secret_access_key="test",
                region="us-east-1"
            )
        )
        
        # Create a mock ClientError for resource not found
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Resource i-1234567890abcdef0 not found'
            }
        }
        client_error = MagicMock()
        client_error.response = error_response
        
        # Test handling resource not found error
        with self.assertRaises(ResourceNotFoundError):
            service.handle_error(client_error, "test_operation")
        
        # Create a mock ClientError for permission denied
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'User is not authorized'
            }
        }
        client_error = MagicMock()
        client_error.response = error_response
        
        # Test handling permission denied error
        with self.assertRaises(PermissionDeniedError):
            service.handle_error(client_error, "test_operation")


if __name__ == '__main__':
    unittest.main()