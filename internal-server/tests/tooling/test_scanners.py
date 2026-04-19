"""Scanner stub tests."""

from __future__ import annotations

import pytest

from src.tooling import scanners


def test_semgrep_stub_flags_shell_true(tmp_path):
    bad = tmp_path / "x.py"
    bad.write_text('import subprocess\nsubprocess.run("ls", shell=True)\n')
    findings = scanners.run_semgrep(str(tmp_path))
    assert any(f["severity"] == "high" for f in findings)
    assert any("shell" in f["title"].lower() for f in findings)


def test_gitleaks_stub_flags_aws_key(tmp_path):
    (tmp_path / "env.txt").write_text("AWS_ACCESS_KEY_ID=AKIAABCDEFGHIJKLMNOP\n")
    findings = scanners.run_gitleaks(str(tmp_path))
    assert any(f["severity"] == "critical" for f in findings)


def test_trivy_stub_returns_empty_without_seed(tmp_path):
    (tmp_path / "hello.py").write_text("print('hi')\n")
    assert scanners.run_trivy(str(tmp_path)) == []


def test_trivy_stub_honours_seed(tmp_path):
    import json

    (tmp_path / "hello.py").write_text("print('hi')\n")
    (tmp_path / ".trivy-seed.json").write_text(
        json.dumps([{"severity": "high", "title": "CVE-SEEDED-1", "file": "hello.py"}])
    )
    findings = scanners.run_trivy(str(tmp_path))
    assert findings and findings[0]["title"] == "CVE-SEEDED-1"


def test_summarise_counts():
    summary = scanners.summarise(
        [
            {"severity": "high", "title": "x"},
            {"severity": "high", "title": "y"},
            {"severity": "low", "title": "z"},
        ]
    )
    assert summary["blocking_count"] == 2
    assert summary["has_blocking"] is True
    assert summary["by_severity"]["high"] == 2
