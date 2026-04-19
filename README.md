# Xerant

Ship any project with one prompt. Xerant gives coding agents (OpenCode, Claude Code, and any MCP-aware client) the tools to do the full DevOps loop end-to-end — security-audit your Dockerfile, build your image, run it on the internal platform, stream logs, roll back — all from a single `/xerant --prod` inside the agent.

[![npm](https://img.shields.io/npm/v/xerant-mcp-server.svg?label=xerant-mcp-server)](https://www.npmjs.com/package/xerant-mcp-server)
[![release](https://img.shields.io/github/v/release/sanchaymittal/buildathon.svg)](https://github.com/sanchaymittal/buildathon/releases/latest)
[![license](https://img.shields.io/github/license/sanchaymittal/buildathon.svg)](LICENSE)

```
Coding agent  ── stdio ──▶  xerant-mcp-server  ── HTTP ──▶  internal-server  ──▶  Docker
```

---

## Install (one line)

From the root of the project you want to deploy:

```bash
curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh | bash
```

Then in your agent:

```
/xerant --prod
```

That's it. The installer drops a portable `xerant` skill into `.agents/skills/xerant/`, wires your `opencode.json`, and self-tests 22 MCP tools. Works in any project. Supports Docker Compose and GitHub-based deploys.

### Install options

| What | How |
|---|---|
| **One-liner, tracks `main`** | `curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh \| bash` |
| **Pinned to v0.1.0 release** | `curl -fsSL https://github.com/sanchaymittal/buildathon/releases/download/v0.1.0/xerant-skill-v0.1.0.tar.gz \| tar -xz && bash .agents/skills/xerant/install.sh` |
| **MCP only, no skill files** | Add `"command": ["npx","-y","xerant-mcp-server@latest"]` to your `opencode.json` |
| **Vanity URL** *(pending)* | `curl -fsSL https://xerant.cloud/install \| sh` |
| **Offline / air-gapped** | `cp -r` the skill folder and run `bash install.sh` |

Full install options, env vars, and troubleshooting: **[`.agents/skills/xerant/README.md`](.agents/skills/xerant/README.md)**.

---

## What you get

After install, your coding agent can:

- **Deploy**: `/xerant --prod` triggers an end-to-end pipeline. Auto-picks between two flows:
  - **Compose (MVP, default)** — runs `docker compose up -d` against your local project directory on the Xerant host.
  - **Legacy GitHub** — clones + builds from your repo's branch, runs a single container.
- **Audit**: every deploy is gated by a local security pass:
  - `.dockerignore` coverage, `ARG`→`ENV` leak detection, secret-pattern scan (AWS, GitHub, Slack, Google, OpenAI, private keys, heuristic assignments with placeholder awareness).
  - Compose-specific: sensitive bind-mount rejection (`docker.sock`, `/root`, `/etc`, `~/.ssh`, `~/.aws`, `~/.docker`, `~/.gnupg`), `privileged: true` rejection, low-port warnings, `env_file` warnings.
  - Optional `hadolint`.
- **Inspect + operate**: tail logs, restart, redeploy, stop, or remove containers directly via 22 MCP tools — no custom CLI.

Tool catalog: `xerant_health`, `xerant_docker_health`, `xerant_compose_ping`, `xerant_compose_up/_down/_status/_logs`, `xerant_deploy`, `xerant_list_deployments`, `xerant_get_deployment`, `xerant_deployment_logs`, `xerant_stop_/_start_/_restart_deployment`, `xerant_redeploy`, `xerant_remove_deployment`, `xerant_list_containers`, `xerant_get_container`, `xerant_container_logs`, `xerant_github_get_repo`, `xerant_github_list_branches`, `xerant_github_get_file`.

---

## Repo map

```
buildathon/
├── .agents/skills/xerant/    ← the drop-in skill (workflow + installer + bundled MCP)
│   └── README.md                 ← user-facing install + usage docs
├── mcp-server/               ← TypeScript MCP bridge, published as xerant-mcp-server on npm
│   └── README.md                 ← MCP server docs + dev guide
├── internal-server/          ← FastAPI DevOps API (the thing that runs Docker)
│   └── AGENTS.md                 ← contract + endpoints
├── cli/                      ← [WIP] xerant-cli npm package for npx-based install
├── xerant/                   ← Next.js marketing site (xerant.cloud)
├── examples/                 ← framework deploy test results
├── QUICKSTART.md             ← full-stack local dev guide (run everything end-to-end)
└── README.md                 ← you are here
```

Each subproject has its own README. Start there if you're working on that layer.

---

## Requirements

| Layer | Need |
|---|---|
| Your project (consumer) | **Node.js ≥ 20** to run the bundled MCP or `npx xerant-mcp-server`. No Docker, no Python. |
| Xerant host (operator) | **Docker daemon** for containers, **Python 3.11+** for `internal-server`, a GitHub PAT for repo operations. See [`QUICKSTART.md`](QUICKSTART.md). |

---

## Environment

| Var | Default | Purpose |
|---|---|---|
| `XERANT_API_URL` | `http://localhost:8000` | Base URL of the internal-server |
| `XERANT_API_KEY` | *(unset)* | Optional bearer token, forwarded as `Authorization: Bearer`. Never written to disk. Forward-compatible; the server doesn't enforce auth today. |

---

## How it works

1. **Skill** ([`.agents/skills/xerant/`](.agents/skills/xerant/)) — a portable folder of workflow markdown + shell scripts + Dockerfile/compose templates + a pre-bundled MCP binary. OpenCode (or any MCP-aware agent) reads `SKILL.md` and follows the pipeline.
2. **MCP bridge** ([`mcp-server/`](mcp-server/), [npm `xerant-mcp-server`](https://www.npmjs.com/package/xerant-mcp-server)) — TypeScript server over stdio. Exposes 22 tools. Translates agent intents into HTTP calls against the internal server.
3. **Internal server** ([`internal-server/`](internal-server/)) — FastAPI app that talks to Docker on the host. Two deploy surfaces:
   - `/compose/*` — local-path MVP (pass a directory with a `Dockerfile` + `compose.yml`)
   - `/deployments/*` — legacy GitHub clone + build + run

You run (1) and (2) on your workstation. (3) runs wherever the Xerant platform is deployed.

---

## Running everything locally

Full stack (internal-server + MCP + skill) in one repo:

```bash
# 1. Internal server
cd internal-server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_…
python -m src.api.app          # :8000

# 2. MCP bridge (only if editing source; otherwise npx picks up the npm package)
cd ../mcp-server
npm install && npm run bundle  # writes the bundle used by the skill

# 3. Run OpenCode and use the skill
# opencode.json in the repo already wires everything up
```

Detailed walkthrough with docker-compose variant, troubleshooting, and per-flow debug tips: **[`QUICKSTART.md`](QUICKSTART.md)**.

---

## Distribution status

| Artifact | Where | Version | Status |
|---|---|---|---|
| Skill folder | this repo, `.agents/skills/xerant/` | tracks `main` | **live** |
| Release tarball | [GitHub Releases](https://github.com/sanchaymittal/buildathon/releases/latest) | v0.1.0 | **live** |
| MCP server | [npm `xerant-mcp-server`](https://www.npmjs.com/package/xerant-mcp-server) | 0.1.0 | **live** |
| One-liner installer | `curl … install-remote.sh` | tracks `main` | **live** |
| `xerant-cli` npm package | [npm `xerant-cli`](https://www.npmjs.com/package/xerant-cli) | — | **pending** (v0.2) |
| `@xerant/*` npm scope | npm org `xerant` | — | **pending** (org creation) |
| `xerant.cloud/install` vanity URL | Next.js redirect | — | **pending** (redirect config) |

---

## Contributing

1. Fork and branch off `main`.
2. Keep commits scoped (skill / mcp-server / internal-server / cli / xerant[marketing]).
3. Follow the code-style notes in [`internal-server/AGENTS.md`](internal-server/AGENTS.md) for Python work.
4. For TypeScript (mcp-server, cli): keep strict mode on, prefer `zod` for runtime validation, never log secrets.
5. Run the smoke tests before pushing:
   ```bash
   # skill gates
   bash .agents/skills/xerant/scripts/check-dockerfile.sh /path/to/any/project
   # MCP handshake
   cd mcp-server && npm run build && node dist/index.js < /dev/null
   ```

Issues and PRs: <https://github.com/sanchaymittal/buildathon/issues>.

---

## Licenses

- **Code** (skill, mcp-server, internal-server, cli, examples) — MIT.
- **Marketing site** (`xerant/`) — not open-source; proprietary assets, see that folder's own notices.
- **Bundled binary** `.agents/skills/xerant/bin/xerant-mcp.mjs` — generated from `mcp-server/` source; same MIT license.

---

## More docs

- [`.agents/skills/xerant/README.md`](.agents/skills/xerant/README.md) — skill install, usage, troubleshooting (the canonical user doc)
- [`.agents/skills/xerant/SKILL.md`](.agents/skills/xerant/SKILL.md) — the workflow spec the agent reads
- [`mcp-server/README.md`](mcp-server/README.md) — MCP bridge internals and publishing
- [`internal-server/README.md`](internal-server/README.md) + [`internal-server/AGENTS.md`](internal-server/AGENTS.md) — server contract and code-style
- [`QUICKSTART.md`](QUICKSTART.md) — full-stack local dev
- [`BRAND.md`](BRAND.md) — visual identity guidelines
