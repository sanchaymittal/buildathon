# xerant skill

Deploy any project to the Xerant internal DevOps platform from OpenCode, in one invocation.

```
OpenCode ── stdio ──▶ xerant-mcp (bundled) ── HTTP ──▶ internal-server ──▶ Docker
```

This folder is the **entire skill** — workflow spec, installer, pre-built MCP bridge, security scripts, and Dockerfile / compose templates.

---

## Install (one line)

From the root of the project you want to deploy:

```bash
curl -fsSL https://xerant.cloud/install | sh
```

That's the whole install. The script downloads the skill into `.agents/skills/xerant/`, wires `./opencode.json`, and self-tests the 22 MCP tools. Then restart OpenCode and run:

```
/xerant --prod
```

### One-line alternatives

If you're somewhere `xerant.cloud` isn't reachable, or want a pinned ref:

```bash
# Direct from GitHub (always current main)
curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh | bash

# Pin to a specific ref / branch / tag / SHA
curl -fsSL https://xerant.cloud/install | XERANT_REF=v0.2.0 sh
```

### Install options (env vars)

| Var | Default | Purpose |
|---|---|---|
| `XERANT_REF` | `main` | Branch, tag, or commit SHA to pull the skill from |
| `XERANT_REPO` | `sanchaymittal/buildathon` | Override the source repo (for forks / mirrors) |
| `XERANT_TARGET` | `.agents/skills/xerant` | Destination directory inside your project |
| `XERANT_FORCE` | `0` | Set `1` to overwrite an existing skill dir |

### Offline / air-gapped install

The skill folder is fully self-contained (~750 KB including the bundled MCP). Copy it in by hand:

```bash
cp -r /path/to/xerant .agents/skills/xerant
bash .agents/skills/xerant/install.sh
```

No network calls are made after install.

---

## Requirements

| Requirement | Why |
|---|---|
| **Node.js ≥ 20** | To run the bundled MCP server (`install.sh` enforces this). Check with `node -v`. |
| **A reachable internal-server** | The MCP server forwards deploy calls to the FastAPI service. Default: `http://localhost:8000`. Set `XERANT_API_URL` to override. |
| **Docker daemon** (on the internal-server host) | Needed only by the internal-server, not by this skill. |

The skill itself does not need Docker, Python, or any build tools on the consumer side.

---

## Install

From the root of the project you want to deploy:

```bash
# option A: copy the folder in (assumes you've cloned buildathon nearby)
cp -r ~/github/buildathon/.agents/skills/xerant .agents/skills/xerant

# option B: fetch just the skill as a tarball (when hosted)
# curl -fsSL https://example.com/xerant-skill.tar.gz | tar -xz -C .agents/skills/

# Wire it into OpenCode
bash .agents/skills/xerant/install.sh
```

The installer:

1. Verifies `bin/xerant-mcp.mjs` exists and is executable.
2. Verifies Node.js ≥ 20.
3. Computes a project-relative path to the MCP binary.
4. Creates or merges an `mcp.xerant` block into `./opencode.json`. If the file exists, your other keys (`plugin`, `tools`, other MCP servers, etc.) are preserved. A timestamped backup is written as `opencode.json.bak.<epoch>` before any edit.
5. Runs a stdio self-test against the bundle to confirm the 22 MCP tools load.

It **does not**:

- Install or modify Node.js.
- Start the internal-server.
- Write any secrets. `XERANT_API_KEY` / `XERANT_API_URL` stay in your shell env.

### Configuration

After install, optionally export:

```bash
# Where the internal-server is running (default http://localhost:8000)
export XERANT_API_URL=http://localhost:8000

# Bearer token, if/when the server adds auth. Forward-compatible, ignored today.
export XERANT_API_KEY=…
```

Both are read lazily per MCP call. Nothing is persisted to disk by the skill.

### What `install.sh` writes to `opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "xerant": {
      "type": "local",
      "command": ["node", "./.agents/skills/xerant/bin/xerant-mcp.mjs"],
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

The `{env:…}` substitution is an OpenCode feature — at spawn time it reads your shell env and injects the values into the MCP process.

---

## Use

The skill auto-picks a deploy flow based on what's in your project.

### Compose flow (default when a `compose.yml` exists)

This is the **MVP / hackathon-preferred** path. The internal-server runs `docker compose up -d` on its host, using your local project directory.

```
/xerant --prod
```

or explicitly:

```
xerant --path .        # implicitly --dev unless env flag given
xerant --path . --staging
```

Workflow the skill runs:

1. Detects compose file → COMPOSE flow.
2. `xerant_health` + `xerant_compose_ping` pre-flight.
3. Ensures `Dockerfile` + `compose.yml` + `.dockerignore` exist (offers templates if missing).
4. Runs security gates (see below). Halts on any hard finding.
5. Calls `xerant_compose_up` with `{project_path, env: {DEPLOY_ENV: <tier>}}`.
6. Polls `xerant_compose_status` and prints service URLs + state.

