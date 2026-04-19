"""
FastAPI Application - Main API entry point.

The compose router (``/compose/*``) is always registered. The legacy routers
(``/deployments``, ``/containers``, ``/github``) register conditionally
depending on whether the optional ``docker`` / ``agents`` / ``PyGithub``
packages are installed. This keeps the server bootable in a minimal
hackathon environment while preserving the legacy surface when its
dependencies are present.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from . import routes
from ..docker_svc.base import DockerDaemonError, DockerServiceError
from ..docker_svc.compose_service import ComposeDeployService

try:  # pragma: no cover - depends on optional deps
    from ..docker_svc.service import DockerService  # type: ignore

    _LEGACY_DOCKER_AVAILABLE = True
except Exception:  # pragma: no cover
    DockerService = None  # type: ignore[assignment]
    _LEGACY_DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    from ..gemini_agents.client import is_available as gemini_sdk_available

    logger.info("Starting Agentic DevOps API")
    if not gemini_sdk_available():
        logger.info(
            "Gemini runtime disabled (install 'google-generativeai' to enable live agent runs)"
        )
    if not routes._LEGACY_DOCKER_ROUTES:
        logger.info(
            "Legacy Docker routes disabled (install 'docker' + 'openai-agents' to enable)"
        )
    if not routes._GITHUB_ROUTES:
        logger.info("GitHub routes disabled (install 'PyGithub' to enable)")
    yield
    logger.info("Shutting down Agentic DevOps API")


app = FastAPI(
    title="Agentic DevOps API",
    description=(
        "AI-powered Docker deployment platform. MVP flow: POST a local repo "
        "path to /compose/up to run it on the host Docker daemon."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Always register the compose, agent, and mcp routers.
app.include_router(routes.compose.router)
app.include_router(routes.agent_routes.router)
app.include_router(routes.mcp.router)

# Register legacy routers only when their underlying deps loaded.
if routes._LEGACY_DOCKER_ROUTES:  # pragma: no branch
    app.include_router(routes.deployments.router)
    app.include_router(routes.containers.router)

if routes._GITHUB_ROUTES:  # pragma: no branch
    app.include_router(routes.github_routes.router)


@app.get("/health", tags=["health"])
def health_check() -> JSONResponse:
    """Liveness check."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "service": "agentic-devops"},
    )


@app.get("/health/compose", tags=["health"])
def compose_health_check() -> JSONResponse:
    """Check that the local Docker daemon is reachable via the compose flow."""
    service = ComposeDeployService(skip_verification=True)
    try:
        service.ping()
    except DockerServiceError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "docker": str(exc)},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "docker": "connected"},
    )


@app.get("/health/gemini", tags=["health"])
def gemini_health_check() -> JSONResponse:
    """Check that Gemini credentials and SDK are available."""
    from ..core.credentials import CredentialError, get_credential_manager
    from ..gemini_agents.client import is_available as gemini_sdk_available

    if not gemini_sdk_available():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "gemini": "google-generativeai not installed",
            },
        )
    try:
        creds = get_credential_manager().get_gemini_credentials()
    except CredentialError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "gemini": str(exc)},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "gemini": "configured",
            "model": creds.model,
        },
    )


@app.get("/health/docker", tags=["health"])
def docker_health_check() -> JSONResponse:
    """Legacy Docker daemon health check (via docker-py)."""
    if not _LEGACY_DOCKER_AVAILABLE:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "docker": "legacy flow unavailable; use /health/compose",
            },
        )
    try:
        docker = DockerService()  # type: ignore[misc]
        docker.client.ping()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "docker": "connected"},
        )
    except DockerDaemonError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "docker": str(e)},
        )


def run(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the API server."""
    import uvicorn

    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run()
