---
name: xerant
description: >
  DevOps workflow that deploys a project to the Xerant internal platform via the
  `xerant-mcp` MCP server (which forwards to the internal FastAPI service).
  Supports two flows:

    1. COMPOSE (MVP, default) — deploy a local project directory with a Dockerfile
       and compose.yml using `docker compose up -d` on the internal server's host.
    2. LEGACY GITHUB — deploy a GitHub repo+branch; the server clones and builds
       a single container.

  Both flows run a security audit on the local Dockerfile + compose.yml before
  deploy. Supported environments: prod, staging, preview, dev (mapped to
  project_name suffix and DEPLOY_ENV env var).
  Trigger when the user says "xerant", "xerant --prod|--staging|--preview|--dev",
  "xerant --path ...", "xerant --repo ...", "deploy to xerant", or invokes /xerant.
---

# xerant — Deploy to the Xerant Platform

End-to-end deploy pipeline with two flows. The **compose** flow is the hackathon MVP and is preferred whenever a local `compose.yml` is available.

```
OpenCode ── stdio ──▶ xerant-mcp ── HTTP ──▶ internal-server ──▶ Docker
```

## Drop-in install (any project)

The skill is fully self-contained — scripts, templates, and a pre-bundled MCP server binary live entirely inside this directory.

To add it to any project:

```bash
# From the target project root:
cp -r /path/to/buildathon/.agents/skills/xerant .agents/skills/xerant

# Or drop via curl once the skill is served somewhere:
#   curl -fsSL https://.../xerant-skill.tar.gz | tar -xz -C .agents/skills/

# Wire it into OpenCode (creates or merges opencode.json):
bash .agents/skills/xerant/install.sh

# Restart OpenCode. The `xerant` MCP server auto-starts on demand.
```

Requirements on the host:
- **Node.js ≥ 20** (for the bundled MCP binary; `install.sh` enforces this).
- An internal-server instance reachable at `XERANT_API_URL` (default `http://localhost:8000`). Start it with `python -m src.cli serve` from `internal-server/` or via its `Dockerfile`.

What `install.sh` does:
1. Verifies `bin/xerant-mcp.mjs` is present and executable.
2. Writes or merges an `mcp.xerant` block into `./opencode.json`, using a **relative** path so the config stays portable across machines.
3. Runs a stdio self-test (`tools/list`) to confirm the 22 tools load.

The installer never writes secrets. `XERANT_API_URL` / `XERANT_API_KEY` are read from the user's shell env at run time.

## Invocation

Trigger on any of:
- `/xerant`
- `xerant`                              — auto-detect flow
- `xerant --prod | --staging | --preview | --dev`
- `xerant --path <dir>`                 — force COMPOSE flow against `<dir>`
- `xerant --repo <owner/repo> [--branch <b>]`  — force LEGACY flow
- `deploy to xerant …`

If no environment flag is given, ask the user.

## Flow selection (when not forced)

1. Is there a compose file (`compose.yml`, `compose.yaml`, `docker-compose.yml`, `docker-compose.yaml`) in the project root? → **COMPOSE** flow.
2. Otherwise, is there a GitHub `origin` remote and a `Dockerfile`? → **LEGACY GITHUB** flow.
3. Otherwise, offer to scaffold a compose setup (see Step 3 below) and default to COMPOSE.

## Required environment

- `XERANT_API_KEY` *(optional)* — forwarded as `Authorization: Bearer …`. Server currently ignores; forward-compatible. Never log, echo, or write.
- `XERANT_API_URL` *(optional)* — default `http://localhost:8000`.
- `GITHUB_TOKEN` is only relevant for the LEGACY flow, and it's server-side (the skill never touches it).

## Required MCP tools

### Always

- `xerant_health`

### COMPOSE flow

- `xerant_compose_ping` *(pre-flight)*
- `xerant_compose_up`, `xerant_compose_down`, `xerant_compose_status`, `xerant_compose_logs`

### LEGACY GITHUB flow

