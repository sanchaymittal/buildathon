"""
Agent package - spawning and orchestrating Gemini-backed DevOps agents.

Public API:

- :func:`build_devops_agent` - factory that assembles tools, guardrails, and
  the system prompt into a ready-to-run :class:`Agent`.
- :class:`AgentSession` and :class:`AgentSessionStore` - in-memory session
  management with per-session conversation history and optional audit logging.
- :class:`AuditLogger` - append-only JSON-line logger used by the runner.
- :class:`RunResult` / :class:`ToolCallRecord` - re-exported from
  :mod:`src.gemini_agents.runner` for convenience.
"""

from .audit import AuditLogger, get_default_audit_logger
from .factory import build_devops_agent, default_tools
from .prompts import DEVOPS_SYSTEM_PROMPT
from .sessions import AgentSession, AgentSessionStore, get_session_store
from ..gemini_agents.runner import (
    AgentGuardrailError,
    AgentRunError,
    RunResult,
    ToolCallRecord,
)

__all__ = [
    "AuditLogger",
    "get_default_audit_logger",
    "build_devops_agent",
    "default_tools",
    "DEVOPS_SYSTEM_PROMPT",
    "AgentSession",
    "AgentSessionStore",
    "get_session_store",
    "RunResult",
    "ToolCallRecord",
    "AgentRunError",
    "AgentGuardrailError",
]
