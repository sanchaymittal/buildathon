# Agentic DevOps API Reference

Base URL defaults to `http://localhost:8000`. All endpoints return JSON responses and use standard HTTP status codes.

## Authentication
This API assumes the server has been configured with access credentials:

- Docker access is derived from the host environment or `DEVOPS_DOCKER__*` configuration.
- GitHub requests reuse the token configured for the running service (environment variables or `~/.devops/credentials.json`).

No additional headers are required by callers once the backend is provisioned.

## Error Handling
- `400 Bad Request`: Validation failures, Docker or GitHub service errors.
- `401 Unauthorized`: GitHub credentials missing when hitting GitHub endpoints.
- `404 Not Found`: Requested resource is unknown (deployment ID, container ID, repository path, etc.).
- `503 Service Unavailable`: Docker health check cannot reach the daemon.

Error payloads follow FastAPI’s default structure: `{ "detail": "message" }`.

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

### `GET /health/docker`
Verifies Docker connectivity.

Responses:
- `200 OK` with `{ "status": "healthy", "docker": "connected" }`.
- `503 Service Unavailable` with `{ "status": "unhealthy", "docker": "<error>" }` when the daemon is unreachable.

---

## Deployments

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
- `201 Created` with a `Deployment` body (includes `user_id`).
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
