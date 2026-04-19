# @xerant/mcp-server

Model Context Protocol bridge between OpenCode (or any MCP client) and the Xerant internal DevOps API.

```
OpenCode ── stdio ──▶ xerant-mcp (this package) ── HTTP ──▶ internal-server (FastAPI) ──▶ Docker
```

## Install & build

```bash
cd mcp-server
npm install
npm run build
```

This produces an executable at `dist/index.js`.

## Environment

| Var | Default | Purpose |
|-----|---------|---------|
| `XERANT_API_URL` | `http://localhost:8000` | Base URL of the internal-server FastAPI service |
| `XERANT_API_KEY` | *(unset)* | Optional bearer token forwarded on every request |
| `XERANT_API_TIMEOUT_MS` | `60000` | Per-request timeout |

The API key is only sent as `Authorization: Bearer <key>`. It is **never** written to disk, logged, or echoed.

## Register in OpenCode

Add to your `opencode.json` (workspace-level or `~/.config/opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "xerant": {
      "type": "local",
      "command": ["node", "./mcp-server/dist/index.js"],
      "environment": {
        "XERANT_API_URL": "{env:XERANT_API_URL}",
        "XERANT_API_KEY": "{env:XERANT_API_KEY}"
      },
      "enabled": true
    }
  }
}
```

If you prefer running from source without a build step, swap the command for:

```json
"command": ["npx", "-y", "tsx", "./mcp-server/src/index.ts"]
```

## Tools exposed

| Tool | Maps to |
|------|---------|
| `xerant_health` | `GET /health` |
| `xerant_docker_health` | `GET /health/docker` |
| `xerant_deploy` | `POST /deployments` |
| `xerant_list_deployments` | `GET /deployments` |
| `xerant_get_deployment` | `GET /deployments/{id}` |
| `xerant_deployment_logs` | `GET /deployments/{id}/logs` |
| `xerant_stop_deployment` | `POST /deployments/{id}/stop` |
| `xerant_start_deployment` | `POST /deployments/{id}/start` |
| `xerant_restart_deployment` | `POST /deployments/{id}/restart` |
| `xerant_redeploy` | `POST /deployments/{id}/redeploy` |
| `xerant_remove_deployment` | `DELETE /deployments/{id}` |
| `xerant_list_containers` | `GET /containers` |
| `xerant_get_container` | `GET /containers/{id}` |
| `xerant_container_logs` | `GET /containers/{id}/logs` |
| `xerant_github_get_repo` | `GET /github/repos/{owner}/{repo}` |
| `xerant_github_list_branches` | `GET /github/repos/{owner}/{repo}/branches` |
| `xerant_github_get_file` | `GET /github/repos/{owner}/{repo}/contents/{path}?ref=...` |

### `xerant_deploy` mapping details

The tool accepts an `environment` argument (`prod|staging|preview|dev` or their long forms) that the server itself does not understand. The bridge maps it to:

- `env.DEPLOY_ENV = <canonical>` injected into the runtime env
- `name = <repo-name>-<canonical>` derived automatically (override with explicit `name`)

## Development

```bash
# Run from source with hot reload (stdio client will still attach)
npm run dev

# Typecheck only
npm run typecheck

# Manual smoke test: call the `tools/list` method over stdio
node dist/index.js
# paste: {"jsonrpc":"2.0","id":1,"method":"tools/list"}\n
```