- `xerant_docker_health` *(pre-flight)*
- `xerant_deploy`, `xerant_get_deployment`, `xerant_deployment_logs`
- `xerant_github_list_branches`, `xerant_github_get_file` *(for remote Dockerfile parity)*

If a required tool is missing, stop and tell the user to register `xerant-mcp` in `opencode.json` (see `mcp-server/README.md`).

---

## COMPOSE flow

### Step 1 — Resolve target

Gather:
- `project_path` — default to the current working directory, or the `--path` value.
- `environment` — from the flag; ask if missing.
- `project_name` — default `<basename(project_path)>-<environment>` if environment set, else let the server derive it.
- `env` — any user-specified runtime env vars. Always inject `DEPLOY_ENV=<canonical>` when an environment is set.
- `build` — default `true`. Set to `false` only if the user passes `--no-build`.

### Step 2 — Pre-flight

1. `xerant_health` — expect `healthy`.
2. `xerant_compose_ping` — verifies the server-side Docker daemon. Stop on failure.

### Step 3 — Ensure project files

Required in `project_path`:
- `Dockerfile` (or referenced from compose `build:`)
- A compose file (`compose.yml` preferred)

If `Dockerfile` is missing, propose a template from `templates/` as before.

If no compose file exists, propose `templates/compose.yml` (single service, sensible defaults). Show the diff and ask for confirmation before writing.

If `.dockerignore` is missing, copy `templates/.dockerignore` after showing it.

### Step 4 — Security gates

Run `scripts/check-dockerfile.sh` (existing gates: `.dockerignore`, ARG→ENV leaks, secret scan, optional hadolint).

Additionally for compose:
- Scan `compose.yml` for secrets (same patterns as `scan-secrets.sh` applied to the compose file text).
- Flag any `volumes:` entry that bind-mounts a sensitive host path (`/var/run/docker.sock`, `/root`, `~/.ssh`, `~/.aws`, `~/.docker`, `/etc/`, `/var/lib/`). If present, warn prominently and require explicit user confirmation (or `--force`).
- Flag any `ports:` entry that binds `0.0.0.0:<port>` to a port `<= 1024` without a clear reason.
- Warn if any service has `privileged: true`.

Halt on hard findings.

### Step 5 — Deploy

Call `xerant_compose_up` with:

```json
{
  "project_path": "<abs path>",
  "project_name": "<optional>",
  "env": { "DEPLOY_ENV": "<canonical>", ... },
  "build": true
}
```

The tool returns a `DeployLocalResult`:

```json
{
  "status": "succeeded" | "failed",
  "project_name": "...",
  "project_path": "...",
  "compose_file": "compose.yml",
  "services": [ { "service": "web", "state": "running", "ports": "0.0.0.0:8080->80/tcp", ... } ],
  "output": "...",
  "error": null,
  "agents_md_excerpt": "..."
}
```

### Step 6 — Verify & report

If `status == "failed"`:
- Pull `xerant_compose_logs` with `tail=200` and show the output verbatim.
- Print the `error` field.
- Suggest fixes based on the error (e.g., missing image, port collision).

If `status == "succeeded"`:
- List services with their `state` and `ports`.
- If any service is `running`, extract the host port from `ports` and print a curl-friendly URL (`http://localhost:<port>`).
- If `agents_md_excerpt` is present, show it so the user sees repo-provided notes.

---

## LEGACY GITHUB flow

This is the existing flow, preserved for repos where the internal server must clone from GitHub and build a single container itself.

### Step 1 — Resolve target

- `repository` — from `git remote get-url origin` or `--repo`. Convert to `owner/repo`.
- `branch` — from `git rev-parse --abbrev-ref HEAD` or `--branch`. Refuse on detached HEAD.
- `container_port` — default `80`. Ask if unusual.
- `environment` — from flag; ask if missing.

### Step 2 — Pre-flight

1. `xerant_health` → `healthy`.
2. `xerant_docker_health` → `healthy`. Stop if the daemon is unreachable.

