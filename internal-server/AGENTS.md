# AGENTS.md

Guide for agentic coding agents working in this repository.

## Project Overview

`internal-server` is a hackathon-scoped DevOps agent server. It runs locally
and deploys a target repository as a Docker Compose stack on the local
Docker daemon. It exposes three surfaces:

- **HTTP API** (`src/api/`) — FastAPI app with `/compose/*` endpoints
  (MVP) and legacy `/deployments`, `/containers`, `/github` endpoints.
- **CLI** (`src/cli.py`) — `docker compose up/down/status/logs` for the
  MVP flow plus the legacy `docker deploy/list/logs/...` commands.
- **Agent tools** (`src/docker_svc/compose_tools.py`, `tools.py`) — async
  function tools for the OpenAI Agents SDK.

The primary (MVP) deployment flow is local-only: given a local path to a
repo that contains a `Dockerfile`, a compose file, and optionally an
`AGENTS.md`, the server/CLI/tool runs `docker compose up -d` on the local
Docker daemon. No auth, no cloud, no remote hosts, no registry push.

## Target Repository Contract

When the agent is asked to deploy a repo, that repo is expected to contain:

| File | Required | Notes |
| ---- | -------- | ----- |
| `Dockerfile` | Yes (or referenced from compose `build:`) | Image definition |
| `compose.yml` or `docker-compose.yml` | Yes | Compose v2 file the CLI understands |
| `AGENTS.md` | Optional | Free-form advisory notes; a short excerpt is surfaced back in the deploy result. No schema is enforced. |

The agent operates on a **local directory path** passed by the caller. It
does not clone from GitHub in the MVP flow.

## Build / Lint / Test Commands

```bash
# Install dependencies (full)
pip install -e .

# Minimum for the local-compose MVP flow
pip install pydantic fastapi 'uvicorn[standard]' pytest pytest-mock pytest-asyncio httpx

# Run all tests
pytest

# Run only compose/local-deploy tests
pytest -m docker

# Run a single test file
pytest tests/docker_svc/test_compose_service.py
pytest tests/api/test_compose.py

# Type check
mypy src/
```

Actually running a deploy (not just unit tests) needs a local Docker daemon
plus the `docker compose` CLI on PATH. Unit tests mock `subprocess.run` so
they run anywhere.

## HTTP API Quick Reference

The compose router is always available. Legacy routers register only when
their optional dependencies (`docker`, `openai-agents`, `PyGithub`) are
installed.

```
# Liveness
GET  /health
GET  /health/compose          # pings docker daemon via compose CLI
GET  /health/docker           # legacy ping via docker-py (503 if unavailable)

# Compose MVP
GET  /compose/ping
POST /compose/up              body: DeployLocalRequest
POST /compose/down            body: ComposeTargetRequest
POST /compose/status          body: ComposeTargetRequest
POST /compose/logs            body: ComposeLogsRequest

# Legacy single-container flow (docker-py)
POST /deployments             body: DeployRequest (GitHub clone + build + run)
GET  /deployments
GET  /deployments/{id}
GET  /deployments/{id}/logs
POST /deployments/{id}/stop
POST /deployments/{id}/start
POST /deployments/{id}/restart
POST /deployments/{id}/redeploy
DELETE /deployments/{id}

# Legacy container management
GET|POST|DELETE /containers[...]

# GitHub
GET  /github/repos/{owner}/{repo}[/issues|/branches|/pulls]
```

Example:

```bash
# Start the server
python -m src.cli serve --port 8000

# Deploy the bundled sample-app
curl -X POST http://localhost:8000/compose/up \
  -H 'content-type: application/json' \
  -d '{"project_path": "examples/sample-app"}'

# Tear it down
curl -X POST http://localhost:8000/compose/down \
  -H 'content-type: application/json' \
  -d '{"project_path": "examples/sample-app"}'
```

## CLI Quick Reference

```bash
# Local Docker Compose deployment (hackathon MVP)
python -m src.cli docker compose up    --path ./path/to/repo
python -m src.cli docker compose up    --path ./repo --env PORT=8080 --no-build
python -m src.cli docker compose status --path ./repo
python -m src.cli docker compose logs   --path ./repo --service web --tail 100
python -m src.cli docker compose down   --path ./repo

# Legacy GitHub-clone + single-container flow (requires docker-py + PyGithub)
python -m src.cli docker deploy --repo owner/repo
python -m src.cli serve --port 8000
```

## Code Style Guidelines

**Imports:**
- Standard library imports first, then third-party, then local (PEP 257 order)
- Use relative imports within the package: `from ..core.config import get_config`
- Use absolute imports for external packages: `import docker`, `from pydantic import BaseModel`

**Formatting:**
- Follow PEP 8 style
- 4-space indentation, max line length ~100 characters
- Double quotes for strings

