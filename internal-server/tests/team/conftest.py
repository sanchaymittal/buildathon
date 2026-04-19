"""Shared fixtures for five-agent team tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_integration_stubs(monkeypatch):
    """Force every integration adapter back to the NullAdapter default.

    Tests that share process state with other modules (the global default
    adapter is lazy) could leak, so we reset them before each test.
    """
    from src.integrations import linear, slack, pagerduty, github_pr

    for mod in (linear, slack, pagerduty, github_pr):
        monkeypatch.setattr(mod, "_default", None, raising=False)
    yield
