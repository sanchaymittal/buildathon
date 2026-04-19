# DevOps Agent

AI-assisted DevOps toolkit that bundles Docker deployment automation, GitHub operations, and Gemini Agents guardrails into a single backend service and CLI.

## Features
- Deploy GitHub repositories straight to Docker with managed container lifecycles.
- Discover and manipulate running containers through a safe abstraction layer.
- Query GitHub repositories, issues, branches, and pull requests with caching and rich error handling.
- Expose everything through a FastAPI backend, an argparse-powered CLI, and Gemini Agents-compatible function tools.
- Guardrails that screen inputs and outputs for dangerous commands or sensitive information before they reach infrastructure.

## Architecture Overview
- `src/docker_svc/`: Docker client wrappers, deployment orchestrator, and agent tools.
- `src/github/`: REST and PyGithub integrations plus agent-facing tools.
- `src/core/`: Shared configuration, credential management, runtime context, and safety guardrails.
- `src/api/`: FastAPI application with health checks and routes for deployments, containers, and GitHub data.
- `src/cli.py`: End-user CLI mirroring API capabilities and providing a lightweight server launcher.
- `tests/`: pytest suites with extensive mocking to exercise services without touching real infrastructure.

## Prerequisites
- Python 3.9+
- Docker daemon reachable from the host running the service
- GitHub personal access token when interacting with private repositories or the GitHub API

## Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

For editable installs (enables the `devops-agent` console script):
```bash
pip install -e .
```

## Configuration
The service reads configuration and secrets in this order:
1. Defaults defined in `src/core/config.py`.
2. Optional config file pointed to by `DEVOPS_CONFIG_FILE` (defaults to `~/.devops/config.yaml`). Supports YAML or JSON.
3. Environment variables prefixed with `DEVOPS_`, using double underscores for nesting (example: `DEVOPS_DOCKER__BASE_URL=http://127.0.0.1:2375`).

### Credentials
Credentials are loaded via `src/core/credentials.py` in this precedence order:
process environment → `~/.devops/credentials.json` → config file defaults.

- **Gemini API key (required for the agent):** set `GEMINI_API_KEY` (preferred)
  or `GOOGLE_API_KEY`. Alternatively add it to
  `~/.devops/credentials.json`:
  ```json
  {
    "gemini": {
      "api_key": "AIza...",
      "model": "gemini-2.5-flash"
    }
  }
  ```
  Override the model with `GEMINI_MODEL=gemini-2.5-pro` or
  `DEVOPS_GEMINI__MODEL=gemini-2.5-pro`.

- **GitHub token (optional):** set `GITHUB_TOKEN` or add it to
  `~/.devops/credentials.json` under `{"github": {"token": "..."}}`.

- **Docker remote access (optional):** `DOCKER_BASE_URL`, `DOCKER_TLS_VERIFY`,
  `DOCKER_CERT_PATH` when targeting remote daemons (legacy flow only).

A starter `.env.example` is included; copy it to `.env` and fill in the
values you need. The MVP compose flow requires no credentials at all; only
the Gemini agent and the legacy GitHub / remote-Docker flows do.

## Usage

### CLI
The CLI mirrors API functionality. Install the project in editable mode or run with `python -m src.cli`.

```bash
# Deploy a repository
devops-agent docker deploy --repo owner/app --branch main --port 8000 --env KEY=VALUE,FLAG=1

# Inspect deployments and containers
devops-agent docker list
devops-agent docker logs <deploy_id> --tail 200
devops-agent docker ps --all

# Interact with GitHub
devops-agent github list-repos --org my-org
devops-agent github get-repo app --owner my-org

# Launch the FastAPI server
devops-agent serve --host 0.0.0.0 --port 8000 --reload
```

Run `devops-agent --help`, `devops-agent docker --help`, or `devops-agent github --help` for subcommand details.

### FastAPI Server
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Two ready-made health probes are available:
- `GET /health`
- `GET /health/docker`

A full endpoint catalog lives in [docs/api.md](docs/api.md).
MCP access for external agents is documented in [docs/mcp.md](docs/mcp.md).

## Gemini Agents Integration

The internal server spawns real Gemini-backed DevOps agents that call the
project's compose / Docker / GitHub tools through a proper function-calling
loop (`src/gemini_agents/runner.py`).

### Where to put the API key

Any of these (first one found wins):

1. `GEMINI_API_KEY` environment variable (preferred)
2. `GOOGLE_API_KEY` environment variable
3. `~/.devops/credentials.json` → `{"gemini": {"api_key": "..."}}`

See `.env.example` in the repo root.

### How spawning works

- `src/agent/factory.py` assembles an `Agent` with a default tool set that
  starts with the local-compose MVP (`deploy_local_project`,
  `project_status`, `stop_local_project`, `project_logs`) and extends with
  legacy Docker and GitHub tools whenever their optional dependencies are
  installed.
- `src/agent/sessions.py` keeps sessions in memory, each with its own
  conversation history, `DevOpsContext`, and async lock.
- `src/gemini_agents/runner.py` converts the function-tool signatures to
  Gemini function declarations, runs the tool-call loop (capped at 16
  calls by default), and applies input/output guardrails from
  `src/core/guardrails.py`.
- Every turn is appended as a JSON line to `~/.devops/agent.log`
  (override with `DEVOPS_AGENT__LOG_FILE`).

### HTTP surface (`/agent/*`)

```
POST /agent/run                         # one-shot prompt
POST /agent/sessions                    # spawn a session
GET  /agent/sessions                    # list sessions
GET  /agent/sessions/{id}               # session summary
POST /agent/sessions/{id}/run           # run a prompt against a session
DELETE /agent/sessions/{id}             # close a session
GET  /health/gemini                     # key + SDK availability check
```

### CLI

```bash
# One-shot
devops-agent agent run "Deploy examples/sample-app and tail the web logs"

# Persistent sessions (in-process only)
SID=$(devops-agent agent spawn)
devops-agent agent session-run "$SID" "What services are running?"
devops-agent agent sessions
devops-agent agent close "$SID"
```

The low-level `gemini_agents.function_tool` decorators in
`src/docker_svc/tools.py`, `src/docker_svc/compose_tools.py`, and
`src/github/github_tools.py` are what actually get wired into the
Gemini function-calling loop.

## Testing
```bash
pytest
```

The tests rely on mocks and do not require a live Docker daemon or GitHub network access.

## Project Status
The package is currently version `0.2.0` (alpha). Expect rapid iteration and breaking changes while APIs solidify.
