"""Slack adapter (stub)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import IntegrationAdapter, NullAdapter

logger = logging.getLogger(__name__)


class NullSlackAdapter(NullAdapter):
    def __init__(self) -> None:
        super().__init__("slack")


class SlackAdapter:
    service_name = "slack"

    def __init__(self, webhook_url: str) -> None:
        self._webhook = webhook_url

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError("Real Slack integration not implemented for MVP")


_default: Optional[IntegrationAdapter] = None


def get_adapter() -> IntegrationAdapter:
    global _default
    if _default is None:
        _default = NullSlackAdapter()
    return _default


def set_adapter(adapter: IntegrationAdapter) -> None:
    global _default
    _default = adapter


def slack_post(channel: str, message: str) -> Dict[str, Any]:
    """Post (or stub-post) a Slack message."""
    return get_adapter().send(
        {"action": "post_message", "channel": channel, "message": message}
    )
