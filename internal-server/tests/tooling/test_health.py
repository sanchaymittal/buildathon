"""Sentry health watcher tests."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from src.docker_svc.compose_service import ComposeDeployService
from src.tooling import health


class _FakeClock:
    def __init__(self, steps):
        self._steps = list(steps)

    def __call__(self):
        return self._steps.pop(0)


def _fake_service(statuses):
    """Return a ComposeDeployService whose ``status`` returns canned data."""
    service = ComposeDeployService(skip_verification=True)
    service.status = lambda *a, **k: [
        SimpleNamespace(model_dump=lambda s=s: s) for s in statuses
    ]
    return service


def test_watch_returns_promote_when_healthy(mocker):
    service = _fake_service([{"state": "running"}])
    mocker.patch.object(
        health,
        "http_probe",
        return_value={"url": "http://x", "status": 200, "latency_ms": 10, "ok": True},
    )
    report = health.watch(
        project_path="/tmp/app",
        service=service,
        window_s=1,
        interval_s=1,
        healthcheck_url="http://x",
        clock=_FakeClock([0, 0, 0, 2]),
        sleeper=lambda s: None,
    )
    assert report["recommendation"] == "promote"
    assert report["samples"]


def test_watch_rolls_back_after_threshold(mocker):
    service = _fake_service([{"state": "exited"}])
    mocker.patch.object(
        health,
        "http_probe",
        return_value={"url": "http://x", "status": 500, "latency_ms": 5, "ok": False},
    )
    report = health.watch(
        project_path="/tmp/app",
        service=service,
        window_s=10,
        interval_s=1,
        healthcheck_url="http://x",
        unhealthy_threshold=2,
        clock=_FakeClock([0, 0, 0, 0, 0, 0]),
        sleeper=lambda s: None,
    )
    assert report["recommendation"] == "rollback"
    assert report["unhealthy_streak"] >= 2
