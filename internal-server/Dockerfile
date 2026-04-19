# syntax=docker/dockerfile:1.7
# Xerant internal DevOps API — multi-stage Python build.
#
# The server talks to a Docker daemon to build and run deployments. At runtime
# either:
#   (a) bind-mount the host daemon:
#         -v /var/run/docker.sock:/var/run/docker.sock
#   (b) point at a remote daemon via env:
#         -e DOCKER_BASE_URL=tcp://host.docker.internal:2375
#
# GitHub token must be supplied at runtime:
#         -e GITHUB_TOKEN=ghp_...
# Don't bake secrets into the image.

ARG PYTHON_VERSION=3.11.10-slim-bookworm

# ---- base with wheels ----------------------------------------------------
FROM python:${PYTHON_VERSION} AS builder
WORKDIR /build

# Build tools for any C extensions pulled in by deps.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip wheel --wheel-dir=/build/wheels --no-cache-dir -r requirements.txt

# ---- runtime ------------------------------------------------------------
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

# Minimal runtime deps. `docker` python client uses the CLI socket path or tcp;
# no docker binary needed inside the container itself.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini curl git \
 && rm -rf /var/lib/apt/lists/* \
 && addgroup --system --gid 1001 xerant \
 && adduser  --system --uid 1001 --ingroup xerant --home /app xerant

WORKDIR /app

COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# App code. Copy last so source changes don't bust the dep cache.
COPY --chown=xerant:xerant src ./src
COPY --chown=xerant:xerant setup.py pytest.ini ./

# docker group so the user can access a bind-mounted /var/run/docker.sock on
# typical Linux hosts (GID 999). Override at run time with --group-add on macOS.
RUN groupadd --system --gid 999 docker 2>/dev/null || true \
 && usermod -aG docker xerant

USER xerant

EXPOSE 8000

# Health probe for orchestrators.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}"]
