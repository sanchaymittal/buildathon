"""
TeamRun / TeamRunStore - in-memory registry for five-agent team runs.

Persistence out of scope for MVP; the on-disk audit log
(``~/.devops/agent.log``) is the durable trace.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..audit import AuditLogger, get_default_audit_logger
from .context import TeamContext, TeamRunStatus

logger = logging.getLogger(__name__)


@dataclass
class TeamEvent:
    event: str
    run_id: str
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            **self.payload,
        }


@dataclass
class TeamRun:
    run_id: str
    context: TeamContext
    events: List[TeamEvent] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    task_handle: Optional[asyncio.Task] = None

    def append_event(self, event: TeamEvent) -> None:
        self.events.append(event)

    def summary(self) -> Dict[str, Any]:
        return {
            **self.context.summary(),
            "event_count": len(self.events),
        }


class TeamRunStore:
    """In-memory registry of :class:`TeamRun` objects."""

    def __init__(self, audit_logger: Optional[AuditLogger] = None) -> None:
        self._audit = audit_logger or get_default_audit_logger()
        self._runs: Dict[str, TeamRun] = {}
        self._lock = threading.Lock()

    # --------------------------------------------------------------- mutation
    def create(
        self,
        *,
        task: str,
        project_path: str,
        user_id: str = "anonymous",
    ) -> TeamRun:
        run_id = str(uuid.uuid4())
        context = TeamContext(
            run_id=run_id, user_id=user_id, task=task, project_path=project_path
        )
        run = TeamRun(run_id=run_id, context=context)
        with self._lock:
            self._runs[run_id] = run
        self.record_event(
            run,
            "team_run_created",
            {
                "user_id": user_id,
                "project_path": project_path,
                "task_chars": len(task),
            },
        )
        return run

    def record_event(
        self,
        run: TeamRun,
        event: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TeamEvent:
        evt = TeamEvent(event=event, run_id=run.run_id, payload=dict(payload or {}))
        run.append_event(evt)
        try:
            self._audit.log({"team_run_id": run.run_id, **evt.as_dict()})
        except Exception as exc:  # pragma: no cover
            logger.debug("audit logger failed: %s", exc)
        return evt

    # --------------------------------------------------------------- approval
    def record_approval(
        self, run_id: str, gate: str, approved: bool, reason: Optional[str] = None
    ) -> TeamRun:
        run = self.require(run_id)
        run.context.approvals[gate] = approved
        if approved and run.context.status == TeamRunStatus.waiting_for_approval:
            run.context.set_status(
                TeamRunStatus.deploying, note=f"gate '{gate}' approved"
            )
        elif not approved:
            run.context.set_status(
                TeamRunStatus.failed, note=f"gate '{gate}' rejected: {reason or ''}"
            )
            run.context.blocking_reason = reason or f"gate '{gate}' rejected"
        self.record_event(
            run,
            "team_approval",
            {"gate": gate, "approved": approved, "reason": reason},
        )
        return run

    # ---------------------------------------------------------------- lookups
    def get(self, run_id: str) -> Optional[TeamRun]:
        with self._lock:
            return self._runs.get(run_id)

    def require(self, run_id: str) -> TeamRun:
        run = self.get(run_id)
        if run is None:
            raise KeyError(f"Team run not found: {run_id}")
        return run

    def list(self) -> List[TeamRun]:
        with self._lock:
            return list(self._runs.values())

    def drop(self, run_id: str) -> bool:
        with self._lock:
            return self._runs.pop(run_id, None) is not None


_default_store: Optional[TeamRunStore] = None
_default_lock = threading.Lock()


def get_team_run_store() -> TeamRunStore:
    """Return the process-wide default :class:`TeamRunStore`."""
    global _default_store
    if _default_store is None:
        with _default_lock:
            if _default_store is None:
                _default_store = TeamRunStore()
    return _default_store


def set_team_run_store(store: TeamRunStore) -> None:
    """Override the default store (useful for tests)."""
    global _default_store
    with _default_lock:
        _default_store = store
