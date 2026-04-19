"""
GitHub Package - Provides functionality for GitHub service operations.

This package includes modules for repositories, issues, pull requests, and other
GitHub resources, with integration for the Gemini Agents SDK.
"""

from .github_models import (
    GitHubRepoRequest,
    GitHubIssueRequest,
    GitHubCreateIssueRequest,
    GitHubPRRequest,
    GitHubRepository,
    GitHubIssue,
    GitHubPullRequest
)

from .github import (
    GitHubService,
    GitHubError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
    RateLimitError,
)

from .github_tools import (
    get_repository,
    list_issues,
    create_issue,
    list_pull_requests
)

__all__ = [
    # GitHub Models
    'GitHubRepoRequest',
    'GitHubIssueRequest',
    'GitHubCreateIssueRequest',
    'GitHubPRRequest',
    'GitHubRepository',
    'GitHubIssue',
    'GitHubPullRequest',

    # GitHub Service
    'GitHubService',
    'GitHubError',
    'AuthenticationError',
    'ResourceNotFoundError',
    'ValidationError',
    'RateLimitError',
    
    # GitHub Tools
    'get_repository',
    'list_issues',
    'create_issue',
    'list_pull_requests'
]
