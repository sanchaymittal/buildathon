# Xerant — End-to-end quickstart

> **Just want to use the skill in your own project?** Skip this and run:
>
> ```bash
> curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh | bash
> ```
>
> Details: [`.agents/skills/xerant/README.md`](.agents/skills/xerant/README.md) · Latest release: [v0.1.0](https://github.com/sanchaymittal/buildathon/releases/latest) · npm: [`xerant-mcp-server`](https://www.npmjs.com/package/xerant-mcp-server).
>
> This document is for **developers of this repo** who want to run the whole stack locally (internal-server + MCP bridge + skill) end-to-end.

Three moving parts:

```
┌─────────────┐   stdio    ┌─────────────┐   HTTP   ┌─────────────────┐   Docker API   ┌──────────┐
│  OpenCode   │◀─────────▶│  xerant-mcp │◀────────▶│ internal-server │◀──────────────▶│  Docker  │
│  +  skill   │           │    (TS)     │          │   (FastAPI)     │                │  daemon  │
└─────────────┘            └─────────────┘          └─────────────────┘                └──────────┘
```

- **OpenCode skill** lives at `.agents/skills/xerant/`. Triggered by `/xerant`, `xerant --prod`, etc. See its [README](.agents/skills/xerant/README.md) for the user-facing story.
- **MCP server** (`mcp-server/`, TypeScript). Published to npm as [`xerant-mcp-server`](https://www.npmjs.com/package/xerant-mcp-server). Spawned by OpenCode over stdio; forwards calls to the internal API.
- **Internal server** (`internal-server/`, FastAPI). Talks to the Docker daemon. Supports two deploy flows: local `docker compose` (MVP) and GitHub-clone single-container (legacy).

## 1. Start the internal server

Prereqs on the host:
- Docker daemon running
- GitHub PAT with `repo` scope

```bash
cd internal-server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export GITHUB_TOKEN=ghp_your_token_here
python -m src.api.app   # listens on :8000
```

Or run it as a container (bind-mount the docker socket so it can drive Docker):

```bash
cd internal-server
docker build -t xerant-internal-server:dev .
docker run --rm -p 8000:8000 \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -v /var/run/docker.sock:/var/run/docker.sock \
  xerant-internal-server:dev
```

Sanity check:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/health/docker
```

## 1.5 Run frontend + backend together (Docker)

If you want the Xerant UI and API together:

```bash
export DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
docker compose up --build
```

Note: the backend runs as root in Docker Compose to ensure it can access the host Docker socket.

Then open:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## 2. MCP bridge

You have three options — pick whichever fits your dev loop:

### Option A: Use the npm package (easiest)

No build needed. `opencode.json` just references `npx`:

```json
"command": ["npx", "-y", "xerant-mcp-server@latest"]
```

See [npmjs.com/package/xerant-mcp-server](https://www.npmjs.com/package/xerant-mcp-server).

### Option B: Rebuild the bundled binary from local source

```bash
cd mcp-server
npm install
npm run bundle      # writes single-file bundle to .agents/skills/xerant/bin/xerant-mcp.mjs
```

The committed `opencode.json` points at this bundle. Drop-in installs into other projects also use it.

### Option C: Watch-mode from TypeScript source

```bash
cd mcp-server
npm install
npm run dev         # tsx, hot-reloads on source changes
```

Point `opencode.json` command at `["npx", "-y", "tsx", "./mcp-server/src/index.ts"]`.

### Publishing a new version

```bash
cd mcp-server
npm version patch   # or minor / major
npm publish         # prompts for 2FA OTP
```

## 3. Register the MCP server with OpenCode

The workspace already ships an `opencode.json` pointing at `./.agents/skills/xerant/bin/xerant-mcp.mjs` (the committed bundle). For drop-in into another project, run `.agents/skills/xerant/install.sh` from that project's root — see the skill's [README](.agents/skills/xerant/README.md) for details.

Optional env vars you may want to export in the shell that launches `opencode`:

```bash
export XERANT_API_URL=http://localhost:8000     # or wherever the server lives
export XERANT_API_KEY=…                          # optional; forwarded as Bearer
```

Restart OpenCode so it picks up the new MCP server. Confirm registration:

```
opencode mcp list
```

## 4. Use the skill

From a project you want to deploy:

```
/xerant --prod
```

The skill auto-picks a flow based on the project contents.

### Compose flow (MVP, primary — triggered when a `compose.yml` exists)

1. Resolve target path + environment tier.
2. `xerant_health` + `xerant_compose_ping` pre-flight.
3. Ensure `Dockerfile` + `compose.yml` + `.dockerignore` (offers templates if missing).
4. Security gates: `.dockerignore` coverage, ARG→ENV leaks, secret scan, hadolint, plus compose-specific checks (sensitive bind-mounts, privileged, low-port bindings, `.env` env_file).
5. Call `xerant_compose_up` with `{project_path, env: {DEPLOY_ENV: <tier>}}`.
6. Poll `xerant_compose_status`; print service URLs + state.

### Legacy GitHub flow (fallback — no compose file, has `origin` + `Dockerfile`)

1. Resolve repo/branch from `git remote`.
2. `xerant_health` + `xerant_docker_health` pre-flight.
3. Ensure local `Dockerfile` + `.dockerignore`.
4. Diff local Dockerfile against the target branch on GitHub via `xerant_github_get_file`.
5. Security gates.
6. `xerant_deploy` with `{repository, branch, environment, container_port, env, build_args}`.
7. Poll `xerant_get_deployment` + `xerant_deployment_logs` until running or failed.

### Follow-up ops (no skill required)

```
use xerant_deployment_logs  id=<id>  tail=200
use xerant_compose_status   project_path=.
use xerant_restart_deployment  id=<id>
use xerant_redeploy  id=<id>
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `xerant_health` returns error | internal-server not running | `curl http://localhost:8000/health` to verify |
| `xerant_docker_health` reports unhealthy | Docker daemon not reachable from server | Bind-mount `/var/run/docker.sock` or set `DOCKER_BASE_URL` |
| Skill reports remote Dockerfile missing | Not pushed to target branch | `git push origin <branch>` then retry |
| Skill reports remote differs from local | Uncommitted local changes | Decide: push local, or deploy what's on remote |
| Security gate fails with ARG→ENV leak | `ARG X` + `ENV X=${X}` pattern | Use `RUN --mount=type=secret` instead of promoting ARG to ENV |
| Secret scan hit in build context | Literal credentials in repo | Remove or replace with runtime env; add path to `.dockerignore` |

## Directory map

```
.
├── .agents/skills/xerant/       # OpenCode skill (workflow + scripts + templates)
├── internal-server/             # FastAPI DevOps API (Python)
├── mcp-server/                  # MCP bridge (TypeScript, stdio)
├── opencode.json                # Registers xerant MCP with OpenCode
└── xerant/                      # (unrelated) marketing landing page
```
