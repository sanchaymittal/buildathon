"""GitHub PR commentary adapter (stub for MVP)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import IntegrationAdapter, NullAdapter


class NullGitHubPRAdapter(NullAdapter):
    def __init__(self) -> None:
        super().__init__("github_pr")


class GitHubPRAdapter:
    service_name = "github_pr"

    def __init__(self, token: str) -> None:
        self._token = token

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError("Real GitHub PR adapter not implemented for MVP")


_default: Optional[IntegrationAdapter] = None


def get_adapter() -> IntegrationAdapter:
    global _default
    if _default is None:
        _default = NullGitHubPRAdapter()
    return _default


def set_adapter(adapter: IntegrationAdapter) -> None:
    global _default
    _default = adapter


def github_comment(pr_ref: str, body: str) -> Dict[str, Any]:
    return get_adapter().send({"action": "comment", "pr_ref": pr_ref, "body": body})
