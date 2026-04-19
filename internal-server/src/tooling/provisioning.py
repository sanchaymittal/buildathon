"""Project provisioning helpers.

Given an arbitrary local repository, detect what stack it looks like and
render deterministic Dockerfile + compose.yml scaffolds so the rest of
the Agentic DevOps pipeline (Vector's build/rollout, Sentry's health
watch) can operate on it.

All functions here are pure (no LLM, no Docker daemon) so they are
trivial to unit test.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import fs as fs_tools

logger = logging.getLogger(__name__)


_TEMPLATES_DIR = Path(__file__).parent / "templates"

_COMPOSE_FILENAMES = (
    "compose.yml",
    "compose.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
)

# Keep explicit so stack detection is fully documented. Order matters:
# the first matching sentinel wins for the `detected_stack` field.
_STACK_SENTINELS: List[tuple[str, tuple[str, ...]]] = [
    ("python", ("pyproject.toml", "requirements.txt", "Pipfile", "poetry.lock")),
    ("node", ("package.json",)),
    ("static", ("index.html",)),
]

_DEFAULT_PORT_BY_STACK: Dict[str, int] = {
    "python": 8000,
    "node": 3000,
    "static": 80,
}


class UnknownStackError(RuntimeError):
    """Raised when `render_dockerfile` is asked for a stack it can't handle."""


@dataclass
class ProjectInventory:
    """Summary of a project's deploy-relevant shape.

    Fields:
      has_dockerfile: whether a top-level ``Dockerfile`` exists.
      has_compose: whether any recognised compose filename exists.
      compose_filename: the concrete compose filename if present, else None.
      detected_stack: one of ``python|node|static|unknown``.
      package_files: the sentinel files that drove detection (relative names).
      entrypoint: best-guess entrypoint (e.g. ``app.py``, ``server.js``).
      hinted_port: port extracted from code/config, else a per-stack default.
      has_env_file: whether a ``.env`` file exists at the project root.
    """

    has_dockerfile: bool
    has_compose: bool
    compose_filename: Optional[str]
    detected_stack: str
    package_files: List[str] = field(default_factory=list)
    entrypoint: Optional[str] = None
    hinted_port: int = 8000
    has_env_file: bool = False

    def to_dict(self) -> dict:
        return {
            "has_dockerfile": self.has_dockerfile,
            "has_compose": self.has_compose,
            "compose_filename": self.compose_filename,
            "detected_stack": self.detected_stack,
            "package_files": list(self.package_files),
            "entrypoint": self.entrypoint,
            "hinted_port": self.hinted_port,
            "has_env_file": self.has_env_file,
        }


# ---------------------------------------------------------------- inspection
def inspect_project(root: str) -> ProjectInventory:
    """Inspect ``root`` and return a :class:`ProjectInventory`."""
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise FileNotFoundError(f"Project root not a directory: {root_path}")

    dockerfile = root_path / "Dockerfile"
    has_dockerfile = dockerfile.exists() and dockerfile.is_file()

    compose_filename: Optional[str] = None
    for name in _COMPOSE_FILENAMES:
        if (root_path / name).exists():
            compose_filename = name
            break
    has_compose = compose_filename is not None

    detected_stack = "unknown"
    package_files: List[str] = []
    for stack_name, sentinels in _STACK_SENTINELS:
        hits = [s for s in sentinels if (root_path / s).exists()]
        if hits:
            detected_stack = stack_name
            package_files = hits
            break

    entrypoint = _guess_entrypoint(root_path, detected_stack)
    hinted_port = _guess_port(root_path, detected_stack)
    has_env_file = (root_path / ".env").exists()

    return ProjectInventory(
        has_dockerfile=has_dockerfile,
        has_compose=has_compose,
        compose_filename=compose_filename,
        detected_stack=detected_stack,
        package_files=package_files,
        entrypoint=entrypoint,
        hinted_port=hinted_port,
        has_env_file=has_env_file,
    )


def _guess_entrypoint(root: Path, stack: str) -> Optional[str]:
    if stack == "python":
        for candidate in ("app.py", "main.py", "server.py", "wsgi.py", "asgi.py"):
            if (root / candidate).exists():
                return candidate
        return None
    if stack == "node":
        pkg = root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                main = data.get("main")
                if isinstance(main, str) and main.strip():
                    return main.strip()
                scripts = data.get("scripts") or {}
                if "start" in scripts:
                    return "package.json#start"
            except (OSError, json.JSONDecodeError):
                logger.debug("Could not parse package.json at %s", pkg)
        for candidate in ("index.js", "server.js", "app.js"):
            if (root / candidate).exists():
                return candidate
        return None
    if stack == "static":
        return "index.html" if (root / "index.html").exists() else None
    return None


