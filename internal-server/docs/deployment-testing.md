# End-to-End Deployment Testing

This guide walks through a full local deployment cycle using the API and
CLI. It covers two flows:

1. **Compose MVP (recommended)** — deploy a local project directory that
   already contains a `Dockerfile` and a `compose.yml`. This is the
   primary flow per [AGENTS.md](../AGENTS.md). No GitHub access and no
   credentials are required.
2. **Legacy GitHub flow** — clone a public/private GitHub repo that has
   a root `Dockerfile` and run it as a single container. Requires the
   optional `docker` and `PyGithub` Python packages plus a
   `GITHUB_TOKEN`.

The **target repository contract** (per AGENTS.md) is the caller's
responsibility: the agent / skill calling this service supplies a local
path that already contains `Dockerfile` + `compose.yml`. The server does
not hunt for a Dockerfile in subdirectories or generate one.

---

## Prerequisites

- Python 3.9+
- Docker daemon running locally (`docker ps` should succeed)
- `docker compose` CLI on PATH (Docker Desktop ships this by default)
- For the **legacy GitHub flow only**: `GITHUB_TOKEN` exported or
  stored in `~/.devops/credentials.json`, plus `pip install docker PyGithub`

Confirm Docker connectivity before starting:

```bash
docker ps
docker compose version
```

## 1) Install

Minimum install for the Compose MVP flow:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pydantic fastapi 'uvicorn[standard]' pytest pytest-mock pytest-asyncio httpx
```

Full install (pulls in optional deps for the legacy flow, Gemini agents,
and the team system):

```bash
pip install -r requirements.txt
```

## 2) Start the API Server

Pick a port that does **not** collide with the port your compose
project publishes. The bundled `examples/sample-app` binds `8000:8000`,
so run the API on something else:

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8765 --reload
```

Verify health:

```bash
curl -s http://localhost:8765/health
curl -s http://localhost:8765/health/compose    # MVP flow ping
curl -s http://localhost:8765/health/docker     # legacy flow ping (503 if docker-py missing)
```

All three should return `{"status":"healthy",...}` on a working setup.

---

## Flow A — Compose MVP (recommended)

These endpoints operate on a local path. The caller prepares a directory
with a `Dockerfile` + `compose.yml` and hands that path to the server.

### A.1 Deploy the bundled sample

```bash
curl -s -X POST http://localhost:8765/compose/up \
  -H 'content-type: application/json' \
  -d '{"project_path": "examples/sample-app"}'
```

Expected response (abbreviated):

```json
{
  "status": "succeeded",
  "project_name": "sample-app-75def5",
  "project_path": "/abs/.../examples/sample-app",
  "compose_file": "/abs/.../examples/sample-app/compose.yml",
  "services": [
    {"service": "web", "state": "running", "status": "Up ...", "ports": "..."}
  ],
  "agents_md_excerpt": "..."
}
```

Compose-level build/run failures return **HTTP 200** with
`status="failed"` and the underlying `error` / `output` populated, so the
caller can inspect them.

### A.2 Hit the deployed app

The sample-app publishes on `8000`:

```bash
curl -s http://localhost:8000/
# Hello from Agentic DevOps
```

### A.3 Check status

```bash
curl -s -X POST http://localhost:8765/compose/status \
  -H 'content-type: application/json' \
  -d '{"project_path": "examples/sample-app"}'
```

Returns a JSON array of `ComposeServiceStatus` entries (`service`,
`container_id`, `name`, `state`, `status`, `ports`).

### A.4 Tail logs

```bash
curl -s -X POST http://localhost:8765/compose/logs \
  -H 'content-type: application/json' \
  -d '{"project_path": "examples/sample-app", "tail": 200}'
```

Filter to a single service:

```bash
curl -s -X POST http://localhost:8765/compose/logs \
  -H 'content-type: application/json' \
  -d '{"project_path": "examples/sample-app", "service": "web", "tail": 100}'
```

### A.5 Custom compose file / project name / env

```bash
curl -s -X POST http://localhost:8765/compose/up \
  -H 'content-type: application/json' \
  -d '{
        "project_path": "examples/sample-app",
        "compose_file": "compose.yml",
        "project_name": "sample-app-demo",
        "env": {"GREETING": "Hello from the test guide"},
        "build": true,
        "pull": false
      }'
```

If `compose_file` is omitted, the service auto-detects in this order:
`compose.yml` → `compose.yaml` → `docker-compose.yml` → `docker-compose.yaml`.

If `project_name` is omitted, it defaults to
`<basename(project_path)>-<sha1(abs_path)[:6]>`.

### A.6 Tear down

```bash
curl -s -X POST http://localhost:8765/compose/down \
  -H 'content-type: application/json' \
  -d '{"project_path": "examples/sample-app"}'
```

### A.7 CLI equivalent (no credentials needed)

```bash
python -m src.cli docker compose up     --path examples/sample-app
python -m src.cli docker compose up     --path examples/sample-app --env GREETING=hi --no-build
python -m src.cli docker compose status --path examples/sample-app
python -m src.cli docker compose logs   --path examples/sample-app --service web --tail 100
python -m src.cli docker compose down   --path examples/sample-app
```

