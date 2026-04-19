"""
In-memory agent session store.

Each session wraps an :class:`Agent`, its conversation history, and the
:class:`DevOpsContext`. Sessions are indexed by a UUID and guarded by an
async lock so concurrent runs on the same session serialize cleanly.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.context import DevOpsContext
from ..gemini_agents import Agent
from ..gemini_agents.runner import GeminiRunner, RunResult
from .audit import AuditLogger, get_default_audit_logger
from .factory import build_devops_agent

logger = logging.getLogger(__name__)


@dataclass
class AgentSession:
    session_id: str
    agent: Agent
    context: DevOpsContext
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    run_count: int = 0

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent": self.agent.name,
            "model": self.agent.model,
            "user_id": self.context.user_id,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "turns": self.run_count,
            "history_messages": len(self.history),
        }


class AgentSessionStore:
    """Thread-safe in-memory registry of :class:`AgentSession` objects."""

    def __init__(
        self,
        runner: Optional[GeminiRunner] = None,
        audit_logger: Optional[AuditLogger] = None,
        max_tool_calls: int = 16,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        self._audit = audit_logger or get_default_audit_logger()
        self._runner = runner or GeminiRunner(
            max_tool_calls=max_tool_calls, audit_logger=self._audit
        )
        self._sessions: Dict[str, AgentSession] = {}
        self._sessions_lock = threading.Lock()
        self._ttl_seconds = ttl_seconds

    # ------------------------------------------------------------------ spawn
    def spawn(
        self,
        *,
        user_id: str = "anonymous",
        model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        instructions: Optional[str] = None,
        environment: str = "dev",
    ) -> AgentSession:
        session_id = str(uuid.uuid4())
        agent = build_devops_agent(tools=tools, model=model, instructions=instructions)
        context = DevOpsContext(user_id=user_id, environment=environment)
        session = AgentSession(session_id=session_id, agent=agent, context=context)
        with self._sessions_lock:
            self._sessions[session_id] = session
        self._audit.log(
            {
                "event": "session_spawn",
                "session_id": session_id,
                "user_id": user_id,
                "agent": agent.name,
                "model": agent.model,
                "tool_count": len(agent.tools),
            }
        )
        return session

    # ------------------------------------------------------------------ access
    def get(self, session_id: str) -> Optional[AgentSession]:
        with self._sessions_lock:
            return self._sessions.get(session_id)

    def require(self, session_id: str) -> AgentSession:
        session = self.get(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id}")
        return session

    def list(self) -> List[AgentSession]:
        with self._sessions_lock:
            return list(self._sessions.values())

    def close(self, session_id: str) -> bool:
        with self._sessions_lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        self._audit.log(
            {
                "event": "session_close",
                "session_id": session_id,
                "turns": session.run_count,
            }
        )
        return True

    # ------------------------------------------------------------------ run
    async def run(self, session_id: str, prompt: str) -> RunResult:
        session = self.require(session_id)
        async with session.lock:
            self._audit.log(
                {
                    "event": "session_run",
                    "session_id": session_id,
                    "prompt_chars": len(prompt),
                }
            )
            result = await self._runner.run(
                session.agent,
                prompt,
                context=session.context,
                history=session.history,
            )
            session.run_count += 1
            session.last_used_at = time.time()
            return result

    async def one_shot(
        self,
        prompt: str,
        *,
        user_id: str = "anonymous",
        model: Optional[str] = None,
        tools: Optional[List[Any]] = None,
    ) -> RunResult:
        """Run a prompt against a fresh, non-persisted agent."""
        agent = build_devops_agent(tools=tools, model=model)
        context = DevOpsContext(user_id=user_id)
        self._audit.log(
            {
                "event": "one_shot_run",
                "user_id": user_id,
                "prompt_chars": len(prompt),
                "model": agent.model,
            }
        )
        return await self._runner.run(agent, prompt, context=context)

    # ------------------------------------------------------------------ misc
    def prune_expired(self, now: Optional[float] = None) -> int:
        if not self._ttl_seconds:
            return 0
        cutoff = (now or time.time()) - self._ttl_seconds
        removed = 0
        with self._sessions_lock:
            stale = [
                sid for sid, s in self._sessions.items() if s.last_used_at < cutoff
            ]
            for sid in stale:
                self._sessions.pop(sid, None)
                removed += 1
        if removed:
            self._audit.log({"event": "session_prune", "removed": removed})
        return removed


_default_store: Optional[AgentSessionStore] = None
_default_lock = threading.Lock()


def get_session_store() -> AgentSessionStore:
    """Return a process-wide default :class:`AgentSessionStore`."""
    global _default_store
    if _default_store is None:
        with _default_lock:
            if _default_store is None:
                _default_store = AgentSessionStore()
    return _default_store


def set_session_store(store: AgentSessionStore) -> None:
    """Override the default store (useful for tests)."""
    global _default_store
    with _default_lock:
        _default_store = store
