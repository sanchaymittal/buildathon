"""
GitHub Tools Module - Provides function tools for GitHub operations with OpenAI Agents SDK.

This module implements function tools for getting repository details, listing issues,
creating issues, and listing pull requests, designed to be used with the OpenAI Agents SDK.
"""

import github
import logging
from typing import Dict, List, Any, Optional

from agents import function_tool, RunContextWrapper

from .github_models import (
    GitHubRepoRequest,
    GitHubIssueRequest,
    GitHubCreateIssueRequest,
    GitHubPRRequest,
    GitHubRepository,
    GitHubIssue,
    GitHubPullRequest
)
from ..core.context import DevOpsContext

# Configure logging
logger = logging.getLogger(__name__)


@function_tool()
async def get_repository(
    ctx: RunContextWrapper[DevOpsContext],
    request: GitHubRepoRequest
) -> GitHubRepository:
    """
    Get GitHub repository information.
    
    Args:
        ctx: Run context containing DevOpsContext
        request: Parameters for getting repository information
        
    Returns:
        GitHubRepository object with repository details
    """
    logger.info(f"Getting GitHub repository: {request.owner}/{request.repo}")
    
    # Get GitHub credentials from context
    github_token = ctx.context.github_token if hasattr(ctx.context, 'github_token') else None
    
    # Create GitHub client
    g = github.Github(github_token)
    
    # Get repository
    repo_name = f"{request.owner}/{request.repo}"
    repo = g.get_repo(repo_name)
    
    # Convert to our model
    result = GitHubRepository(
        name=repo.name,
        full_name=repo.full_name,
        description=repo.description,
        url=repo.html_url,
        default_branch=repo.default_branch,
        stars=repo.stargazers_count,
        forks=repo.forks_count,
        open_issues=repo.open_issues_count,
        language=repo.language
    )
    
    logger.info(f"Retrieved GitHub repository: {repo.full_name}")
    return result


@function_tool()
async def list_issues(
    ctx: RunContextWrapper[DevOpsContext],
    request: GitHubIssueRequest
) -> List[GitHubIssue]:
    """
    List GitHub issues for a repository.
    
    Args:
        ctx: Run context containing DevOpsContext
        request: Parameters for listing issues
        
    Returns:
        List of GitHubIssue objects
    """
    logger.info(f"Listing GitHub issues for {request.owner}/{request.repo} with state={request.state}")
    
    # Get GitHub credentials from context
    github_token = ctx.context.github_token if hasattr(ctx.context, 'github_token') else None
    
    # Create GitHub client
    g = github.Github(github_token)
    
    # Get repository
    repo_name = f"{request.owner}/{request.repo}"
    repo = g.get_repo(repo_name)
    
    # Get issues
    issues = repo.get_issues(state=request.state)
    
    # Convert to our model
    result = []
    for issue in issues:
        issue_model = GitHubIssue(
            number=issue.number,
            title=issue.title,
            body=issue.body,
            state=issue.state,
            created_at=issue.created_at.isoformat(),
            updated_at=issue.updated_at.isoformat(),
            url=issue.html_url,
            labels=[label.name for label in issue.labels],
            assignees=[assignee.login for assignee in issue.assignees]
        )
        result.append(issue_model)
    
    logger.info(f"Retrieved {len(result)} GitHub issues")
    return result


@function_tool()
async def create_issue(
    ctx: RunContextWrapper[DevOpsContext],
    request: GitHubCreateIssueRequest
) -> GitHubIssue:
    """
    Create a new GitHub issue.
    
    Args:
        ctx: Run context containing DevOpsContext
        request: Parameters for creating an issue
        
    Returns:
        GitHubIssue object for the created issue
    """
    logger.info(f"Creating GitHub issue in {request.owner}/{request.repo}: {request.title}")
    
    # Get GitHub credentials from context
    github_token = ctx.context.github_token if hasattr(ctx.context, 'github_token') else None
    
    # Create GitHub client
    g = github.Github(github_token)
    
    # Get repository
    repo_name = f"{request.owner}/{request.repo}"
    repo = g.get_repo(repo_name)
    
    # Create issue
    issue = repo.create_issue(
        title=request.title,
        body=request.body,
        labels=request.labels,
        assignees=request.assignees
    )
    
    # Convert to our model
    result = GitHubIssue(
        number=issue.number,
        title=issue.title,
        body=issue.body,
        state=issue.state,
        created_at=issue.created_at.isoformat(),
        updated_at=issue.updated_at.isoformat(),
        url=issue.html_url,
        labels=[label.name for label in issue.labels],
        assignees=[assignee.login for assignee in issue.assignees]
    )
    
    logger.info(f"Created GitHub issue: {issue.html_url}")
    return result


@function_tool()
async def list_pull_requests(
    ctx: RunContextWrapper[DevOpsContext],
    request: GitHubPRRequest
) -> List[GitHubPullRequest]:
    """
    List GitHub pull requests for a repository.
    
    Args:
        ctx: Run context containing DevOpsContext
        request: Parameters for listing pull requests
        
    Returns:
        List of GitHubPullRequest objects
    """
    logger.info(f"Listing GitHub PRs for {request.owner}/{request.repo} with state={request.state}")
    
    # Get GitHub credentials from context
    github_token = ctx.context.github_token if hasattr(ctx.context, 'github_token') else None
    
    # Create GitHub client
    g = github.Github(github_token)
    
    # Get repository
    repo_name = f"{request.owner}/{request.repo}"
    repo = g.get_repo(repo_name)
    
    # Get pull requests
    pulls = repo.get_pulls(state=request.state)
    
    # Convert to our model
    result = []
    for pr in pulls:
        pr_model = GitHubPullRequest(
            number=pr.number,
            title=pr.title,
            body=pr.body,
            state=pr.state,
            created_at=pr.created_at.isoformat(),
            updated_at=pr.updated_at.isoformat(),
            url=pr.html_url,
            labels=[label.name for label in pr.labels],
            assignees=[assignee.login for assignee in pr.assignees],
            base_branch=pr.base.ref,
            head_branch=pr.head.ref
        )
        result.append(pr_model)
    
    logger.info(f"Retrieved {len(result)} GitHub pull requests")
    return result