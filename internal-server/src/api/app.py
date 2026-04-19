"""
FastAPI Application - Main API entry point.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .routes import deployments, containers, github
from ..docker_svc.service import DockerService
from ..docker_svc.base import DockerDaemonError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Agentic DevOps API")
    yield
    logger.info("Shutting down Agentic DevOps API")


app = FastAPI(
    title="Agentic DevOps API",
    description="AI-powered Docker deployment platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deployments.router)
app.include_router(containers.router)
app.include_router(github.router)


@app.get("/health", tags=["health"])
def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "service": "agentic-devops"},
    )


@app.get("/health/docker", tags=["health"])
def docker_health_check() -> JSONResponse:
    """Check Docker daemon health."""
    try:
        docker = DockerService()
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
        "agentic_devops.src.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run()