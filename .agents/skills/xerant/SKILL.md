---
name: xerant
description: >
  DevOps workflow that deploys a GitHub repository to the Xerant internal platform.
  Verifies a production-ready Dockerfile locally AND in the target branch on GitHub,
  runs a security audit (secret scan, .dockerignore, no ARG→ENV leaks, optional
  hadolint), then calls the `xerant_deploy` MCP tool (served by
  `@xerant/mcp-server`, which forwards to the internal DevOps API).
  Supported environments: prod, staging, preview, dev.
  Trigger when the user says "xerant", "xerant --prod|--staging|--preview|--dev",
  "deploy to xerant", or invokes /xerant.
---

# xerant — Deploy to the Xerant Platform

End-to-end deploy pipeline: **resolve target → Dockerfile parity check → security audit → MCP deploy → report**.

Architecture:

```
OpenCode ── stdio ──▶ xerant-mcp (TS) ── HTTP ──▶ internal-server (FastAPI) ──▶ Docker
```

## Invocation

Trigger on any of:
- `/xerant`
- `xerant`                 — ask for environment
- `xerant --prod | --staging | --preview | --dev`
- `deploy to xerant …`

If no environment flag is given, ask the user which one.

## Required environment

- `XERANT_API_KEY` *(optional for now)* — forwarded as `Authorization: Bearer …` by the MCP bridge. The server currently ignores it; kept for forward compatibility. Never log, echo, write to disk, or commit.
- `XERANT_API_URL` *(optional)* — defaults to `http://localhost:8000`.
- The internal server itself needs `GITHUB_TOKEN` server-side; the skill doesn't touch that.

If the user hasn't set `XERANT_API_KEY`, proceed without prompting (server-side auth is off). Call this out in the final report so the user knows.

## Required MCP tools

The skill expects these tools from `xerant-mcp` to be registered:

| Tool | Purpose |
|------|---------|
| `xerant_health` | pre-flight |
| `xerant_docker_health` | pre-flight |
| `xerant_deploy` | main deploy action |
| `xerant_github_get_file` | fetch remote Dockerfile for parity diff |
| `xerant_github_list_branches` | verify branch exists |
| `xerant_list_deployments` / `xerant_get_deployment` / `xerant_deployment_logs` | post-deploy inspection |

If any required tool is missing, stop and tell the user to register `xerant-mcp` in `opencode.json` (see `mcp-server/README.md`).

## Workflow

Run sequentially. **Halt on first failure.**

### Step 1 — Resolve target

Parse the flag and map to canonical tier:

| Flag | Canonical |
|------|-----------|
| `--prod` | `production` |
| `--staging` | `staging` |
| `--preview` | `preview` |
| `--dev` | `development` |

Then gather:
- `repository` — infer from `git remote get-url origin`, strip trailing `.git`, convert to `owner/repo`. Confirm with user if ambiguous.
- `branch` — default to `git rev-parse --abbrev-ref HEAD`. If that's `HEAD` (detached) or uncommitted, ask.
- `container_port` — default `80`. Ask if the app listens on a different port.

### Step 2 — Pre-flight the platform

1. Call `xerant_health`. Expect `{"status":"healthy"}`.
2. Call `xerant_docker_health`. If the Docker daemon is down, stop and show the message — the deploy will fail without it.

### Step 3 — Ensure local Dockerfile exists

1. If `./Dockerfile` missing, detect project type:
   - `package.json` with `"next"` dep → `templates/Dockerfile.nextjs`
   - `package.json` without Next → `templates/Dockerfile.node`
   - `requirements.txt` / `pyproject.toml` → propose a Python template (not bundled; draft inline)
   - else → `templates/Dockerfile.generic` (marked TODO for the user)
2. Show the proposed Dockerfile as a diff. Ask for confirmation before writing.
3. If `./.dockerignore` missing, copy `templates/.dockerignore`. If present, verify it covers: `.env`, `.git`, `node_modules`, `*.pem`, `*.key`, `id_rsa`. Propose additions if any are missing.

### Step 4 — Remote Dockerfile parity

Critical: **the internal server builds from GitHub, not the local checkout.** So the Dockerfile that matters is the one committed on the target branch.