---

## Flow B — Legacy GitHub flow (optional)

This path clones a GitHub repo, looks for a `Dockerfile` at its **root**,
builds a single image, and runs one container. It requires:

- `pip install docker PyGithub` (optional deps)
- `GITHUB_TOKEN` exported (needed even for public repos, to avoid anon
  rate limits, and required by the CLI even for read-only commands)

```bash
export GITHUB_TOKEN="<your_token_here>"
```

If the legacy deps are missing, the `/deployments`, `/containers`, and
`/github` routers do not register and those endpoints return 404; the
Compose MVP flow is unaffected.

### B.1 Create a deployment

The target repo must have a `Dockerfile` **at the root**. Monorepos or
repos with a Dockerfile in a subdirectory are not supported by this flow
— per the AGENTS.md contract, the caller should either deploy a
different branch that places the Dockerfile at the root, or use the
Compose MVP flow against a local checkout.

```bash
curl -s -X POST http://localhost:8765/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "docker/welcome-to-docker",
    "branch": "main",
    "container_port": 3000,
    "env": {"ENVIRONMENT": "staging"}
  }'
```

`container_port` must match the port the app actually binds to inside
the container (typically the `EXPOSE` line of the `Dockerfile`).

### B.2 User-scoped quick deploy

```bash
curl -s -X POST http://localhost:8765/deployments/quick \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "owner/repo",
    "user_id": "user-123",
    "branch": "main",
    "github_token": "<optional_token>"
  }'
```

### B.3 Replace an existing deployment

Delete any previous deployment for the same repo + user and redeploy:

```bash
curl -s -X POST http://localhost:8765/deployments/quick/replace \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "owner/repo",
    "user_id": "user-123",
    "branch": "main"
  }'
```

Returns immediately with a ticket (`status: "building"`), then continues
in the background.

### B.4 Status, logs, lifecycle

```bash
curl -s http://localhost:8765/deployments
curl -s http://localhost:8765/deployments/<deploy_id>
curl -s "http://localhost:8765/deployments/<deploy_id>/logs?tail=200"

curl -s -X POST http://localhost:8765/deployments/<deploy_id>/stop
curl -s -X POST http://localhost:8765/deployments/<deploy_id>/start
curl -s -X POST http://localhost:8765/deployments/<deploy_id>/restart

curl -s -X DELETE http://localhost:8765/deployments/<deploy_id>
```

### B.5 Container introspection (legacy flow only)

```bash
curl -s http://localhost:8765/containers
curl -s http://localhost:8765/containers/<container_id>
curl -s "http://localhost:8765/containers/<container_id>/logs?tail=200"
```

### B.6 CLI equivalent

```bash
python -m src.cli docker deploy --repo owner/repo --branch main --port 3000 --env ENVIRONMENT=staging
python -m src.cli docker list
python -m src.cli docker logs <deploy_id> --tail 200
python -m src.cli docker stop <deploy_id>
python -m src.cli docker start <deploy_id>
python -m src.cli docker rm <deploy_id>
```

Every `docker` (non-compose) subcommand requires `GITHUB_TOKEN` to be
set, even read-only ones like `list`.

---

## Troubleshooting

- **`503 Service Unavailable` from `/health/docker`** — the Docker
  daemon is not reachable, or the `docker` Python SDK is not installed.
  Start Docker Desktop, or `pip install docker` if only the legacy
  endpoints are needed.
- **`503 Service Unavailable` from `/health/compose`** — the
  `docker compose` CLI is missing or failing. Check `docker compose version`.
- **`404 Not Found` on `/deployments/*`, `/containers/*`, or
  `/github/*`** — the optional legacy dependencies (`docker`, `PyGithub`)
  are not installed. Either install them or use the Compose MVP flow.
- **`400 Bad Request` on `POST /deployments`** — the legacy flow failed
  to clone, find a root `Dockerfile`, or build. Common causes:
  - `No Dockerfile found in owner/repo:main` — the repo does not have a
    `Dockerfile` at the root. Per the AGENTS.md contract, the caller
    must provide a deployable target; point this flow at a different
    branch/repo, or switch to the Compose MVP flow with a local path.
  - `build_image failed: ... non-zero code: 1` — the Dockerfile build
    itself failed (missing `package-lock.json` for `npm ci`, compile
    error, etc.). Fix the upstream repo.
- **`POST /compose/up` returns `status: "failed"`** — the exit code from
  `docker compose up` was non-zero. Inspect `output` and `error` in the
  response; `agents_md_excerpt` may also hint at required env vars.
- **`HTTP 501 Unsupported method` on `/compose/*` endpoints** — you are
  hitting a port that is currently published by a compose service, not
  the API. The API and your compose stack must not share a host port.
  Run the API on a free port (e.g., `--port 8765`).
- **App does not respond on the expected port** — for the legacy flow
  confirm the repo actually `EXPOSE`s the `container_port` you supplied;
  for the Compose flow confirm the compose file's `ports:` section
  publishes what you expected.
