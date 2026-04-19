"""Linear adapter (stub)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import IntegrationAdapter, NullAdapter

logger = logging.getLogger(__name__)


class NullLinearAdapter(NullAdapter):
    def __init__(self) -> None:
        super().__init__("linear")


class LinearAdapter:
    """Real Linear adapter placeholder (not implemented for MVP)."""

    service_name = "linear"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError("Real Linear integration not implemented for MVP")


_default: Optional[IntegrationAdapter] = None


def get_adapter() -> IntegrationAdapter:
    global _default
    if _default is None:
        _default = NullLinearAdapter()
    return _default


def set_adapter(adapter: IntegrationAdapter) -> None:
    global _default
    _default = adapter


def linear_create_issue(
    title: str, body: str = "", team: Optional[str] = None
) -> Dict[str, Any]:
    """Create (or stub-create) a Linear issue."""
    return get_adapter().send(
        {"action": "create_issue", "title": title, "body": body, "team": team}
    )
