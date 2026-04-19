"""
GitHub Routes - FastAPI endpoints for GitHub operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ...github import GitHubService
from ...github.github import GitHubError
from ...core.credentials import get_credential_manager

router = APIRouter(prefix="/github", tags=["github"])


def _get_github_service() -> GitHubService:
    """Get GitHub service with credentials."""
    try:
        cred_manager = get_credential_manager()
        creds = cred_manager.get_github_credentials()
        return GitHubService(token=creds.token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"GitHub credentials not available: {e}"
        )


@router.get("/repos/{owner}/{repo}")
def get_repository(
    owner: str,
    repo: str,
    github: GitHubService = Depends(_get_github_service),
) -> dict:
    """Get repository details."""
    try:
        return github.get_repository(repo, owner=owner)
    except GitHubError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/repos/{owner}/{repo}/issues")
def list_issues(
    owner: str,
    repo: str,
    state: str = Query("open", description="Issue state"),
    github: GitHubService = Depends(_get_github_service),
) -> List[dict]:
    """List repository issues."""
    try:
        issues = github.list_issues(repo, owner=owner, state=state)
        return issues
    except GitHubError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/repos/{owner}/{repo}/branches")
def list_branches(
    owner: str,
    repo: str,
    github: GitHubService = Depends(_get_github_service),
) -> List[dict]:
    """List repository branches."""
    try:
        return github.list_branches(repo, owner=owner)
    except GitHubError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/repos/{owner}/{repo}/pulls")
def list_pull_requests(
    owner: str,
    repo: str,
    state: str = Query("open", description="PR state"),
    github: GitHubService = Depends(_get_github_service),
) -> List[dict]:
    """List pull requests."""
    try:
        return github.list_pull_requests(repo, owner=owner, state=state)
    except GitHubError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))