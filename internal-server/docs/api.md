# Agentic DevOps API Reference

Base URL defaults to `http://localhost:8000`. All endpoints return JSON
responses and use standard HTTP status codes.

The server exposes two parallel deploy surfaces:

- **Compose MVP (recommended, always available)** — `/compose/*`
  endpoints operate on a local project directory that already contains
  a `Dockerfile` and a `compose.yml`. This matches the target-repo
  contract described in [AGENTS.md](../AGENTS.md): the caller provides
  a deployable local path; the server does not hunt for Dockerfiles or
  generate build manifests.
- **Legacy GitHub flow (optional)** — `/deployments/*`, `/containers/*`,
  and `/github/*` clone a GitHub repo, look for a root `Dockerfile`,
  and run one container. These routers only register when the optional
  `docker` and `PyGithub` packages are installed; otherwise they return
  404.

## Authentication
This API assumes the server has been configured with access credentials
for the flows you intend to use:

- The **Compose MVP flow** needs no credentials. It only requires a
  local Docker daemon and the `docker compose` CLI on PATH.
- **Docker (legacy) access** is derived from the host environment or
  `DEVOPS_DOCKER__*` configuration.
- **GitHub (legacy) requests** reuse the token configured for the
  running service (environment variables or
  `~/.devops/credentials.json`).

No additional headers are required by callers once the backend is provisioned.

## Error Handling
- `200 OK` with `status: "failed"`: `POST /compose/up` returns 200 even
  when `docker compose up` exits non-zero, so callers can inspect the
  captured `output` / `error` fields.
- `400 Bad Request`: Validation failures, legacy Docker or GitHub
  service errors (e.g., no root Dockerfile, build failure).
- `401 Unauthorized`: GitHub credentials missing when hitting GitHub endpoints.
- `404 Not Found`: Requested resource is unknown (deployment ID,
  container ID, repository path, etc.), or an optional router
  (`/deployments`, `/containers`, `/github`) did not register because
  its dependency is missing.
- `503 Service Unavailable`: Docker / Compose health check cannot reach
  the daemon.

Error payloads follow FastAPI’s default structure: `{ "detail": "message" }`.

---

## Compose MVP

### Models

- **DeployLocalRequest**
  - `project_path` *(string, required)* — absolute or relative path to
    the local project directory.
  - `compose_file` *(string, optional)* — compose filename relative to
    `project_path`. Auto-detects `compose.yml` → `compose.yaml` →
    `docker-compose.yml` → `docker-compose.yaml` when omitted.
  - `project_name` *(string, optional)* — compose project name.
    Defaults to `<basename(project_path)>-<sha1(abs_path)[:6]>`.
  - `env` *(object, default `{}`)* — environment variables passed to
    `docker compose up`.
  - `env_file` *(string, optional)* — path relative to `project_path`
    pointing at a `.env` file.
  - `build` *(bool, default `true`)* — pass `--build` to `up`.
  - `pull` *(bool, default `false`)* — pass `--pull always` to `up`.
- **ComposeTargetRequest** — reference to an existing compose project.
  Fields: `project_path`, optional `compose_file`, optional
  `project_name` (defaults are the same as above).
- **ComposeLogsRequest** — extends `ComposeTargetRequest` with
  `service` *(string, optional)* and `tail` *(int, default `200`)*.
- **ComposeServiceStatus** — `service`, `container_id`, `name`,
  `state`, `status`, `ports`.
- **DeployLocalResult** — `status` (`"succeeded"` / `"failed"`),
  `project_name`, `project_path`, `compose_file`,
  `services[ComposeServiceStatus]`, `output`, `error`,
  `agents_md_excerpt`.

### `GET /compose/ping`

Pings the local Docker daemon via the `docker compose` CLI. Returns
`{ "status": "ok" }` on success.

### `POST /compose/up`

Run `docker compose up -d` for the supplied project path.

Request body: `DeployLocalRequest`.

Responses:
- `200 OK` with a `DeployLocalResult`. `status` is `"succeeded"` on a
  clean bring-up. Compose-level failures return the same shape with
  `status="failed"` and the captured `output` / `error` populated; this
  is intentional so the caller can inspect details without an HTTP 4xx.

### `POST /compose/down`

Run `docker compose down` for the supplied project.

Request body: `ComposeTargetRequest`.

Response: `200 OK` with `{ "output": "<compose stderr/stdout>" }`.

### `POST /compose/status`

Return per-service status for a running compose project.

Request body: `ComposeTargetRequest`.

Response: `200 OK` with `ComposeServiceStatus[]`.

### `POST /compose/logs`

Return recent logs for the compose project (optionally filtered to a
single service).

Request body: `ComposeLogsRequest`.

Response: `200 OK` with `{ "logs": "<text>" }`.

---

## MCP (Model Context Protocol)

The MCP adapter exposes a minimal, open tool surface for external agents. No auth is required.

### `POST /mcp/tools/list`
List available MCP tools.

Response: `200 OK` with `{ "tools": [ ... ] }`.

