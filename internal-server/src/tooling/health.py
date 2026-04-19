"""Health watchers for Sentry.

Two primitives:
- :func:`poll_services` - snapshot of compose service state for a project.
- :func:`http_probe`    - single-shot HTTP GET with latency metrics.
- :func:`watch`         - time-boxed sampling loop combining the above.
"""

from __future__ import annotations

import time
from typing import Callable, List, Literal, Optional

from ..docker_svc.compose_models import ComposeTargetRequest
from ..docker_svc.compose_service import ComposeDeployService


def poll_services(
    service: ComposeDeployService,
    *,
    project_path: str,
    project_name: Optional[str] = None,
    compose_file: Optional[str] = None,
) -> List[dict]:
    statuses = service.status(
        ComposeTargetRequest(
            project_path=project_path,
            project_name=project_name,
            compose_file=compose_file,
        )
    )
    return [s.model_dump() for s in statuses]


def http_probe(url: str, timeout_s: int = 5) -> dict:
    """Single HTTP GET with timing."""
    import requests  # type: ignore

    start = time.monotonic()
    try:
        response = requests.get(url, timeout=timeout_s)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "url": url,
            "status": response.status_code,
            "latency_ms": latency_ms,
            "ok": 200 <= response.status_code < 400,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "url": url,
            "status": None,
            "latency_ms": latency_ms,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def watch(
    *,
    project_path: str,
    service: ComposeDeployService,
    project_name: Optional[str] = None,
    compose_file: Optional[str] = None,
    window_s: int = 60,
    interval_s: int = 5,
    healthcheck_url: Optional[str] = None,
    unhealthy_threshold: int = 3,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict:
    """Poll services + optional HTTP probe for ``window_s`` seconds.

    Returns a structured report. Decides ``recommendation`` based on the
    number of consecutive unhealthy samples: if any sample set exceeds
    ``unhealthy_threshold`` the recommendation is ``rollback``; otherwise
    ``hold`` while the window is still open and ``promote`` after clean
    completion.
    """
    deadline = clock() + window_s
    samples: List[dict] = []
    unhealthy_streak = 0
    recommendation: Literal["promote", "rollback", "hold"] = "hold"

    while clock() < deadline:
        service_snapshot = poll_services(
            service,
            project_path=project_path,
            project_name=project_name,
            compose_file=compose_file,
        )
        probe = (
            http_probe(healthcheck_url)
            if healthcheck_url
            else {"skipped": True, "ok": True}
        )
        services_ok = (
            all(
                (svc.get("state") or "").lower() == "running"
                or (svc.get("status") or "").lower().startswith("up")
                for svc in service_snapshot
            )
            if service_snapshot
            else False
        )

        sample_ok = services_ok and probe.get("ok", False)
        sample = {
            "timestamp": time.time(),
            "services": service_snapshot,
            "probe": probe,
            "ok": sample_ok,
        }
        samples.append(sample)

        if sample_ok:
            unhealthy_streak = 0
        else:
            unhealthy_streak += 1
            if unhealthy_streak >= unhealthy_threshold:
                recommendation = "rollback"
                break

        sleeper(interval_s)

    if recommendation != "rollback":
        # Window elapsed cleanly (or with <threshold unhealthy samples).
        if samples and samples[-1]["ok"]:
            recommendation = "promote"
        else:
            recommendation = "hold"

    return {
        "window_s": window_s,
        "interval_s": interval_s,
        "samples": samples,
        "unhealthy_streak": unhealthy_streak,
        "recommendation": recommendation,
    }
