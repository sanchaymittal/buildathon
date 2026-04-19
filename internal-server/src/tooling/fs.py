"""File-system helpers scoped to a project root.

All paths are resolved against a ``project_path`` (e.g.
``TeamContext.project_path``) and must remain inside that root. Anything
that tries to escape raises :class:`FileSystemSandboxError`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class FileSystemSandboxError(RuntimeError):
    """Raised when a file operation would escape the project sandbox."""


def _resolve_within(root: str, rel_path: str) -> Path:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileSystemSandboxError(f"Project root does not exist: {root_path}")
    if not root_path.is_dir():
        raise FileSystemSandboxError(f"Project root is not a directory: {root_path}")

    candidate = (root_path / rel_path).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise FileSystemSandboxError(
            f"Path '{rel_path}' escapes project root '{root_path}'"
        ) from exc
    return candidate


def read_file(root: str, rel_path: str, max_bytes: int = 200_000) -> str:
    """Read a file, capped at ``max_bytes`` to protect the agent context."""
    path = _resolve_within(root, rel_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {rel_path}")
    if not path.is_file():
        raise FileSystemSandboxError(f"Path is not a regular file: {rel_path}")
    data = path.read_bytes()
    truncated = False
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True
    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += f"\n... (truncated at {max_bytes} bytes)"
    return text


def write_file(root: str, rel_path: str, content: str) -> dict:
    """Create or overwrite a file within the project root."""
    path = _resolve_within(root, rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {
        "path": str(path.relative_to(Path(root).resolve())),
        "bytes": len(content.encode("utf-8")),
    }


def apply_patch(root: str, unified_diff: str) -> dict:
    """Apply a unified diff via ``git apply`` inside the project root.

    Falls back to a plain ``patch`` call if git isn't available. Returns a
    summary dict; raises ``RuntimeError`` on non-zero exit with stderr.
    """
    import subprocess

    root_path = Path(root).expanduser().resolve()
    result = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        input=unified_diff,
        cwd=str(root_path),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git apply failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return {"applied": True, "stdout": result.stdout, "stderr": result.stderr}


def list_files(
    root: str, rel_dir: Optional[str] = None, max_entries: int = 200
) -> list:
    """List files inside a directory (non-recursive)."""
    base = _resolve_within(root, rel_dir or ".")
    if not base.is_dir():
        raise FileSystemSandboxError(f"Not a directory: {rel_dir}")
    entries = []
    for i, p in enumerate(sorted(base.iterdir())):
        if i >= max_entries:
            break
        entries.append(
            {
                "name": p.name,
                "is_dir": p.is_dir(),
                "size": p.stat().st_size if p.is_file() else None,
            }
        )
    return entries