### `POST /mcp/tools/call`
Invoke an MCP tool.

Request body:
```json
{
  "name": "deploy_quick",
  "arguments": {
    "repository": "owner/repo",
    "user_id": "user-123"
  }
}
```

Response body:
```json
{
  "result": {
    "id": "4c9b1b72",
    "user_id": "user-123",
    "repository": "owner/repo",
    "branch": "main",
    "image": "devops-repo:main-4c9b1b72",
    "container_id": "...",
    "container_name": "devops-repo-4c9b1b72",
    "host_port": 32788,
    "container_port": 80,
    "url": "http://localhost:32788",
    "status": "running",
    "created_at": "2026-04-19T10:40:12.321928",
    "env": {},
    "labels": {
      "managed-by": "devops-agent",
      "deployment-id": "4c9b1b72",
      "repository": "owner/repo",
      "branch": "main",
      "user-id": "user-123"
    }
  },
  "is_error": false
}
```

---

## Health

### `GET /health`
Simple heartbeat that returns `{ "status": "healthy", "service": "agentic-devops" }`.

### `GET /health/compose`
Verifies local Docker connectivity via the `docker compose` CLI (MVP flow).

Responses:
- `200 OK` with `{ "status": "healthy", "docker": "connected" }`.
- `503 Service Unavailable` when the CLI is missing or the daemon is
  unreachable.

### `GET /health/docker`
Verifies Docker connectivity via `docker-py` (legacy flow).

Responses:
- `200 OK` with `{ "status": "healthy", "docker": "connected" }`.
- `503 Service Unavailable` with `{ "status": "unhealthy", "docker": "<error>" }`
  when the daemon is unreachable **or** the `docker` Python SDK is not
  installed.

---

## Deployments (legacy GitHub flow)

> Requires the optional `docker` (`docker-py`) and `PyGithub` packages.
> If either is missing, the `/deployments/*` and `/containers/*`
> routers do not register and all endpoints below return 404.
>
> This flow clones a GitHub repo and looks for a **root** `Dockerfile`.
> Repos with a Dockerfile in a subdirectory, multi-service compose
> projects, or generated build manifests are out of scope — per the
> AGENTS.md contract the caller is responsible for providing a
> deployable target. For those cases, use the Compose MVP flow with a
> local checkout instead.

### Deployment Models
- **DeployRequest**
  - `repository` *(string, required)* – GitHub repo (`owner/name` or URL).
  - `branch` *(string, default `"main"`)* – Git branch to deploy.
  - `container_port` *(integer, default `80`)* – Internal container port.
  - `env` *(object, default `{}`)* – Environment variables to inject.
  - `build_args` *(object, default `{}`)* – Docker build arguments.
  - `name` *(string, optional)* – Friendly deployment name.
- **DeployUserRequest**
  - `repository` *(string, required)* – GitHub repo (`owner/name` or URL).
  - `user_id` *(string, required)* – Unique user identifier for tenant segregation.
  - `branch` *(string, default `"main"`)* – Git branch to deploy.
  - `github_token` *(string, optional)* – GitHub token for private repos.
- **Deployment**
  - `id` *(string)* – Deployment identifier.
  - `user_id` *(string|null)* – Associated user identifier when provided.
  - `repository`, `branch` *(strings)*.
  - `image` *(string)* – Built Docker image tag.
  - `container_id`, `container_name` *(strings).* 
  - `host_port`, `container_port` *(integers).* 
  - `url` *(string)* – Convenience access URL.
  - `status` *(string)* – `running`, `stopped`, `failed`, etc.
  - `created_at` *(ISO timestamp).* 
  - `logs_tail` *(string|null)* – Last log tail if captured.
  - `env` *(object)* – Environment variables used.
  - `labels` *(object)* – Docker labels applied to the container.
- **DeploymentTicket**
  - `id` *(string)* – Deployment identifier.
  - `user_id` *(string|null)* – Associated user identifier when provided.
  - `repository`, `branch` *(strings)*.
  - `status` *(string)* – `building`, `running`, `failed`.
  - `url` *(string)* – Access URL reserved at request time.

### `POST /deployments`
Create a deployment from a GitHub repository.

Request body: `DeployRequest`.

Responses:
- `201 Created` with a `Deployment` body.
- `400 Bad Request` if cloning, building, or startup fails.

### `POST /deployments/quick`
Create a deployment using only a GitHub repo and a `user_id`. Other settings use defaults.

Request body: `DeployUserRequest`.

Responses:
- `201 Created` with a `Deployment` body (includes `user_id`).
- `400 Bad Request` if cloning, building, or startup fails.

### `POST /deployments/quick/replace`
Delete any existing deployment for the same `repository` + `user_id`, then deploy fresh.

Request body: `DeployUserRequest`.

Responses:
- `201 Created` with a `DeploymentTicket` body (includes `user_id`, `status=building`, `url`).
- `400 Bad Request` if cloning, building, or startup fails.

