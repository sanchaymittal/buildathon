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
GitHub and Docker credentials are loaded via `src/core/credentials.py`:
- GitHub token: set `GITHUB_TOKEN` or add it to `~/.devops/credentials.json` under `{"github": {"token": "..."}}`.
- Docker remote access: `DOCKER_BASE_URL`, `DOCKER_TLS_VERIFY`, and `DOCKER_CERT_PATH` when targeting remote daemons.

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

## Gemini Agents Integration
The `gemini_agents.function_tool` decorators in `src/docker_svc/tools.py` and `src/github/github_tools.py` expose Docker and GitHub capabilities to Gemini Agents. Guardrails in `src/core/guardrails.py` provide security and sensitive-information tripwires for both inputs and outputs.

## Testing
```bash
pytest
```

The tests rely on mocks and do not require a live Docker daemon or GitHub network access.

## Project Status
The package is currently version `0.2.0` (alpha). Expect rapid iteration and breaking changes while APIs solidify.