**Types:**
- Python type hints on all function signatures
- `Optional[T]` for optional parameters
- Pydantic models for data structures

**Naming:**
- Classes: `PascalCase` (e.g., `DockerService`, `ComposeDeployService`, `Deployment`)
- Functions/methods: `snake_case` (e.g., `deploy_local_project`, `get_config`)

**Error Handling:**
- Custom exception hierarchy: `DockerServiceError` -> `ContainerNotFoundError`, `ImageBuildError`, `DockerDaemonError`, `ComposeDeployError`, ...
- Use the `@docker_operation` decorator for automatic error handling (legacy flow)
- Include `suggestion` fields on exceptions

**Class Pattern:**
- Legacy service classes: `DockerService`, `DockerDeployService`, `GitHubService` (depend on docker-py / PyGithub)
- Local-compose MVP service: `ComposeDeployService` — pure subprocess wrapping `docker compose`, no docker-py dependency
- Use dependency injection for credentials where applicable; the local-compose flow needs no credentials

**Docker Compose Service (MVP):**
- `ComposeDeployService` lives in `src/docker_svc/compose_service.py` and is pure-subprocess
- The single point of subprocess execution is `ComposeDeployService._run`, which tests patch via `mocker.patch("src.docker_svc.compose_service.subprocess.run", ...)`
- Compose filename auto-detection order: explicit → `compose.yml` → `compose.yaml` → `docker-compose.yml` → `docker-compose.yaml`
- Default project name: `<basename(path)>-<sha1(abs_path)[:6]>`

**FastAPI layer:**
- Compose router is always registered; legacy routers register conditionally via `routes/__init__.py`.
- Dependencies live in `src/api/dependencies.py`. `get_compose_service()` is dependency-light; `get_docker_service()` / `get_deploy_service()` / `get_github_service()` raise HTTP 503 when their optional deps are missing.
- Error mapping: `DockerDaemonError` → 503, `ComposeDeployError` / `DockerServiceError` → 400. Compose-level failures (non-zero `up` exit) return 200 with `status="failed"` so the caller can inspect details.

**Testing:**
- Test files in `tests/` mirror `src/` structure
- `pytest-mock` patches `subprocess.run` — no real Docker daemon needed
- API tests use `TestClient` + `app.dependency_overrides` to inject fake services
- Test class names: `TestClassName`; test function names: `test_descriptive_name`
- Mark Docker/compose tests with `@pytest.mark.docker`

## Repository Structure

```
internal-server/
  src/
    docker_svc/
      __init__.py
      base.py              # Exception hierarchy + @docker_operation
      models.py            # Legacy single-container models
      service.py           # Legacy DockerService (docker-py, optional)
      deploy.py            # Legacy GitHub-clone + single container (optional)
      tools.py             # Legacy agent tools (requires `agents`, optional)
      compose_models.py    # Local-compose MVP pydantic models
      compose_service.py   # ComposeDeployService (pure subprocess)
      compose_tools.py     # Agent tools for the MVP flow
    github/                # GitHub service module (optional)
    core/                  # Shared: config, context, credentials, guardrails
    api/
      app.py               # FastAPI app
      dependencies.py      # DI: get_compose_service, get_docker_service, ...
      routes/
        __init__.py        # Conditional legacy router imports
        compose.py         # /compose/* endpoints (MVP)
        deployments.py     # /deployments/* (legacy, optional)
        containers.py      # /containers/* (legacy, optional)
        github.py          # /github/* (legacy, optional)
    __init__.py            # Public API exports
    cli.py                 # CLI entry point
  tests/
    docker_svc/
      conftest.py          # tmp_project / mock_run fixtures
      test_compose_service.py
      test_deploy.py       # Legacy tests (importorskip)
    api/
      test_compose.py
      test_deployments.py  # Legacy tests
    github/
    core/
  examples/
    sample-app/            # Tiny Dockerfile + compose.yml + AGENTS.md
    docker_compose_local_deploy.py
  pytest.ini
  setup.py
  requirements.txt
```

## Key Conventions

- **Backend:** All public API is exported through `src/__init__.py`
- **Backend:** Services use dependency injection for credentials; default to credential manager
- **Backend:** Optional heavy dependencies (`docker`, `agents`, `PyGithub`) are imported defensively so the local-compose flow stays usable in minimal environments
- **Backend:** The `DevOpsContext` pydantic model carries user/operation context
- **Docker (MVP):** `ComposeDeployService` shells out to `docker compose` — no docker-py required
- **Docker (legacy):** Uses docker-py SDK for container operations
- **API:** FastAPI serves HTTP endpoints on port 8000 by default
- **Never hardcode secrets:** Use environment variables or credential managers

## Git Branch Naming

- `feature/` — new features
- `fix/` — bug fixes
- `docs/` — documentation
