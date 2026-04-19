# Xerant — End-to-end quickstart

Three moving parts:

```
┌─────────────┐   stdio    ┌─────────────┐   HTTP   ┌─────────────────┐   Docker API   ┌──────────┐
│  OpenCode   │◀─────────▶│  xerant-mcp │◀────────▶│ internal-server │◀──────────────▶│  Docker  │
│  +  skill   │           │    (TS)     │          │   (FastAPI)     │                │  daemon  │
└─────────────┘            └─────────────┘          └─────────────────┘                └──────────┘
```

- **OpenCode skill** lives at `.agents/skills/xerant/`. Triggered by `/xerant`, `xerant --prod`, etc.
- **MCP server** (`mcp-server/`, TypeScript) is spawned by OpenCode over stdio and forwards calls to the internal API.
- **Internal server** (`internal-server/`, FastAPI) talks to the Docker daemon to build images from GitHub repos and run containers.

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

## 2. Build the MCP bridge

```bash
cd mcp-server
npm install
npm run build
```

This writes an executable to `mcp-server/dist/index.js`.

## 3. Register the MCP server with OpenCode

The workspace already ships an `opencode.json` pointing at `./mcp-server/dist/index.js`. Optional env vars you may want to export in the shell that launches `opencode`:

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

The skill will:

1. Resolve target repo/branch/env.
2. Call `xerant_health` + `xerant_docker_health` via MCP.
3. Ensure a local `Dockerfile` exists (proposing a template if not).
4. Diff the local Dockerfile against `Dockerfile` on the target branch in GitHub (via `xerant_github_get_file`).
5. Run security gates (`check-dockerfile.sh`): `.dockerignore`, ARG→ENV leaks, secret scan, hadolint.
6. Call `xerant_deploy` with `{repository, branch, environment, container_port, env, build_args}`.
7. Poll `xerant_get_deployment` and `xerant_deployment_logs` until running or failed.
8. Print a compact deploy report with URL, container id, and status.

Follow-up actions (no skill required, just ask OpenCode to use the tool):

```
use xerant_deployment_logs  id=<id>  tail=200
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
