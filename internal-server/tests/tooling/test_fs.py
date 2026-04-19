"""Filesystem sandbox tests."""

from __future__ import annotations

import pytest

from src.tooling.fs import (
    FileSystemSandboxError,
    list_files,
    read_file,
    write_file,
)


def test_write_and_read_roundtrip(tmp_path):
    result = write_file(str(tmp_path), "hello.txt", "hi there")
    assert result["bytes"] == len("hi there".encode("utf-8"))
    assert read_file(str(tmp_path), "hello.txt") == "hi there"


def test_escape_attempt_blocked(tmp_path):
    with pytest.raises(FileSystemSandboxError):
        read_file(str(tmp_path), "../../etc/passwd")


def test_list_files_skips_ignored(tmp_path):
    write_file(str(tmp_path), "a.py", "print('a')")
    write_file(str(tmp_path), "b.txt", "b")
    entries = list_files(str(tmp_path))
    names = sorted(e["name"] for e in entries)
    assert "a.py" in names and "b.txt" in names


def test_read_truncates_large_file(tmp_path):
    big = "x" * 5000
    write_file(str(tmp_path), "big.txt", big)
    data = read_file(str(tmp_path), "big.txt", max_bytes=100)
    assert "truncated" in data