def _guess_port(root: Path, stack: str) -> int:
    default = _DEFAULT_PORT_BY_STACK.get(stack, 8000)
    # Very light-touch heuristic: look for PORT=nnnn in a .env file.
    env_file = root / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("PORT=") or line.startswith("APP_PORT="):
                    _, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    if value.isdigit():
                        return int(value)
        except OSError:
            pass
    return default


# ----------------------------------------------------------------- rendering
def _template(name: str) -> str:
    path = _TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {name}")
    return path.read_text(encoding="utf-8")


def render_dockerfile(stack: str, inventory: ProjectInventory) -> str:
    """Render a Dockerfile for ``stack`` using details from ``inventory``."""
    stack = (stack or "").lower()
    if stack == "python":
        return _render_python_dockerfile(inventory)
    if stack == "node":
        return _render_node_dockerfile(inventory)
    if stack == "static":
        return _render_static_dockerfile(inventory)
    raise UnknownStackError(
        f"Cannot render Dockerfile for stack={stack!r}. "
        "Supported stacks: python, node, static."
    )


def _render_python_dockerfile(inventory: ProjectInventory) -> str:
    # Prefer pyproject.toml if present, else requirements.txt.
    dep_file = "requirements.txt"
    install_cmd = "pip install --no-cache-dir -r requirements.txt"
    if "pyproject.toml" in inventory.package_files:
        dep_file = "pyproject.toml"
        install_cmd = "pip install --no-cache-dir ."
    elif "requirements.txt" not in inventory.package_files:
        # No dependency file detected; emit a no-op install line that won't
        # explode even on an empty repo.
        dep_file = "."
        install_cmd = "echo 'no dependency manifest detected; skipping install'"

    entry = inventory.entrypoint or "app.py"
    cmd = f'["python", "{entry}"]'
    port = inventory.hinted_port or _DEFAULT_PORT_BY_STACK["python"]

    tmpl = _template("dockerfile.python.tmpl")
    return tmpl.format(
        dependency_file=dep_file,
        install_cmd=install_cmd,
        port=port,
        cmd=cmd,
    )


def _render_node_dockerfile(inventory: ProjectInventory) -> str:
    install_cmd = "npm ci --omit=dev || npm install --omit=dev"
    entry = inventory.entrypoint
    if entry == "package.json#start" or not entry:
        cmd = '["npm", "start"]'
    else:
        cmd = f'["node", "{entry}"]'
    port = inventory.hinted_port or _DEFAULT_PORT_BY_STACK["node"]
    tmpl = _template("dockerfile.node.tmpl")
    return tmpl.format(install_cmd=install_cmd, port=port, cmd=cmd)


def _render_static_dockerfile(inventory: ProjectInventory) -> str:
    port = inventory.hinted_port or _DEFAULT_PORT_BY_STACK["static"]
    tmpl = _template("dockerfile.static.tmpl")
    return tmpl.format(port=port)


def render_compose(
    service_name: str,
    port: int,
    has_env_file: bool,
) -> str:
    """Render a single-service compose.yml."""
    if not service_name or not service_name.strip():
        raise ValueError("service_name must be non-empty")
    env_file_block = "\n    env_file:\n      - .env" if has_env_file else ""
    tmpl = _template("compose.single.tmpl")
    return tmpl.format(
        service_name=service_name.strip(),
        port=port,
        env_file_block=env_file_block,
    )


# ------------------------------------------------------------------ writing
def write_scaffold(
    root: str,
    files: Dict[str, str],
    overwrite: bool = False,
) -> Dict[str, str]:
    """Write scaffold files under ``root``.

    Returns a mapping ``{path: action}`` where action is ``'written'`` or
    ``'skipped_exists'``. Uses the sandboxed :func:`tooling.fs.write_file`
    so callers can't escape the project root.
    """
    results: Dict[str, str] = {}
    root_path = Path(root).expanduser().resolve()
    for rel_path, content in files.items():
        target = (root_path / rel_path).resolve()
        if target.exists() and not overwrite:
            results[rel_path] = "skipped_exists"
            continue
        fs_tools.write_file(str(root_path), rel_path, content)
        results[rel_path] = "written"
    return results


def default_service_name(root: str) -> str:
    """Derive a safe compose service name from a project directory name."""
    base = Path(root).expanduser().resolve().name.lower()
    base = base.replace(" ", "-")
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in base)
    safe = safe.strip("-") or "app"
    return safe