### Step 3 — Ensure local Dockerfile exists

Same as COMPOSE Step 3, but compose file is not required.

### Step 4 — Remote Dockerfile parity

Because the server builds from GitHub, not from the local checkout:

1. Call `xerant_github_get_file` with `{owner, repo, path: "Dockerfile", ref: branch}`.
2. Diff against local:
   - **Identical** → proceed.
   - **Remote missing** → stop; instruct user to push the Dockerfile.
   - **Remote differs** → show the diff; ask whether to push local or deploy remote as-is.

If `git status --porcelain` includes `Dockerfile`, warn: local is uncommitted.

### Step 5 — Security gates

`scripts/check-dockerfile.sh` — same gates as COMPOSE. No compose-file-specific checks.

### Step 6 — Deploy

Call `xerant_deploy`:

```json
{
  "repository": "<owner/repo>",
  "branch": "<branch>",
  "environment": "<prod|staging|preview|dev>",
  "container_port": <port>,
  "env": { /* user-provided */ },
  "build_args": { /* user-provided */ }
}
```

The MCP bridge injects `DEPLOY_ENV` and derives `name = <repo>-<environment>`.

### Step 7 — Verify

Poll `xerant_get_deployment` until `status` is `running` or `failed`. On failure, pull `xerant_deployment_logs` with `tail=200`.

---

## Report format (both flows)

```
Flow              <compose|legacy>
Project           <compose: project_name @ path | legacy: owner/repo@branch (sha)>
Environment       <canonical>
Status            <succeeded|running|failed>
Services          (compose) list of name → state → ports
URL               (if running)
Auth              XERANT_API_KEY [set|unset]
```

On failure: failing step + underlying error + suggested next step.

## Boundaries

- **Never** echo `XERANT_API_KEY`.
- **Never** skip a failed security gate without an explicit `--force` that gets logged.
- **Never** modify local files (Dockerfile, compose.yml, .dockerignore) without showing the change first.
- **Never** call destructive tools (`xerant_remove_deployment`, `xerant_compose_down`) unprompted.
- Don't combine with the `caveman` skill — deploy output must stay readable.

## Files in this skill

```
.agents/skills/xerant/
├── SKILL.md                   # this file
├── install.sh                 # drop-in installer (merges opencode.json)
├── bin/
│   └── xerant-mcp.mjs         # pre-bundled MCP server (single-file, Node >= 20)
├── scripts/
│   ├── check-dockerfile.sh    # security gate runner (Dockerfile + compose)
│   ├── scan-secrets.sh        # secret-pattern scanner
│   └── deploy.sh              # legacy CLI fallback when MCP unavailable
└── templates/
    ├── Dockerfile.nextjs
    ├── Dockerfile.node
    ├── Dockerfile.generic
    ├── compose.yml            # single-service starter for the MVP flow
    └── .dockerignore
```

The MCP server source lives in `mcp-server/` at the repo root. Re-bundle after source changes with:

```bash
cd mcp-server && npm install && npm run bundle
```

`npm run bundle` writes the bundled binary directly into this skill's `bin/xerant-mcp.mjs` via esbuild.

## MCP tool catalog

Platform:
- `xerant_health`, `xerant_docker_health`, `xerant_compose_ping`

Compose (MVP):
- `xerant_compose_up`, `xerant_compose_down`, `xerant_compose_status`, `xerant_compose_logs`

Legacy GitHub:
- `xerant_deploy`, `xerant_list_deployments`, `xerant_get_deployment`, `xerant_deployment_logs`
- `xerant_stop_deployment`, `xerant_start_deployment`, `xerant_restart_deployment`, `xerant_redeploy`, `xerant_remove_deployment`

Containers / GitHub:
- `xerant_list_containers`, `xerant_get_container`, `xerant_container_logs`
- `xerant_github_get_repo`, `xerant_github_list_branches`, `xerant_github_get_file`

Use these for follow-up ops (tail logs, restart, redeploy, etc.) without re-running the skill.