### `GET /deployments`
List all known deployments.

Response: `200 OK` with `Deployment[]`.

### `GET /deployments/{deploy_id}`
Fetch a single deployment by ID.

Responses:
- `200 OK` with `Deployment`.
- `404 Not Found` if the ID is unknown.

### `GET /deployments/{deploy_id}/logs`
Return recent container logs.

Query parameters:
- `tail` *(integer, default `100`)* – Number of lines.

Responses:
- `200 OK` with `{ "deploy_id": "...", "logs": "<text>" }`.
- `404 Not Found` if the deployment does not exist.

### `POST /deployments/{deploy_id}/stop`
Stop a running deployment. Response mirrors `Deployment`.

### `POST /deployments/{deploy_id}/start`
Start a stopped deployment. Response mirrors `Deployment`.

### `POST /deployments/{deploy_id}/restart`
Restart an existing deployment. Response mirrors `Deployment`.

### `DELETE /deployments/{deploy_id}`
Remove the deployment and its resources.

Response: `200 OK` with `{ "status": "removed", "deployment_id": "..." }`.

### `POST /deployments/{deploy_id}/redeploy`
Redeploy from source (rebuild and launch a fresh container).

Responses:
- `200 OK` with a new `Deployment` descriptor.
- `400 Bad Request` if the redeploy attempt fails.

---

## Containers

Container responses are simple dictionaries capturing Docker metadata (`id`, `name`, `image`, `status`, `ports`, `labels`, etc.).

### `GET /containers`
List containers via Docker.

Query parameters:
- `all` *(bool, default `false`)* – Include stopped containers.
- `label_filter` *(string, optional)* – Supply `key=value` to filter by label.

Response: `200 OK` with `object[]`.

### `GET /containers/{container_id}`
Inspect a container.

Responses:
- `200 OK` with container details.
- `404 Not Found` if Docker cannot locate it.

### `GET /containers/{container_id}/logs`
Fetch container logs.

Query parameters:
- `tail` *(integer, default `100`)*.
- `timestamps` *(bool, default `false`)* – Include Docker timestamps.

Responses:
- `200 OK` with `{ "container_id": "...", "logs": "<text>" }`.
- `404 Not Found` if the container is missing.

### `POST /containers/{container_id}/stop`
Stop a container.

Query parameters:
- `force` *(bool, default `false`)* – Force stop.

Responses:
- `200 OK` with `{ "status": "stopped", "container_id": "..." }`.
- `404 Not Found` if the container cannot be reached.

### `POST /containers/{container_id}/start`
Start a container.

Response: `200 OK` with `{ "status": "started", "container_id": "..." }`.

### `POST /containers/{container_id}/restart`
Restart a container.

Response: `200 OK` with `{ "status": "restarted", "container_id": "..." }`.

### `DELETE /containers/{container_id}`
Remove a container.

Query parameters:
- `force` *(bool, default `false`)* – Force removal of running containers.

Response: `200 OK` with `{ "status": "removed", "container_id": "..." }`.

---

## GitHub

All GitHub endpoints proxy the authenticated service token and return GitHub REST payloads. Missing or invalid credentials trigger `401 Unauthorized`.

### `GET /github/repos/{owner}/{repo}`
Return repository details (same shape as `GET /repos/{owner}/{repo}` from GitHub’s API).

### `GET /github/repos/{owner}/{repo}/issues`
List issues.

Query parameters:
- `state` *(string, default `"open"`)* – `open`, `closed`, or `all`.

Response: `200 OK` with an array of issue dictionaries.

### `GET /github/repos/{owner}/{repo}/branches`
List branches for a repository.

Response: `200 OK` with GitHub branch objects (`name`, `commit`, etc.).

### `GET /github/repos/{owner}/{repo}/pulls`
List pull requests.

Query parameters:
- `state` *(string, default `"open"`)* – `open`, `closed`, or `all`.

Response: `200 OK` with an array of PR dictionaries.

---

## Sample Deployment Request
```json
{
  "repository": "acme/sample-app",
  "branch": "main",
  "container_port": 8080,
  "env": {
    "ENVIRONMENT": "staging",
    "FEATURE_FLAG": "true"
  },
  "build_args": {
    "PYTHON_VERSION": "3.11"
  }
}
```

## Sample Deployment Response
```json
{
  "id": "4c9b1b72",
  "repository": "acme/sample-app",
  "branch": "main",
  "image": "devops-sample-app:main-4c9b1b72",
  "container_id": "e1c5...",
  "container_name": "devops-sample-app-4c9b1b72",
  "host_port": 32788,
  "container_port": 8080,
  "url": "http://localhost:32788",
  "status": "running",
  "created_at": "2026-04-19T10:40:12.321928",
  "env": {
    "ENVIRONMENT": "staging",
    "FEATURE_FLAG": "true"
  },
  "labels": {
    "managed-by": "devops-agent",
    "deployment-id": "4c9b1b72",
    "repository": "acme/sample-app",
    "branch": "main"
  }
}
```