### Legacy GitHub flow (fallback)

Used when there's no compose file but a `Dockerfile` + `origin` remote. The internal-server clones the repo, builds, and runs a single container.

```
xerant --repo owner/repo --branch main --prod
```

Workflow:

1. `xerant_health` + `xerant_docker_health` pre-flight.
2. Resolves repo + branch from `git remote` if not provided.
3. Fetches the remote Dockerfile via `xerant_github_get_file` and diffs against local. Halts if they differ or remote is missing.
4. Runs security gates.
5. Calls `xerant_deploy` with `{repository, branch, environment, container_port}`.
6. Polls `xerant_get_deployment`; tails `xerant_deployment_logs` on failure.

### Security gates (both flows)

Before any deploy:

- `.dockerignore` exists and covers `.env`, `.git`, `node_modules`, `*.pem`, `*.key`, `id_rsa`.
- No `ARG X` promoted to `ENV X=${X}` (classic secret leak).
- No literal secrets in Dockerfile or repo (AWS/GitHub/Slack/Google/OpenAI keys, private-key headers, heuristic `SECRET=`/`PASSWORD=` assignments). Placeholders like `EXAMPLE`, `changeme`, `<your-key>`, `${VAR}` are ignored.
- `hadolint` if installed (advisory).

Compose-specific (when a compose file is present):

- **Hard fail** on sensitive host bind-mounts (`docker.sock`, `/root`, `/etc`, `~/.ssh`, `~/.aws`, `~/.docker`, `~/.gnupg`).
- **Hard fail** on `privileged: true`.
- **Warn** on host port ≤ 1024 bindings.
- **Warn** on `env_file` referencing `.env` variants (usually git-ignored, must exist on host).

A hard finding stops the pipeline. The skill will show the exact offending line and suggest a fix. Bypassing requires explicit `--force`, which gets logged in the final report.

### Environment tiers

`--prod | --staging | --preview | --dev` maps to:

| Flag | Canonical | Injected |
|---|---|---|
| `--prod` | `production` | `DEPLOY_ENV=production`, name suffix `-production` |
| `--staging` | `staging` | `DEPLOY_ENV=staging`, name suffix `-staging` |
| `--preview` | `preview` | `DEPLOY_ENV=preview`, name suffix `-preview` |
| `--dev` | `development` | `DEPLOY_ENV=development`, name suffix `-development` |

---

## MCP tools exposed (22)

Available to the agent after install, not just via the skill:

| Tool | Purpose |
|---|---|
| `xerant_health` | `GET /health` — service liveness |
| `xerant_docker_health` | `GET /health/docker` — legacy docker-py daemon check |
| `xerant_compose_ping` | `GET /compose/ping` — compose-aware daemon check |
| `xerant_compose_up` / `_down` / `_status` / `_logs` | local-path compose ops |
| `xerant_deploy` / `_list_deployments` / `_get_deployment` / `_deployment_logs` | legacy GitHub-clone deploy ops |
| `xerant_stop_deployment` / `_start_deployment` / `_restart_deployment` / `_redeploy` / `_remove_deployment` | lifecycle ops on a deployment id |
| `xerant_list_containers` / `_get_container` / `_container_logs` | raw container inspection |
| `xerant_github_get_repo` / `_list_branches` / `_get_file` | repo metadata + remote Dockerfile fetch |

You can invoke them directly in a prompt without rerunning the skill:

> "Use `xerant_deployment_logs` with id=abc123 tail=300 to show why my last deploy failed."

---

## Verify the install

After `install.sh` completes, confirm the MCP server is reachable:

```bash
# Direct stdio handshake (no OpenCode required)
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | node .agents/skills/xerant/bin/xerant-mcp.mjs 2>/dev/null \
  | tail -1 | python3 -c 'import json,sys;d=json.loads(sys.stdin.read());print(len(d["result"]["tools"]),"tools")'
# Expected: 22 tools
```

Or through OpenCode once restarted:

```
opencode mcp list
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `curl https://xerant.cloud/install` → 404 | Marketing site redirect not deployed yet | Use the raw GitHub URL instead: `curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh \| bash` |
| `install-remote.sh` says "Destination already exists" | Previous install present | Re-run with `XERANT_FORCE=1`: `curl ... \| XERANT_FORCE=1 sh` |
| Extract failed ("repo may not contain") | Bad `XERANT_REF` | Verify the branch/tag/sha exists on the source repo |
| `install.sh` says "node is not on PATH" | Node not installed | Install Node ≥ 20 from <https://nodejs.org> |
| `install.sh` says "Node X is too old" | Node < 20 | Upgrade Node; `nvm install 20` if using nvm |
| `install.sh` says "Bundled MCP binary missing" | Copied only part of the folder | Re-copy the whole `.agents/skills/xerant/` tree, including `bin/` |
| OpenCode doesn't list the skill | OpenCode not restarted after install | Quit and relaunch OpenCode |
| `xerant_health` → network error | internal-server not running or wrong URL | `curl $XERANT_API_URL/health`; adjust `XERANT_API_URL` |
| `xerant_docker_health` → unhealthy | Docker daemon on the server host is down | Start Docker; if on Mac with Docker Desktop, ensure the whale is green |
| Skill halts "remote Dockerfile differs" | Local Dockerfile hasn't been pushed to the target branch | `git push origin <branch>` then retry, or accept the remote version |
| Security gate: ARG→ENV leak | `ARG X` + `ENV X=${X}` pattern | Switch to BuildKit: `RUN --mount=type=secret,id=X …` |
| Security gate: secret scan hit | Literal credential in your repo/Dockerfile | Move it to runtime env or BuildKit secret; add the path to `.dockerignore` |
| Compose hard fail: bind-mount | You're mounting `docker.sock` or similar | Use a named volume, or pass `--force` if truly required (flagged in report) |

