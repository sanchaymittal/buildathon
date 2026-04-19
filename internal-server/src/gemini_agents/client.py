"""
Gemini client helpers.

Thin wrapper around ``google.generativeai`` that centralises:

* reading ``GeminiCredentials`` from the credential manager,
* calling ``genai.configure`` exactly once per key,
* instantiating ``GenerativeModel`` objects with tool bindings.

The heavy import is guarded so the rest of the package still works in
environments where ``google-generativeai`` is not installed (tests, minimal
compose-only installs).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, List, Optional

from ..core.credentials import GeminiCredentials

logger = logging.getLogger(__name__)

try:  # pragma: no cover - depends on optional deps
    import google.generativeai as genai  # type: ignore

    _GENAI_AVAILABLE = True
except Exception:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    _GENAI_AVAILABLE = False


class GeminiUnavailableError(RuntimeError):
    """Raised when ``google-generativeai`` is not importable."""


_CONFIGURED_KEY: Optional[str] = None
_CONFIGURE_LOCK = threading.Lock()


def is_available() -> bool:
    """Return True if the Gemini SDK is importable."""
    return _GENAI_AVAILABLE


def _ensure_configured(creds: GeminiCredentials) -> None:
    """Call ``genai.configure`` once per distinct API key."""
    if not _GENAI_AVAILABLE:
        raise GeminiUnavailableError(
            "google-generativeai is not installed. Run 'pip install google-generativeai'."
        )

    global _CONFIGURED_KEY
    with _CONFIGURE_LOCK:
        if _CONFIGURED_KEY == creds.api_key:
            return
        kwargs: dict = {"api_key": creds.api_key}
        if creds.api_base:
            kwargs["client_options"] = {"api_endpoint": creds.api_base}
        genai.configure(**kwargs)  # type: ignore[union-attr]
        _CONFIGURED_KEY = creds.api_key
        logger.info("Configured google-generativeai (model default=%s)", creds.model)


def build_model(
    creds: GeminiCredentials,
    model_override: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    system_instruction: Optional[str] = None,
) -> Any:
    """
    Build a ``GenerativeModel`` bound to tools and a system instruction.

    Args:
        creds: Gemini credentials (API key + default model).
        model_override: Optional model name that overrides ``creds.model``
            (e.g. ``"gemini-2.5-pro"``).
        tools: Optional list of Gemini tool declarations. For function tools
            pass a list of ``genai.protos.Tool`` (or the simpler
            ``{"function_declarations": [...]}`` dict form) built by the
            runner.
        system_instruction: Optional plain-text system prompt.

    Returns:
        A ``google.generativeai.GenerativeModel`` instance.

    Raises:
        GeminiUnavailableError: if the SDK isn't importable.
    """
    _ensure_configured(creds)
    model_name = model_override or creds.model
    return genai.GenerativeModel(  # type: ignore[union-attr]
        model_name=model_name,
        tools=tools,
        system_instruction=system_instruction,
    )
