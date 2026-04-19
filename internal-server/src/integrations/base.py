"""Common contracts for external integrations."""

from __future__ import annotations

import logging
from typing import Any, Dict, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class IntegrationAdapter(Protocol):
    """Protocol every external integration adapter conforms to."""

    service_name: str

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        ...


class NullAdapter:
    """Default adapter that logs the payload and returns a fake ack."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("NullAdapter(%s): %s", self.service_name, payload)
        return {
            "service": self.service_name,
            "delivered": False,
            "mode": "stub",
            "payload": payload,
        }
