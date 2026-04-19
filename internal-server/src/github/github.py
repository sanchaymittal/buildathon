"""
GitHub Service Module - Provides functionality for interacting with GitHub APIs.

This module enables management of GitHub repositories, branches, content, and other
GitHub resources, with integration points for Docker deployments.
"""

import os
import logging
import json
import base64
import re
import time
import requests
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin, quote

from ..core.config import get_config
from ..core.credentials import GitHubCredentials, get_credential_manager

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_API_URL = "https://api.github.com"
DEFAULT_PAGE_SIZE = 100
DEFAULT_CACHE_TTL = 60  # 1 minute


class GitHubError(Exception):
    """Base exception for GitHub service errors."""
    pass


class ResourceNotFoundError(GitHubError):
    """Exception raised when a requested GitHub resource is not found."""
    pass


class AuthenticationError(GitHubError):
    """Exception raised when authentication fails."""
    pass


class ValidationError(GitHubError):
    """Exception raised when input validation fails."""
    pass


class RateLimitError(GitHubError):
    """Exception raised when GitHub API rate limits are exceeded."""
    pass


class GitHubService:
    """
    Service class for interacting with GitHub APIs.
    
    Provides methods for managing repositories, content, branches, pull requests,
    and other GitHub resources, with caching and error handling.
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        api_url: str = DEFAULT_API_URL,
        organization: Optional[str] = None,
        use_agent_endpoint: bool = False,
        agent_url: Optional[str] = None
    ):
        """
        Initialize the GitHub service.
        
        Args:
            token: GitHub API token. If None, will be loaded from credentials manager.
            api_url: GitHub API URL, defaults to public GitHub API.
            organization: Default GitHub organization to use.
            use_agent_endpoint: Whether to use the agent endpoint instead of direct GitHub API.
            agent_url: URL of the agent endpoint, if use_agent_endpoint is True.
            
        Raises:
            AuthenticationError: If token is not provided and cannot be loaded.
        """
        self.api_url = api_url
        self.organization = organization
        self.use_agent_endpoint = use_agent_endpoint
        self.agent_url = agent_url
        
        # Set up credentials
        if token:
            self.token = token
        else:
            cred_manager = get_credential_manager()
            try:
                github_credentials = cred_manager.get_github_credentials()
                self.token = github_credentials.token
            except Exception as e:
                raise AuthenticationError(f"Failed to get GitHub token: {e}")
        
        if not self.token:
            raise AuthenticationError("GitHub token is required")
        
        # Load configuration
        self.config = get_config()
        
        # If no organization is provided, try to get from config or env
        if not self.organization:
            self.organization = (
                self.config.get("github.organization") or
                os.environ.get("GITHUB_ORG") or
                None
            )
        
        # Initialize cache
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        # Verify access
        self._verify_access()
    
    def _verify_access(self) -> None:
        """
        Verify that the token has access to GitHub API.
        
        Raises:
            AuthenticationError: If authentication fails.
        """
        try:
            # Make a simple API call to verify access
            self._make_request("GET", "user")
        except Exception as e:
            raise AuthenticationError(f"GitHub authentication failed: {e}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = False,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        raw_response: bool = False
    ) -> Any:
        """
        Make an HTTP request to the GitHub API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (e.g., "repos/{owner}/{repo}")
            params: Query parameters
            data: Request body data
            headers: Additional headers
            use_cache: Whether to use cached response (for GET requests only)
            cache_ttl: Cache TTL in seconds
            raw_response: Whether to return the raw response object
            
        Returns:
            Parsed JSON response or raw response if raw_response is True
            
        Raises:
            GitHubError: If the request fails
            RateLimitError: If rate limits are exceeded
            ResourceNotFoundError: If the resource is not found
            AuthenticationError: If authentication fails
        """
        # Determine the URL
        if self.use_agent_endpoint and self.agent_url:
            # If using agent endpoint, construct URL for that
            base_url = self.agent_url.rstrip("/") + "/"
            full_url = urljoin(base_url, endpoint)
        else:
            # Direct GitHub API call
            base_url = self.api_url.rstrip("/") + "/"
            full_url = urljoin(base_url, endpoint)
        
        # Check cache for GET requests
        cache_key = None
        if method == "GET" and use_cache:
            cache_key = f"{method}:{full_url}:{json.dumps(params or {})}"
            cached = self.cache.get(cache_key)
            if cached and time.time() - cached["timestamp"] < cache_ttl:
                return cached["data"]
        
        # Prepare headers
        request_headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevOpsAgent/0.1.0"
        }
        
        # Add authorization header unless using agent endpoint
        if not self.use_agent_endpoint:
            request_headers["Authorization"] = f"token {self.token}"
        
        # Add custom headers
        if headers:
            request_headers.update(headers)
        
        # Make the request
        try:
            response = requests.request(
                method=method,
                url=full_url,
                params=params,
                json=data,
                headers=request_headers
            )
            
            # Check for rate limit
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining and int(remaining) == 0:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait_time = max(0, reset_time - int(time.time()))
                raise RateLimitError(
                    f"GitHub API rate limit exceeded. Resets in {wait_time} seconds."
                )
            
            # Handle common error responses
            if response.status_code == 404:
                raise ResourceNotFoundError(f"GitHub resource not found: {endpoint}")
            
            if response.status_code == 401:
                raise AuthenticationError("GitHub authentication failed")
            
            if response.status_code == 403:
                if "rate limit" in response.text.lower():
                    raise RateLimitError("GitHub API rate limit exceeded")
                else:
                    raise GitHubError(f"GitHub API access forbidden: {response.text}")
            
            if response.status_code >= 400:
                raise GitHubError(
                    f"GitHub API error ({response.status_code}): {response.text}"
                )
            
            # Return raw response if requested
            if raw_response:
                return response
            
            # Parse JSON response
            result = response.json() if response.content else {}
            
            # Cache successful GET responses
            if method == "GET" and use_cache and cache_key:
                self.cache[cache_key] = {
                    "timestamp": time.time(),
                    "data": result
                }
            
            return result
            
        except (ResourceNotFoundError, AuthenticationError, RateLimitError) as e:
            # Re-raise known exceptions
            raise
        except requests.RequestException as e:
            raise GitHubError(f"GitHub API request failed: {e}")
        except json.JSONDecodeError as e:
            raise GitHubError(f"Failed to parse GitHub API response: {e}")
    
    def clear_cache(self) -> None:
        """Clear the request cache."""
        self.cache.clear()
    
    def _get_repo_path(self, repo: str, owner: Optional[str] = None) -> str:
        """
        Get the repository path for API requests.
        
        Args:
            repo: Repository name or full path (owner/repo)
            owner: Repository owner (organization or user)
            
        Returns:
            Repository path in the format "repos/{owner}/{repo}"
        """
        if "/" in repo:
            # Full repository path provided
            parts = repo.split("/", 1)
            return f"repos/{parts[0]}/{parts[1]}"
        
        # Use provided owner or default organization
        repo_owner = owner or self.organization
        if not repo_owner:
            raise ValidationError(
                "Repository owner is required (either specify owner parameter, "
                "set a default organization, or use full repo path 'owner/repo')"
            )
        
        return f"repos/{repo_owner}/{repo}"
    
    #
    # Repository Management
    #
    
    def list_repositories(
        self,
        org: Optional[str] = None,
        user: Optional[str] = None,
        type: str = "all",
        sort: str = "updated",
        direction: str = "desc",
        per_page: int = DEFAULT_PAGE_SIZE,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List repositories for the specified organization or user.
        
        Args:
            org: Organization name. If None, uses default organization.
            user: User name. If specified, lists user's repositories instead of org's.
            type: Repository type (all, public, private, forks, sources, member).
            sort: Sort field (created, updated, pushed, full_name).
            direction: Sort direction (asc, desc).
            per_page: Number of results per page.
            use_cache: Whether to use cached response.
            
        Returns:
            List of repository details.
            
        Raises:
            ValidationError: If neither org nor user is specified and no default org.
        """
        params = {
            "sort": sort,
            "direction": direction,
            "per_page": per_page
        }
        
        if user:
            # List user repositories
            endpoint = f"users/{user}/repos"
            params["type"] = type
        else:
            # List organization repositories
            organization = org or self.organization
            if not organization:
                raise ValidationError(
                    "Organization is required (either specify org parameter, "
                    "set a default organization, or specify user parameter)"
                )
            
            endpoint = f"orgs/{organization}/repos"
            params["type"] = type
            
        # Get all pages of results
        all_repos = []
        page = 1
        
        while True:
            params["page"] = page
            response = self._make_request(
                "GET", endpoint, params=params, use_cache=use_cache
            )
            
            if not response:
                break
                
            all_repos.extend(response)
            
            if len(response) < per_page:
                break
                
            page += 1
        
        return all_repos
    
    def get_repository(
        self,
        repo: str,
        owner: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get details for a specific repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            owner: Repository owner. If None, uses owner from repo or default organization.
            use_cache: Whether to use cached response.
            
        Returns:
            Repository details.
            
        Raises:
            ResourceNotFoundError: If the repository does not exist.
        """
        repo_path = self._get_repo_path(repo, owner)
        return self._make_request("GET", repo_path, use_cache=use_cache)
    
    def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        owner: Optional[str] = None,
        auto_init: bool = False,
        gitignore_template: Optional[str] = None,
        license_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new GitHub repository.
        
        Args:
            name: Repository name.
            description: Repository description.
            private: Whether the repository should be private.
            owner: Owner (organization or user) to create the repository under.
                  If None, uses default organization.
            auto_init: Whether to auto-initialize the repository with a README.
            gitignore_template: Gitignore template to use.
            license_template: License template to use.
            
        Returns:
            Details of the created repository.
            
        Raises:
            ValidationError: If repository name is invalid.
            GitHubError: If repository creation fails.
        """
        # Validate repository name
        if not re.match(r'^[a-zA-Z0-9_.-]+$', name):
            raise ValidationError(
                "Invalid repository name. Use only letters, numbers, hyphens, dots, and underscores."
            )
        
        # Determine if creating in an organization or for the authenticated user
        org_name = owner or self.organization
        
        data = {
            "name": name,
            "private": private,
            "auto_init": auto_init
        }
        
        # Add optional parameters
        if description:
            data["description"] = description
        
        if gitignore_template:
            data["gitignore_template"] = gitignore_template
            
        if license_template:
            data["license_template"] = license_template
        
        if org_name:
            # Create in organization
            endpoint = f"orgs/{org_name}/repos"
        else:
            # Create for authenticated user
            endpoint = "user/repos"
        
        return self._make_request("POST", endpoint, data=data)

    def delete_repository(
        self,
        repo: str,
        owner: Optional[str] = None
    ) -> bool:
        """
        Delete a GitHub repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            owner: Repository owner. If None, uses owner from repo or default organization.
            
        Returns:
            True if successful.
            
        Raises:
            ResourceNotFoundError: If the repository does not exist.
            GitHubError: If repository deletion fails.
        """
        repo_path = self._get_repo_path(repo, owner)
        self._make_request("DELETE", repo_path)
        return True

    #
    # Content Operations
    #
    
    def get_readme(
        self,
        repo: str,
        owner: Optional[str] = None,
        ref: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get the README content for a repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            owner: Repository owner. If None, uses owner from repo or default organization.
            ref: Git reference (branch, tag, commit). If None, uses the default branch.
            use_cache: Whether to use cached response.
            
        Returns:
            README content and metadata.
            
        Raises:
            ResourceNotFoundError: If the README does not exist.
        """
        repo_path = self._get_repo_path(repo, owner)
        params = {}
        if ref:
            params["ref"] = ref
            
        response = self._make_request(
            "GET", f"{repo_path}/readme", params=params, use_cache=use_cache
        )
        
        # Decode content if it's base64 encoded
        if response.get("encoding") == "base64" and response.get("content"):
            response["decoded_content"] = base64.b64decode(
                response["content"].replace("\n", "")
            ).decode("utf-8")
            
        return response
    
    def get_content(
        self,
        repo: str,
        path: str,
        owner: Optional[str] = None,
        ref: Optional[str] = None,
        use_cache: bool = True
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Get contents of a file or directory in a repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            path: Path to the file or directory.
            owner: Repository owner. If None, uses owner from repo or default organization.
            ref: Git reference (branch, tag, commit). If None, uses the default branch.
            use_cache: Whether to use cached response.
            
        Returns:
            Content and metadata (for a file) or list of contents (for a directory).
            
        Raises:
            ResourceNotFoundError: If the path does not exist.
        """
        repo_path = self._get_repo_path(repo, owner)
        params = {}
        if ref:
            params["ref"] = ref
            
        response = self._make_request(
            "GET", f"{repo_path}/contents/{path}", params=params, use_cache=use_cache
        )
        
        # Handle file vs directory response
        if isinstance(response, dict) and response.get("encoding") == "base64":
            # Single file response
            response["decoded_content"] = base64.b64decode(
                response["content"].replace("\n", "")
            ).decode("utf-8")
            
        return response
    
    def create_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        owner: Optional[str] = None,
        committer: Optional[Dict[str, str]] = None,
        author: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new file in a repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            path: Path to the file.
            content: Content of the file.
            message: Commit message.
            branch: Branch to commit to. If None, uses the default branch.
            owner: Repository owner. If None, uses owner from repo or default organization.
            committer: Committer information (name and email).
            author: Author information (name and email).
            
        Returns:
            Result of the commit.
            
        Raises:
            GitHubError: If file creation fails.
        """
        repo_path = self._get_repo_path(repo, owner)
        
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode()
        }
        
        if branch:
            data["branch"] = branch
            
        if committer:
            data["committer"] = committer
            
        if author:
            data["author"] = author
            
        return self._make_request("PUT", f"{repo_path}/contents/{path}", data=data)
    
    def update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        sha: str,
        branch: Optional[str] = None,
        owner: Optional[str] = None,
        committer: Optional[Dict[str, str]] = None,
        author: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing file in a repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            path: Path to the file.
            content: New content of the file.
            message: Commit message.
            sha: SHA of the file to update.
            branch: Branch to commit to. If None, uses the default branch.
            owner: Repository owner. If None, uses owner from repo or default organization.
            committer: Committer information (name and email).
            author: Author information (name and email).
            
        Returns:
            Result of the commit.
            
        Raises:
            ResourceNotFoundError: If the file does not exist.
            GitHubError: If file update fails.
        """
        repo_path = self._get_repo_path(repo, owner)
        
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "sha": sha
        }
        
        if branch:
            data["branch"] = branch
            
        if committer:
            data["committer"] = committer
            
        if author:
            data["author"] = author
            
        return self._make_request("PUT", f"{repo_path}/contents/{path}", data=data)
    
    def delete_file(
        self,
        repo: str,
        path: str,
        message: str,
        sha: str,
        branch: Optional[str] = None,
        owner: Optional[str] = None,
        committer: Optional[Dict[str, str]] = None,
        author: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Delete a file from a repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            path: Path to the file.
            message: Commit message.
            sha: SHA of the file to delete.
            branch: Branch to commit to. If None, uses the default branch.
            owner: Repository owner. If None, uses owner from repo or default organization.
            committer: Committer information (name and email).
            author: Author information (name and email).
            
        Returns:
            Result of the commit.
            
        Raises:
            ResourceNotFoundError: If the file does not exist.
            GitHubError: If file deletion fails.
        """
        repo_path = self._get_repo_path(repo, owner)
        
        data = {
            "message": message,
            "sha": sha
        }
        
        if branch:
            data["branch"] = branch
            
        if committer:
            data["committer"] = committer
            
        if author:
            data["author"] = author
            
        return self._make_request("DELETE", f"{repo_path}/contents/{path}", data=data)

    #
    # Issues & Pull Requests
    #

    def list_issues(
        self,
        repo: str,
        owner: Optional[str] = None,
        state: str = "open",
        labels: Optional[List[str]] = None,
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> List[Dict[str, Any]]:
        """List issues for a repository."""
        repo_path = self._get_repo_path(repo, owner)
        params: Dict[str, Any] = {
            "state": state,
            "per_page": per_page,
        }
        if labels:
            params["labels"] = ",".join(labels)

        issues: List[Dict[str, Any]] = []
        page = 1
        while True:
            params["page"] = page
            page_items = self._make_request(
                "GET", f"{repo_path}/issues", params=params, use_cache=False
            )
            if not page_items:
                break
            issues.extend(page_items)
            if len(page_items) < per_page:
                break
            page += 1

        return issues

    def create_issue(
        self,
        repo: str,
        title: str,
        body: Optional[str] = None,
        owner: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new issue in a repository."""
        repo_path = self._get_repo_path(repo, owner)
        data: Dict[str, Any] = {"title": title}
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees

        return self._make_request("POST", f"{repo_path}/issues", data=data)

    def list_pull_requests(
        self,
        repo: str,
        owner: Optional[str] = None,
        state: str = "open",
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> List[Dict[str, Any]]:
        """List pull requests for a repository."""
        repo_path = self._get_repo_path(repo, owner)
        params: Dict[str, Any] = {
            "state": state,
            "per_page": per_page,
        }

        pulls: List[Dict[str, Any]] = []
        page = 1
        while True:
            params["page"] = page
            page_items = self._make_request(
                "GET", f"{repo_path}/pulls", params=params, use_cache=False
            )
            if not page_items:
                break
            pulls.extend(page_items)
            if len(page_items) < per_page:
                break
            page += 1

        return pulls

    #
    # Branch Management
    #

    def list_branches(
        self,
        repo: str,
        owner: Optional[str] = None,
        protected: Optional[bool] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List branches in a repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            owner: Repository owner. If None, uses owner from repo or default organization.
            protected: Filter branches by protection status.
            use_cache: Whether to use cached response.
            
        Returns:
            List of branch details.
            
        Raises:
            ResourceNotFoundError: If the repository does not exist.
        """
        repo_path = self._get_repo_path(repo, owner)
        params = {}
        
        if protected is not None:
            params["protected"] = "true" if protected else "false"
            
        response = self._make_request(
            "GET", f"{repo_path}/branches", params=params, use_cache=use_cache
        )
        
        return response
    
    def get_branch(
        self,
        repo: str,
        branch: str,
        owner: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get details for a specific branch.
        
        Args:
            repo: Repository name or full path (owner/repo).
            branch: Branch name.
            owner: Repository owner. If None, uses owner from repo or default organization.
            use_cache: Whether to use cached response.
            
        Returns:
            Branch details.
            
        Raises:
            ResourceNotFoundError: If the branch does not exist.
        """
        repo_path = self._get_repo_path(repo, owner)
        return self._make_request(
            "GET", f"{repo_path}/branches/{branch}", use_cache=use_cache
        )
    
    def create_branch(
        self,
        repo: str,
        name: str,
        sha: str,
        owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new branch in a repository.
        
        Args:
            repo: Repository name or full path (owner/repo).
            name: New branch name.
            sha: SHA of the commit to branch from.
            owner: Repository owner. If None, uses owner from repo or default organization.
            
        Returns:
            Created reference details.
            
        Raises:
            GitHubError: If branch creation fails.
        """
        repo_path = self._get_repo_path(repo, owner)
        data = {
            "ref": f"refs/heads/{name}",
            "sha": sha
        }
        
        return self._make_request("POST", f"{repo_path}/git/refs", data=data)
    
    #
    # Docker Integration
    #
    
    def deploy_to_docker(
        self,
        repo: str,
        branch: Optional[str] = None,
        owner: Optional[str] = None,
        docker_service: Optional["DockerService"] = None,
    ) -> Dict[str, Any]:
        """
        Deploy a GitHub repository to Docker.
        
        Args:
            repo: Repository name or full path (owner/repo).
            branch: Branch to deploy. If None, uses the default branch.
            owner: Repository owner. If None, uses owner from repo or default organization.
            docker_service: DockerService instance (created if not provided).
            
        Returns:
            Deployment status and details.
            
        Raises:
            ValidationError: If deployment fails.
            GitHubError: If repository access fails.
        """
        from ..docker_svc.deploy import DockerDeployService
        from ..docker_svc.models import DeployRequest
        
        repo_details = self.get_repository(repo, owner)
        
        if not branch:
            branch = repo_details.get("default_branch", "main")
        
        try:
            self.get_branch(repo, branch, owner)
        except ResourceNotFoundError:
            raise ValidationError(f"Branch '{branch}' not found in repository")
        
        if not docker_service:
            docker_service = DockerDeployService()
        
        request = DeployRequest(
            repository=f"{repo_details['owner']['login']}/{repo_details['name']}",
            branch=branch,
        )
        
        result = docker_service.deploy_from_github(request, self.token)
        
        return {
            'service': 'docker',
            'repository': repo_details['full_name'],
            'branch': branch,
            'url': result.url,
            'container_id': result.container_id,
        }