---

## Contents of this folder

```
xerant/
├── README.md                  # this file (human-facing)
├── SKILL.md                   # agent-facing spec (frontmatter + workflow)
├── install-remote.sh          # curl | sh entry point (fetches tree from GitHub)
├── install.sh                 # local installer (merges opencode.json)
├── bin/
│   └── xerant-mcp.mjs         # pre-bundled MCP server (~720KB, Node >= 20, 22 tools)
├── scripts/
│   ├── check-dockerfile.sh    # security-gate runner (Dockerfile + compose)
│   ├── scan-secrets.sh        # secret-pattern scanner
│   └── deploy.sh              # legacy CLI fallback when MCP unavailable
└── templates/
    ├── Dockerfile.nextjs      # Next.js standalone multi-stage
    ├── Dockerfile.node        # generic Node multi-stage
    ├── Dockerfile.generic     # language-agnostic starter
    ├── compose.yml            # single-service compose starter for the MVP flow
    └── .dockerignore          # secure defaults
```

---

## Updating the bundled MCP server

The source lives in `mcp-server/` at the repo root (not inside this folder). After editing, re-bundle:

```bash
cd mcp-server
npm install        # once
npm run bundle     # writes .agents/skills/xerant/bin/xerant-mcp.mjs
```

Commit the resulting `bin/xerant-mcp.mjs` with your source change.

---

## Security posture

- `XERANT_API_KEY` is never written to disk, echoed, or passed on argv. The MCP process reads it from env at startup and forwards it only as an HTTP `Authorization` header.
- `install.sh` takes a timestamped backup of `opencode.json` before editing.
- The bundled MCP is an ESM file, shebang-prefixed, no postinstall scripts. Inspect it before trusting with: `head -20 bin/xerant-mcp.mjs`.
- All security gates run locally on the consumer's machine before any network call to the internal-server.

---

## For maintainers

### `xerant.cloud/install` redirect

For the one-liner `curl -fsSL https://xerant.cloud/install | sh` to work, the marketing site must redirect `/install` to this repo's `install-remote.sh`. The site is Next.js — add this to `xerant/next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/install",
        destination:
          "https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
```

Deploy the site and the one-liner starts working. Until then, use the `raw.githubusercontent.com` URL directly.

For Vercel-hosted deploys without touching `next.config.ts`, a `xerant/vercel.json` also works:

```json
{
  "redirects": [
    {
      "source": "/install",
      "destination": "https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh",
      "permanent": false
    }
  ]
}
```

### Planned: npm packages (`@xerant/*`)

Long-term the install flow should move to npm so users get `npx -y @xerant/cli install` with autoupdate and signed artifacts. Two packages to publish, once the `@xerant` npm org is created:

| Package | Source | Purpose |
|---|---|---|
| `@xerant/mcp-server` | `mcp-server/` | Spawned by OpenCode as `npx -y @xerant/mcp-server` |
| `@xerant/cli` | new `cli/` dir | `npx -y @xerant/cli install` — copies skill, writes opencode.json, points at the npm MCP package |

Once those are live, the installer swaps:

```json
"command": ["node", "./.agents/skills/xerant/bin/xerant-mcp.mjs"]
```

to:

```json
"command": ["npx", "-y", "@xerant/mcp-server@latest"]
```

…and the committed `bin/xerant-mcp.mjs` becomes redundant (though we keep it for offline installs).

## Related docs

- **`SKILL.md`** (this folder) — the workflow spec OpenCode reads.
- **`install.sh`** — local installer (called by `install-remote.sh` after it fetches the tree).
- **`install-remote.sh`** — the `curl | sh` entry point that fetches the skill from GitHub.
- **`QUICKSTART.md`** (repo root, if you have the full buildathon checkout) — end-to-end: start internal-server → build MCP → restart OpenCode.
- **`mcp-server/README.md`** — MCP server source, dev workflow, and how its tools map to REST endpoints.
- **`internal-server/AGENTS.md`** — API surface + contract the skill relies on.

---

Questions / issues: open one against `sanchaymittal/buildathon`.
