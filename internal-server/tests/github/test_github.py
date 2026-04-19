"""
Unit tests for the GitHub service module.

These tests use the unittest.mock library to mock GitHub API calls
and test the GitHubService class without making actual GitHub API calls.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
import json

from src.github.github import GitHubService
from src.core.credentials import GitHubCredentials

# Test data
TEST_REPO_OWNER = "test-owner"
TEST_REPO_NAME = "test-repo"
TEST_BRANCH = "main"
TEST_TOKEN = "test-token"


@pytest.fixture
def github_credentials():
    """Create a test GitHub credentials object."""
    return GitHubCredentials(token=TEST_TOKEN)


@pytest.fixture
def github_service(github_credentials):
    """Create a test GitHub service with mock credentials."""
    # Create a mock service that doesn't make actual API calls
    with patch.object(GitHubService, '_verify_access', return_value=None):
        # Create the service with the test token
        service = GitHubService(token=github_credentials.token)
        
        # Mock the _make_request method to avoid making actual API calls
        service._make_request = MagicMock()
        
        return service


def test_get_repository(github_service):
    """Test getting a repository."""
    # Mock response
    mock_response = {
        "id": 12345,
        "name": TEST_REPO_NAME,
        "full_name": f"{TEST_REPO_OWNER}/{TEST_REPO_NAME}",
        "description": "Test repository",
        "default_branch": TEST_BRANCH
    }
    github_service._make_request.return_value = mock_response

    # Call the method
    repo = github_service.get_repository(TEST_REPO_NAME, owner=TEST_REPO_OWNER)

    # Verify the request
    github_service._make_request.assert_called_once_with(
        "GET", 
        f"repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}", 
        use_cache=True
    )

    # Verify the result
    assert repo["name"] == TEST_REPO_NAME
    assert repo["full_name"] == f"{TEST_REPO_OWNER}/{TEST_REPO_NAME}"


def test_list_repositories(github_service):
    """Test listing repositories."""
    # Mock response
    mock_response = [
        {
            "id": 12345,
            "name": "repo1",
            "full_name": f"{TEST_REPO_OWNER}/repo1",
            "description": "Test repository 1"
        },
        {
            "id": 67890,
            "name": "repo2",
            "full_name": f"{TEST_REPO_OWNER}/repo2",
            "description": "Test repository 2"
        }
    ]
    github_service._make_request.return_value = mock_response

    # Call the method with org parameter
    repos = github_service.list_repositories(org=TEST_REPO_OWNER)

    # Verify the request
    github_service._make_request.assert_called_once_with(
        "GET", 
        f"orgs/{TEST_REPO_OWNER}/repos", 
        params={
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100,
            'type': 'all',
            'page': 1
        }, 
        use_cache=True
    )

    # Verify the result
    assert len(repos) == 2
    assert repos[0]["name"] == "repo1"
    assert repos[1]["name"] == "repo2"

    # Reset mock
    github_service._make_request.reset_mock()

    # Mock response for user repos
    github_service._make_request.return_value = mock_response

    # Call the method with user parameter
    repos = github_service.list_repositories(user=TEST_REPO_OWNER)

    # Verify the request
    github_service._make_request.assert_called_once_with(
        "GET", 
        f"users/{TEST_REPO_OWNER}/repos", 
        params={
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100,
            'type': 'all',
            'page': 1
        }, 
        use_cache=True
    )


def test_get_readme(github_service):
    """Test getting a repository README."""
    # Mock response
    mock_response = {
        "content": "IyBUZXN0IFJlcG9zaXRvcnkKClRoaXMgaXMgYSB0ZXN0IHJlcG9zaXRvcnku",  # Base64 encoded "# Test Repository\n\nThis is a test repository."
        "encoding": "base64",
        "decoded_content": "# Test Repository\n\nThis is a test repository."
    }
    github_service._make_request.return_value = mock_response

    # Call the method
    readme = github_service.get_readme(TEST_REPO_NAME, owner=TEST_REPO_OWNER)

    # Verify the request
    github_service._make_request.assert_called_once_with(
        "GET", 
        f"repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/readme", 
        params={}, 
        use_cache=True
    )

    # Verify the result
    assert "content" in readme
    assert readme["decoded_content"] == "# Test Repository\n\nThis is a test repository."


def test_list_branches(github_service):
    """Test listing repository branches."""
    # Mock response
    mock_response = [
        {
            "name": "main",
            "commit": {
                "sha": "abc123",
                "url": f"https://api.github.com/repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/commits/abc123"
            },
            "protected": True
        },
        {
            "name": "develop",
            "commit": {
                "sha": "def456",
                "url": f"https://api.github.com/repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/commits/def456"
            },
            "protected": False
        }
    ]
    github_service._make_request.return_value = mock_response

    # Call the method
    branches = github_service.list_branches(TEST_REPO_NAME, owner=TEST_REPO_OWNER)

    # Verify the request
    github_service._make_request.assert_called_once_with(
        "GET", 
        f"repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/branches", 
        params={}, 
        use_cache=True
    )

    # Verify the result
    assert len(branches) == 2
    assert branches[0]["name"] == "main"
    assert branches[1]["name"] == "develop"


def test_get_content(github_service):
    """Test getting file content from a repository."""
    # Mock response
    mock_response = {
        "content": "Y29uc3QgaGVsbG8gPSAid29ybGQiOw==",  # Base64 encoded "const hello = "world";"
        "encoding": "base64",
        "name": "example.js",
        "path": "src/example.js",
        "sha": "abc123",
        "decoded_content": 'const hello = "world";'
    }
    github_service._make_request.return_value = mock_response

    # Call the method
    file_content = github_service.get_content(
        TEST_REPO_NAME,
        "src/example.js",
        owner=TEST_REPO_OWNER,
        ref=TEST_BRANCH
    )

    # Verify the request
    github_service._make_request.assert_called_once_with(
        "GET", 
        f"repos/{TEST_REPO_OWNER}/{TEST_REPO_NAME}/contents/src/example.js", 
        params={'ref': TEST_BRANCH}, 
        use_cache=True
    )

    # Verify the result
    assert file_content["name"] == "example.js"
    assert file_content["path"] == "src/example.js"
    assert file_content["decoded_content"] == 'const hello = "world";'


def test_error_handling(github_service):
    """Test error handling in the GitHub service."""
    # Mock error response
    from src.github.github import ResourceNotFoundError
    
    # Configure the mock to raise an exception
    github_service._make_request.side_effect = ResourceNotFoundError("GitHub resource not found: repos/test-owner/test-repo")
    
    # Call the method and expect an exception
    with pytest.raises(ResourceNotFoundError) as excinfo:
        github_service.get_repository(TEST_REPO_NAME, owner=TEST_REPO_OWNER)
    
    # Verify the exception message
    assert "GitHub resource not found" in str(excinfo.value)