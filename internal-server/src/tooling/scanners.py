"""Security scanners with real-binary detection and deterministic stubs.

Each ``run_*`` function tries the real binary (semgrep / trivy / gitleaks)
via :func:`shutil.which`. If it's absent we fall back to a deterministic
stub that scans the project tree for a small hard-coded pattern set. The
stub is intentionally dumb: it must never raise (Warden depends on
determinism) and must return the same ``[Finding...]`` for the same input.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from .shell import run_shell, which


# ---------------------------------------------------------------- stub patterns
_SEMGREP_STUBS = [
    (
        re.compile(r"\beval\s*\("),
        "medium",
        "Use of eval() can enable arbitrary code execution",
    ),
    (
        re.compile(r"\bexec\s*\("),
        "medium",
        "Use of exec() can enable arbitrary code execution",
    ),
    (
        re.compile(r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True"),
        "high",
        "subprocess with shell=True invites shell-injection",
    ),
    (
        re.compile(r"--privileged"),
        "high",
        "Docker --privileged grants root-equivalent access to the host",
    ),
    (
        re.compile(r"DROP\s+TABLE", re.IGNORECASE),
        "high",
        "Unparameterised DROP TABLE statement",
    ),
    (
        re.compile(r"pickle\.loads\s*\("),
        "medium",
        "Deserialising untrusted pickle data is unsafe",
    ),
]

_GITLEAKS_STUBS = [
    (
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "critical",
        "AWS access key ID in source",
    ),
    (
        re.compile(r"-----BEGIN (?:RSA|OPENSSH) PRIVATE KEY-----"),
        "critical",
        "Private key committed to repository",
    ),
    (
        re.compile(r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]"),
        "high",
        "Hard-coded API key literal",
    ),
    (
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),
        "critical",
        "GitHub personal access token",
    ),
]


_SCAN_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".rb",
    ".java",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".env",
    ".ini",
    ".cfg",
    ".txt",
    ".md",
}

_SCAN_IGNORES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "dist",
    "build",
    ".tox",
}


# ---------------------------------------------------------------- helpers
def _iter_files(root: Path, max_files: int = 2000) -> List[Path]:
    out: List[Path] = []
    for dirpath, dirnames, filenames in _safe_walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SCAN_IGNORES]
        for name in filenames:
            if Path(name).suffix.lower() in _SCAN_SUFFIXES:
                out.append(Path(dirpath) / name)
                if len(out) >= max_files:
                    return out
    return out


def _safe_walk(root: Path):
    import os

    for dirpath, dirnames, filenames in os.walk(str(root)):
        # Filter ignored dirs in-place so os.walk doesn't descend.
        dirnames[:] = sorted(d for d in dirnames if d not in _SCAN_IGNORES)
        filenames.sort()
        yield dirpath, dirnames, filenames


def _stub_scan(root: Path, patterns, scanner: str) -> List[dict]:
    findings: List[dict] = []
    for file_path in _iter_files(root):
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for regex, severity, title in patterns:
                if regex.search(line):
                    findings.append(
                        {
                            "scanner": scanner,
                            "severity": severity,
                            "title": title,
                            "file": str(file_path.relative_to(root)),
                            "line": lineno,
                            "details": line.strip()[:200],
                        }
                    )
    findings.sort(key=lambda f: (f["file"], f["line"], f["severity"]))
    return findings


# ---------------------------------------------------------------- public API
def run_semgrep(project_path: str) -> List[dict]:
    root = Path(project_path).expanduser().resolve()
    if which("semgrep"):
        result = run_shell(
            "semgrep --json --config auto .",
            cwd=str(root),
            timeout_s=300,
        )
        if result.get("returncode") in (0, 1) and result.get("stdout"):
            try:
                parsed = json.loads(result["stdout"])
                return [
                    _semgrep_normalise(f, str(root)) for f in parsed.get("results", [])
                ]
            except json.JSONDecodeError:
                pass
        # Fall through to stub on any parse or run failure.
    return _stub_scan(root, _SEMGREP_STUBS, scanner="stub")


def _semgrep_normalise(item: dict, root: str) -> dict:
    return {
        "scanner": "semgrep",
        "severity": _map_semgrep_severity(
            (item.get("extra") or {}).get("severity", "INFO")
        ),
        "title": item.get("check_id") or "semgrep finding",
        "file": _rel(item.get("path"), root),
        "line": (item.get("start") or {}).get("line"),
        "details": ((item.get("extra") or {}).get("message") or "")[:500],
    }


def _map_semgrep_severity(s: str) -> str:
    s = (s or "").upper()
    if s in ("ERROR", "HIGH"):
        return "high"
    if s in ("WARNING", "MEDIUM"):
        return "medium"
    if s in ("INFO", "LOW"):
        return "low"
    return "medium"


def _rel(path: Optional[str], root: str) -> Optional[str]:
    if not path:
        return None
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return path


def run_trivy(project_path: str) -> List[dict]:
    """Trivy stub: honours a ``.trivy-seed.json`` seed file for tests."""
    root = Path(project_path).expanduser().resolve()
    if which("trivy"):
        result = run_shell(
            "trivy fs --quiet --format json .",
            cwd=str(root),
            timeout_s=300,
        )
        if result.get("returncode") == 0 and result.get("stdout"):
            try:
                parsed = json.loads(result["stdout"])
                return _trivy_normalise(parsed)
            except json.JSONDecodeError:
                pass
    seed = root / ".trivy-seed.json"
    if seed.exists():
        try:
            items = json.loads(seed.read_text(encoding="utf-8"))
            if isinstance(items, list):
                return [
                    {
                        "scanner": "stub",
                        "severity": item.get("severity", "medium"),
                        "title": item.get("title", "trivy stub finding"),
                        "file": item.get("file"),
                        "line": item.get("line"),
                        "details": item.get("details"),
                    }
                    for item in items
                ]
        except Exception:
            return []
    return []


def _trivy_normalise(parsed: dict) -> List[dict]:
    out: List[dict] = []
    for target in parsed.get("Results", []) or []:
        for vuln in target.get("Vulnerabilities", []) or []:
            out.append(
                {
                    "scanner": "trivy",
                    "severity": (vuln.get("Severity") or "medium").lower(),
                    "title": vuln.get("VulnerabilityID") or "trivy finding",
                    "file": target.get("Target"),
                    "line": None,
                    "details": vuln.get("Title") or "",
                }
            )
    return out


def run_gitleaks(project_path: str) -> List[dict]:
    root = Path(project_path).expanduser().resolve()
    if which("gitleaks"):
        result = run_shell(
            "gitleaks detect --no-git --redact --report-format json --report-path /tmp/gitleaks.json",
            cwd=str(root),
            timeout_s=300,
        )
        report = Path("/tmp/gitleaks.json")
        if report.exists():
            try:
                parsed = json.loads(report.read_text(encoding="utf-8"))
                return [
                    {
                        "scanner": "gitleaks",
                        "severity": "high",
                        "title": item.get("Description") or "gitleaks finding",
                        "file": item.get("File"),
                        "line": item.get("StartLine"),
                        "details": item.get("Match", "")[:200],
                    }
                    for item in parsed or []
                ]
            except json.JSONDecodeError:
                pass
    return _stub_scan(root, _GITLEAKS_STUBS, scanner="stub")


def summarise(findings: List[dict]) -> dict:
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", "medium")
        by_severity[sev] = by_severity.get(sev, 0) + 1
    blocking = sum(by_severity.get(s, 0) for s in ("critical", "high"))
    return {
        "total": len(findings),
        "by_severity": by_severity,
        "blocking_count": blocking,
        "has_blocking": blocking > 0,
    }