1. Call `xerant_github_get_file` with `{owner, repo, path: "Dockerfile", ref: branch}`.
2. Compare `decoded_content` against the local file:
   - **Identical** → proceed.
   - **Remote missing** → tell the user they must commit and push the Dockerfile to `<branch>` before this deploy can work. Stop.
   - **Remote differs** → show a concise diff; ask whether to push local or to deploy what's on the remote. Stop and wait for a decision.

If the git working tree is dirty (`git status --porcelain` non-empty) and includes `Dockerfile`, warn explicitly: "Local Dockerfile is uncommitted; the server will use the committed version."

### Step 5 — Security gates

Run `scripts/check-dockerfile.sh` from the skill directory. It performs:

1. **`.dockerignore` coverage** — required entries present.
2. **ARG → ENV leak check** — flags `ARG X` + `ENV X=${X}`.
3. **Secret scan** — via `scripts/scan-secrets.sh`. Patterns: AWS access keys (`AKIA…`/`ASIA…`), GitHub PATs (`ghp_…`, `github_pat_…`), Slack tokens, Google API keys, OpenAI-style, private-key headers, and heuristic `API_KEY=/SECRET=/TOKEN=/PASSWORD=` assignments with literal (non-placeholder) values.
4. **hadolint** — optional; run if `hadolint` is on `PATH`.

Any hard finding → stop. Print findings verbatim and propose fixes. Do **not** bypass without an explicit user `--force` override, which must be logged in the final report.

### Step 6 — Deploy via MCP

Call the `xerant_deploy` tool with:

```json
{
  "repository": "<owner/repo>",
  "branch": "<branch>",
  "environment": "<prod|staging|preview|dev>",
  "container_port": <port>,
  "env": { /* any user-provided runtime env vars */ },
  "build_args": { /* any user-provided build args */ }
}
```

The MCP bridge injects `DEPLOY_ENV=<canonical>` into the env dict and derives `name = <repo>-<canonical>` unless the user supplied a `name`.

The server response shape (`Deployment` model):
- `id`, `status`, `url`, `container_id`, `container_name`, `host_port`, `container_port`, `image`, `created_at`, `logs_tail`, `env`, `labels`.

### Step 7 — Verify

1. Immediately call `xerant_get_deployment` with the returned `id`. Report `status` (`building|running|stopped|failed`).
2. If `status == "failed"`, pull `xerant_deployment_logs` with `tail=200` and show them.
3. If `status == "running"`, print the `url` and commit SHA (`git rev-parse --short HEAD`).

### Step 8 — Report

Print a compact summary:

```
Deployment        <id>
Repository        <owner/repo>@<branch> (commit <sha>)
Environment       <canonical>
Image             <image tag>
Container         <name> (id <short>)
URL               <url>
Status            <status>
Auth              XERANT_API_KEY [set|unset]
```

On any failure, print:
- The failing step
- The underlying error (exit code or API error body)
- Suggested next step (e.g. "push Dockerfile to main", "check Docker daemon")

## Boundaries

- **Never** echo `XERANT_API_KEY`.
- **Never** skip a failed security gate without an explicit `--force` that gets logged.
- **Never** modify local files (Dockerfile, .dockerignore) without showing the change first.
- **Never** call `xerant_remove_deployment` or any destructive tool unprompted.
- Don't combine with the `caveman` skill — deploy output must stay readable.

## Files in this skill

```
.agents/skills/xerant/
├── SKILL.md                   # this file
├── scripts/
│   ├── check-dockerfile.sh    # security gate runner
│   ├── scan-secrets.sh        # secret-pattern scanner
│   └── deploy.sh              # legacy CLI fallback (only used if MCP unavailable)
└── templates/
    ├── Dockerfile.nextjs
    ├── Dockerfile.node
    ├── Dockerfile.generic
    └── .dockerignore
```

## MCP tool catalog (for reference)

Full tool list exposed by `xerant-mcp`:

- `xerant_health`, `xerant_docker_health`
- `xerant_deploy`, `xerant_list_deployments`, `xerant_get_deployment`, `xerant_deployment_logs`
- `xerant_stop_deployment`, `xerant_start_deployment`, `xerant_restart_deployment`, `xerant_redeploy`, `xerant_remove_deployment`
- `xerant_list_containers`, `xerant_get_container`, `xerant_container_logs`
- `xerant_github_get_repo`, `xerant_github_list_branches`, `xerant_github_get_file`

Use these for follow-up operations (tail logs, restart, redeploy, etc.) — they do not require re-running the skill.
