"""PagerDuty adapter (stub)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import IntegrationAdapter, NullAdapter


class NullPagerDutyAdapter(NullAdapter):
    def __init__(self) -> None:
        super().__init__("pagerduty")


class PagerDutyAdapter:
    service_name = "pagerduty"

    def __init__(self, routing_key: str) -> None:
        self._routing_key = routing_key

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError("Real PagerDuty integration not implemented for MVP")


_default: Optional[IntegrationAdapter] = None


def get_adapter() -> IntegrationAdapter:
    global _default
    if _default is None:
        _default = NullPagerDutyAdapter()
    return _default


def set_adapter(adapter: IntegrationAdapter) -> None:
    global _default
    _default = adapter


def pagerduty_trigger(
    summary: str, severity: str = "warning", source: str = "agentic-devops"
) -> Dict[str, Any]:
    return get_adapter().send(
        {
            "action": "trigger",
            "summary": summary,
            "severity": severity,
            "source": source,
        }
    )
