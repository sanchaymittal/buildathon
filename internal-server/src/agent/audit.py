"""
Append-only JSON-line audit logger for agent runs.

Each call to :meth:`AuditLogger.log` writes a single line to the configured
log file. The file path is resolved lazily from the config subsystem so tests
can override it without monkey-patching imports.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """Thread-safe append-only JSON-line logger."""

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = self._resolve_path(path)
        self._lock = threading.Lock()
        self._ensure_parent()

    @staticmethod
    def _resolve_path(path: Optional[str]) -> Path:
        if path:
            return Path(os.path.expanduser(path))
        try:
            from ..core.config import get_config_value

            configured = get_config_value("agent.log_file")
        except Exception:
            configured = None
        return Path(os.path.expanduser(configured or "~/.devops/agent.log"))

    def _ensure_parent(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover
            logger.debug("Could not create audit log directory: %s", exc)

    @property
    def path(self) -> Path:
        return self._path

    def log(self, payload: Dict[str, Any]) -> None:
        """Append a single JSON line with a timestamp."""
        entry = {"ts": time.time(), **payload}
        line = json.dumps(entry, default=str, separators=(",", ":"))
        with self._lock:
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to write audit log: %s", exc)


_default: Optional[AuditLogger] = None
_default_lock = threading.Lock()


def get_default_audit_logger() -> AuditLogger:
    """Return a process-wide default :class:`AuditLogger`."""
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                _default = AuditLogger()
    return _default
