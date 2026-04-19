# xerant skill

Deploy any project to the Xerant internal DevOps platform from OpenCode, in one invocation.

[![npm](https://img.shields.io/npm/v/xerant-mcp-server.svg?label=xerant-mcp-server)](https://www.npmjs.com/package/xerant-mcp-server)
[![release](https://img.shields.io/github/v/release/sanchaymittal/buildathon.svg)](https://github.com/sanchaymittal/buildathon/releases/latest)

```
OpenCode ── stdio ──▶ xerant-mcp ── HTTP ──▶ internal-server ──▶ Docker
```

This folder is the **entire skill** — workflow spec, installer, pre-built MCP bridge, security scripts, and Dockerfile / compose templates. Fully self-contained (~750 KB including the MCP binary). Drops into any project with one command.

---

## Install

Pick the path that fits. All three land in the same place.

### 1. `curl | bash` from GitHub (recommended — live today)

From the root of the project you want to deploy:

```bash
curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh | bash
```

That's it. The script downloads the skill into `./.agents/skills/xerant/`, wires `./opencode.json`, and self-tests the 22 MCP tools. Restart OpenCode and run:

```
/xerant --prod
```

### 2. Tarball from the GitHub release (pinned, live today)

```bash
curl -fsSL https://github.com/sanchaymittal/buildathon/releases/download/v0.1.0/xerant-skill-v0.1.0.tar.gz | tar -xz
bash .agents/skills/xerant/install.sh
```

Latest release: **[v0.1.0](https://github.com/sanchaymittal/buildathon/releases/latest)**. Use this when you want an immutable install tied to a specific version.

### 3. `xerant.cloud/install` (pending marketing-site redirect)

```bash
curl -fsSL https://xerant.cloud/install | sh
```

Works once the redirect lands on `xerant.cloud`. Until then, use path 1. Maintainer note below on how to wire the redirect.

### 4. MCP only, no skill files (for advanced users)

If you already have a workflow and just want the MCP server wired into OpenCode, skip the skill entirely and add this to your `opencode.json`:

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

npm: [`xerant-mcp-server`](https://www.npmjs.com/package/xerant-mcp-server). Updates every time the package publishes a new version.

### Install options (env vars for the installer)

| Var | Default | Purpose |
|---|---|---|
| `XERANT_REF` | `main` | Branch, tag, or commit SHA to pull the skill from |
| `XERANT_REPO` | `sanchaymittal/buildathon` | Override the source repo (for forks / mirrors) |
| `XERANT_TARGET` | `.agents/skills/xerant` | Destination directory inside your project |
| `XERANT_FORCE` | `0` | Set `1` to overwrite an existing skill dir |

Pin a version:

```bash
curl -fsSL .../install-remote.sh | XERANT_REF=v0.1.0 bash
```

### 5. Offline / air-gapped

The skill folder works without network after install. Copy it in by hand:

```bash
cp -r /path/to/xerant .agents/skills/xerant
bash .agents/skills/xerant/install.sh
```

The bundled `bin/xerant-mcp.mjs` (~720 KB) is used instead of npm.

---

## Requirements

| Requirement | Why |
|---|---|
| **Node.js ≥ 20** | Runs the bundled MCP or the `npx xerant-mcp-server` process. Installer enforces this. |
| **A reachable internal-server** | The MCP bridge forwards calls to the FastAPI service. Default `http://localhost:8000`. Override with `XERANT_API_URL`. |
| **Docker daemon** (on the internal-server host) | Only the internal-server talks to Docker. The skill itself doesn't. |

No Python, Docker, or build tools required on the consumer side.

---

## Configuration

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

If you'd rather use the npm-published server than the committed bundle, swap `command` to `["npx", "-y", "xerant-mcp-server@latest"]`. Both work identically.

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
xerant --path .          # implicitly --dev unless env flag given
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
- No literal secrets in Dockerfile or repo (AWS / GitHub / Slack / Google / OpenAI keys, private-key headers, heuristic `SECRET=` / `PASSWORD=` assignments). Placeholders like `EXAMPLE`, `changeme`, `<your-key>`, `${VAR}` are ignored.
- `hadolint` if installed (advisory).

Compose-specific (when a compose file is present):

- **Hard fail** on sensitive host bind-mounts (`docker.sock`, `/root`, `/etc`, `~/.ssh`, `~/.aws`, `~/.docker`, `~/.gnupg`).
- **Hard fail** on `privileged: true`.
- **Warn** on host port ≤ 1024 bindings.
- **Warn** on `env_file` referencing `.env` variants (usually git-ignored, must exist on host).

A hard finding stops the pipeline with the exact offending line and a fix suggestion. Bypassing requires explicit `--force`, which gets logged in the final report.

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

Invoke directly in a prompt without rerunning the skill:

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
| `curl https://xerant.cloud/install` → 404 | Marketing site redirect not deployed yet | Use the raw GitHub URL (path 1) or the release tarball (path 2) |
| `install-remote.sh` says "Destination already exists" | Previous install present | Re-run with `XERANT_FORCE=1` |
| Extract failed ("repo may not contain") | Bad `XERANT_REF` | Verify the branch / tag / SHA exists on the source repo |
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
│   └── xerant-mcp.mjs         # pre-bundled MCP server (~720 kB, Node >= 20, 22 tools)
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

Commit the resulting `bin/xerant-mcp.mjs` along with your source change.

To publish a new version of `xerant-mcp-server` to npm:

```bash
cd mcp-server
npm version patch           # or minor / major
npm publish                 # will prompt for 2FA OTP
```

---

## Distribution status

| Artifact | Where | Version | Status |
|---|---|---|---|
| Skill folder | this repo, `.agents/skills/xerant/` | tracks `main` | **live** |
| Release tarball | [GitHub Releases](https://github.com/sanchaymittal/buildathon/releases/latest) | v0.1.0 | **live** |
| MCP server | [npm `xerant-mcp-server`](https://www.npmjs.com/package/xerant-mcp-server) | 0.1.0 | **live** |
| One-liner installer | `curl … install-remote.sh` | tracks `main` | **live** |
| `xerant-cli` npm package | [npm `xerant-cli`](https://www.npmjs.com/package/xerant-cli) | — | **pending** (v0.2) |
| `@xerant/*` npm scope | npm org `xerant` | — | **pending** (needs org creation) |
| `xerant.cloud/install` vanity URL | Next.js redirect | — | **pending** (see below) |

---

## For maintainers

### `xerant.cloud/install` redirect

For the one-liner `curl -fsSL https://xerant.cloud/install | sh` to work, the marketing site (`xerant/` at the repo root) must redirect `/install` to this repo's `install-remote.sh`. Add this to `xerant/next.config.ts`:

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

Deploy the site and the one-liner starts working. A `xerant/vercel.json` alternative also works if you host there:

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

### Moving to the `@xerant` npm scope

The server is currently published as unscoped `xerant-mcp-server` because the `@xerant` org didn't exist at publish time. When ready to migrate:

1. Create the org at <https://www.npmjs.com/org/create> (free tier for public packages, ~30 seconds via web UI — not available via npm CLI).
2. `cd mcp-server && npm pkg set name=@xerant/mcp-server && npm version minor && npm publish`.
3. Update the skill's `install.sh`, `install-remote.sh`, this README, and the top-level `opencode.json` to prefer `@xerant/mcp-server`.
4. Deprecate the unscoped name with a pointer:
   ```bash
   npm deprecate xerant-mcp-server "Renamed to @xerant/mcp-server"
   ```

### Planned `xerant-cli` package

Target one-liner: `npx -y xerant-cli install`. The package will ship a compiled install command that embeds this skill's assets and writes `opencode.json` with the `npx -y xerant-mcp-server@latest` MCP command. Scaffold lives at `cli/` in this repo (work in progress). Once shipped, this section gets replaced with the `npx` one-liner at the top of the README.

### Cutting a release

```bash
# 1. Make sure mcp-server is re-bundled so bin/xerant-mcp.mjs is up to date
cd mcp-server && npm run bundle && cd ..

# 2. Build the skill tarball
tar -czf /tmp/xerant-skill-vX.Y.Z.tar.gz -C . .agents/skills/xerant

# 3. Tag + push + create release
git tag -a vX.Y.Z -m "xerant vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z /tmp/xerant-skill-vX.Y.Z.tar.gz \
  --title "vX.Y.Z — <description>" \
  --notes "<release notes>"

# 4. Bump the npm package version if mcp-server source changed
cd mcp-server && npm version patch && npm publish
```

---

## Related docs

- **`SKILL.md`** (this folder) — the workflow spec OpenCode reads.
- **`install.sh`** — local installer (called by `install-remote.sh` after it fetches the tree).
- **`install-remote.sh`** — the `curl | sh` entry point that fetches the skill from GitHub.
- **`QUICKSTART.md`** (repo root, if you have the full buildathon checkout) — end-to-end: start internal-server → build MCP → restart OpenCode.
- **`mcp-server/README.md`** — MCP server source, dev workflow, and how its tools map to REST endpoints.
- **`internal-server/AGENTS.md`** — API surface + contract the skill relies on.

---

Questions / issues: [open one on GitHub](https://github.com/sanchaymittal/buildathon/issues).
