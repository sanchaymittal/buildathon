# Forge — Staff Engineer

> *"Keep changes minimal and well-documented."*

Forge is the only agent that writes code. It reads the repo, applies a
minimal diff, runs tests, and pushes the branch — all inside a sandbox
scoped to `TeamContext.project_path`.

**Source:** `src/agent/team/forge.py`

## Role in the pipeline

Invoked by Axiom via `handoff_to_forge(task_spec)`. On return Axiom
expects:

- A final commit sha recorded on `TeamContext.commit_sha`.
- A branch name recorded on `TeamContext.branch`.
- Tests run and a pass/fail result in the summary.

## System prompt (summary)

Full text in `FORGE_SYSTEM_PROMPT` (`forge.py:18`). Hard rules:

- Never touch paths outside the project root.
- Never run destructive shell commands (the whitelist in
  `src/tooling/shell.py` enforces this).
- Minimal, well-documented diffs.

Suggested workflow:

1. `read_file` / `list_files` to orient.
2. `apply_patch` (preferred) or `write_file`.
3. `run_pytest`.
4. `create_branch` → `commit_all` → `push_branch`.
5. `record_commit` with the final sha.

## Tools

| Tool             | Signature                                                     | Backed by                         |
| ---------------- | ------------------------------------------------------------- | --------------------------------- |
| `read_file`      | `(path: str, max_bytes: int = 200_000) -> dict`               | `tooling/fs.py::read_file`         |
| `write_file`     | `(path: str, content: str) -> dict`                           | `tooling/fs.py::write_file`        |
| `list_files`     | `(directory: str = ".") -> dict`                              | `tooling/fs.py::list_files`        |
| `apply_patch`    | `(unified_diff: str) -> dict`                                 | `tooling/fs.py::apply_patch` (`git apply`) |
| `run_shell`      | `(command: str, timeout_s: int = 120) -> dict`                | `tooling/shell.py::run_shell` (whitelisted) |
| `run_pytest`     | `(pattern: str \| None) -> dict`                              | `tooling/testing.py::run_pytest`   |
| `create_branch`  | `(name: str) -> dict`                                         | `tooling/git_tools.py::create_branch` |
| `commit_all`     | `(message: str) -> dict`                                      | `tooling/git_tools.py::commit_all` |
| `push_branch`    | `(branch: str \| None, remote: str = "origin") -> dict`       | `tooling/git_tools.py::push_branch` (no-op if no remote) |
| `record_commit`  | `(sha: str, branch: str \| None) -> dict`                     | Writes to `TeamContext`             |

## State it mutates

| Field             | Via                              |
| ----------------- | -------------------------------- |
| `branch`          | `create_branch`, `record_commit` |
| `commit_sha`      | `commit_all`, `record_commit`    |
| `status`          | `record_commit` flips `planning → engineering` |
| `notes`           | via `status` transition          |

## Sandbox & safety

- **Filesystem writes** are clamped to `project_path` by `tooling/fs.py`.
  Attempts to escape via `..` or absolute paths raise immediately.
- **Shell commands** go through a whitelist:
  `git`, `pytest`, `python`, `docker compose …`, `ls`, `cat`, `echo`.
  Anything else returns `{"ok": false, "error": ...}`.
- **No remote push required.** `push_branch` returns a no-op dict when
  the repo has no `origin` remote — keeps hackathon demos on a laptop
  clean.

## Failure modes

- **Patch doesn't apply.** `apply_patch` returns `{"ok": false, ...}`
  with `git apply`'s stderr. Forge should retry with `write_file`.
- **Tests fail.** `run_pytest` returns `returncode != 0`; Forge should
  iterate before calling `commit_all`.
- **Disallowed shell command.** `ShellNotAllowedError` is caught and
  surfaced as `{"ok": false, "error": ...}` — the run continues.

## Configuration

- **Model.** Inherits from `CredentialManager.get_gemini_credentials().model`
  via `build_team(peer_model=...)`.
- **Tool-call budget.** 24 by default when spun up through `handoff_tool`
  (one handoff counts as one of Axiom's tool calls).
