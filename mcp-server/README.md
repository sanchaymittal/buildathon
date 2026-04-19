# xerant-mcp-server

[![npm](https://img.shields.io/npm/v/xerant-mcp-server.svg)](https://www.npmjs.com/package/xerant-mcp-server)
[![node](https://img.shields.io/node/v/xerant-mcp-server.svg)](https://nodejs.org)

Model Context Protocol bridge between OpenCode (or any MCP client) and the Xerant internal DevOps API. Exposes 22 tools over stdio.

```
OpenCode ── stdio ──▶ xerant-mcp-server ── HTTP ──▶ internal-server (FastAPI) ──▶ Docker
```

## Install

### From npm (recommended)

No install step — spawn on demand with `npx`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "xerant": {
      "type": "local",
      "command": ["npx", "-y", "xerant-mcp-server@latest"],
      "environment": {
        "XERANT_API_URL": "{env:XERANT_API_URL}",
        "XERANT_API_KEY": "{env:XERANT_API_KEY}"
      },
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

Pin a version with `xerant-mcp-server@0.1.0` if you want deterministic behaviour.

### From source (for dev on this repo)

```bash
cd mcp-server
npm install
npm run build          # writes dist/index.js
# OR
npm run bundle         # writes a single-file bundle to ../.agents/skills/xerant/bin/xerant-mcp.mjs
```

Then point `opencode.json` at the local build:

```json
"command": ["node", "./mcp-server/dist/index.js"]
```

For watch-mode during development:

```json
"command": ["npx", "-y", "tsx", "./mcp-server/src/index.ts"]
```

## Environment

| Var | Default | Purpose |
|-----|---------|---------|
| `XERANT_API_URL` | `http://localhost:8000` | Base URL of the internal-server FastAPI service |
| `XERANT_API_KEY` | *(unset)* | Optional bearer token forwarded on every request |
| `XERANT_API_TIMEOUT_MS` | `60000` | Per-request timeout |

The API key is only sent as `Authorization: Bearer <key>`. It is **never** written to disk, logged, or echoed.

## Tools exposed (22)

| Tool | Maps to |
|------|---------|
| `xerant_health` | `GET /health` |
| `xerant_docker_health` | `GET /health/docker` |
| `xerant_compose_ping` | `GET /compose/ping` |
| `xerant_compose_up` | `POST /compose/up` |
| `xerant_compose_down` | `POST /compose/down` |
| `xerant_compose_status` | `POST /compose/status` |
| `xerant_compose_logs` | `POST /compose/logs` |
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

The tool accepts an `environment` argument (`prod|staging|preview|dev` or their long forms) that the server itself does not model. The bridge translates it into:

- `env.DEPLOY_ENV = <canonical>` injected into the runtime env
- `name = <repo-name>-<canonical>` derived automatically (override with explicit `name`)

## Development

```bash
# Run from source with hot reload (stdio client will still attach)
npm run dev

# Typecheck only
npm run typecheck

# Manual smoke test: handshake + tools/list over stdio
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | node dist/index.js 2>/dev/null | tail -1
```

## Publishing

```bash
npm version patch      # or minor / major; bumps + commits + tags
npm publish            # prompts for 2FA OTP
git push --follow-tags
```

`prepublishOnly` runs `clean + build`, so the dist is always fresh. The tarball ships `dist/` + `README.md` only (see `files` in package.json).

## Related

- **[Skill README](../.agents/skills/xerant/README.md)** — user-facing install + usage.
- **[GitHub releases](https://github.com/sanchaymittal/buildathon/releases)** — tagged tarballs of the skill folder.
- **[internal-server/AGENTS.md](../internal-server/AGENTS.md)** — the FastAPI surface this bridge wraps.

## License

MIT
