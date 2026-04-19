"""
GitHub Models Module - Provides data models for GitHub operations.

This module defines Pydantic models for GitHub repository requests, issue requests,
pull request requests, and entity representations for use with the OpenAI Agents SDK.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class GitHubRepoRequest(BaseModel):
    """
    Request model for GitHub repository operations.
    """
    
    owner: str = Field(
        description="Owner (organization or user) of the repository"
    )
    
    repo: str = Field(
        description="Name of the repository"
    )


class GitHubIssueRequest(BaseModel):
    """
    Request model for listing GitHub issues.
    """
    
    owner: str = Field(
        description="Owner (organization or user) of the repository"
    )
    
    repo: str = Field(
        description="Name of the repository"
    )
    
    state: str = Field(
        default="open",
        description="State of issues to retrieve (open, closed, or all)"
    )
    
    labels: Optional[List[str]] = Field(
        default=None,
        description="List of label names to filter by"
    )
    
    assignee: Optional[str] = Field(
        default=None,
        description="GitHub username to filter issues by assignee"
    )
    
    creator: Optional[str] = Field(
        default=None,
        description="GitHub username to filter issues by creator"
    )
    
    mentioned: Optional[str] = Field(
        default=None,
        description="GitHub username to filter issues by mention"
    )
    
    sort: Optional[str] = Field(
        default="created",
        description="What to sort results by (created, updated, comments)"
    )
    
    direction: Optional[str] = Field(
        default="desc",
        description="Direction to sort (asc or desc)"
    )
    
    since: Optional[str] = Field(
        default=None,
        description="Only issues updated at or after this time (ISO 8601 format)"
    )


class GitHubCreateIssueRequest(BaseModel):
    """
    Request model for creating a GitHub issue.
    """
    
    owner: str = Field(
        description="Owner (organization or user) of the repository"
    )
    
    repo: str = Field(
        description="Name of the repository"
    )
    
    title: str = Field(
        description="Title of the issue"
    )
    
    body: str = Field(
        description="Body content of the issue"
    )
    
    labels: Optional[List[str]] = Field(
        default=None,
        description="List of labels to apply to the issue"
    )
    
    assignees: Optional[List[str]] = Field(
        default=None,
        description="List of GitHub usernames to assign to the issue"
    )
    
    milestone: Optional[int] = Field(
        default=None,
        description="Milestone ID to associate with the issue"
    )


class GitHubPRRequest(BaseModel):
    """
    Request model for listing GitHub pull requests.
    """
    
    owner: str = Field(
        description="Owner (organization or user) of the repository"
    )
    
    repo: str = Field(
        description="Name of the repository"
    )
    
    state: str = Field(
        default="open",
        description="State of pull requests to retrieve (open, closed, or all)"
    )
    
    head: Optional[str] = Field(
        default=None,
        description="Filter by head user or head organization and branch name"
    )
    
    base: Optional[str] = Field(
        default=None,
        description="Filter by base branch name"
    )
    
    sort: Optional[str] = Field(
        default="created",
        description="What to sort results by (created, updated, popularity, long-running)"
    )
    
    direction: Optional[str] = Field(
        default="desc",
        description="Direction to sort (asc or desc)"
    )


class GitHubRepository(BaseModel):
    """
    Model representing a GitHub repository.
    """
    
    name: str = Field(
        description="Name of the repository"
    )
    
    full_name: str = Field(
        description="Full name of the repository (owner/repo)"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Description of the repository"
    )
    
    url: str = Field(
        description="URL of the repository"
    )
    
    default_branch: str = Field(
        description="Default branch of the repository"
    )
    
    stars: int = Field(
        description="Number of stars the repository has"
    )
    
    forks: int = Field(
        description="Number of forks the repository has"
    )
    
    open_issues: int = Field(
        description="Number of open issues in the repository"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Primary language of the repository"
    )
    
    private: bool = Field(
        default=False,
        description="Whether the repository is private"
    )
    
    created_at: Optional[str] = Field(
        default=None,
        description="When the repository was created (ISO 8601 format)"
    )
    
    updated_at: Optional[str] = Field(
        default=None,
        description="When the repository was last updated (ISO 8601 format)"
    )
    
    topics: Optional[List[str]] = Field(
        default=None,
        description="Topics associated with the repository"
    )


class GitHubIssue(BaseModel):
    """
    Model representing a GitHub issue.
    """
    
    number: int = Field(
        description="Issue number"
    )
    
    title: str = Field(
        description="Title of the issue"
    )
    
    body: Optional[str] = Field(
        default=None,
        description="Body content of the issue"
    )
    
    state: str = Field(
        description="State of the issue (open or closed)"
    )
    
    created_at: str = Field(
        description="When the issue was created (ISO 8601 format)"
    )
    
    updated_at: str = Field(
        description="When the issue was last updated (ISO 8601 format)"
    )
    
    closed_at: Optional[str] = Field(
        default=None,
        description="When the issue was closed (ISO 8601 format)"
    )
    
    url: str = Field(
        description="URL of the issue"
    )
    
    labels: List[str] = Field(
        default_factory=list,
        description="Labels applied to the issue"
    )
    
    assignees: List[str] = Field(
        default_factory=list,
        description="GitHub usernames assigned to the issue"
    )
    
    milestone: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Milestone associated with the issue"
    )
    
    comments: Optional[int] = Field(
        default=None,
        description="Number of comments on the issue"
    )


class GitHubPullRequest(BaseModel):
    """
    Model representing a GitHub pull request.
    """
    
    number: int = Field(
        description="Pull request number"
    )
    
    title: str = Field(
        description="Title of the pull request"
    )
    
    body: Optional[str] = Field(
        default=None,
        description="Body content of the pull request"
    )
    
    state: str = Field(
        description="State of the pull request (open, closed, or merged)"
    )
    
    created_at: str = Field(
        description="When the pull request was created (ISO 8601 format)"
    )
    
    updated_at: str = Field(
        description="When the pull request was last updated (ISO 8601 format)"
    )
    
    closed_at: Optional[str] = Field(
        default=None,
        description="When the pull request was closed (ISO 8601 format)"
    )
    
    merged_at: Optional[str] = Field(
        default=None,
        description="When the pull request was merged (ISO 8601 format)"
    )
    
    url: str = Field(
        description="URL of the pull request"
    )
    
    head_branch: str = Field(
        description="Name of the head branch"
    )
    
    base_branch: str = Field(
        description="Name of the base branch"
    )
    
    labels: List[str] = Field(
        default_factory=list,
        description="Labels applied to the pull request"
    )
    
    assignees: List[str] = Field(
        default_factory=list,
        description="GitHub usernames assigned to the pull request"
    )
    
    requested_reviewers: List[str] = Field(
        default_factory=list,
        description="GitHub usernames requested to review the pull request"
    )
    
    merged: bool = Field(
        default=False,
        description="Whether the pull request has been merged"
    )
    
    mergeable: Optional[bool] = Field(
        default=None,
        description="Whether the pull request is mergeable"
    )
    
    comments: Optional[int] = Field(
        default=None,
        description="Number of comments on the pull request"
    )
    
    commits: Optional[int] = Field(
        default=None,
        description="Number of commits in the pull request"
    )
    
    additions: Optional[int] = Field(
        default=None,
        description="Number of additions in the pull request"
    )
    
    deletions: Optional[int] = Field(
        default=None,
        description="Number of deletions in the pull request"
    )
    
    changed_files: Optional[int] = Field(
        default=None,
        description="Number of changed files in the pull request"
    )