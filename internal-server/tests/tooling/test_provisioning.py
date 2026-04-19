"""Tests for src/tooling/provisioning.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.tooling import provisioning


# ------------------------------------------------------------ inspect_project
class TestInspectProject:
    def test_python_repo_with_requirements_txt(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask==3.0.0\n")
        (tmp_path / "app.py").write_text("print('hi')\n")

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.detected_stack == "python"
        assert "requirements.txt" in inv.package_files
        assert inv.entrypoint == "app.py"
        assert inv.has_dockerfile is False
        assert inv.has_compose is False
        assert inv.hinted_port == 8000

    def test_python_repo_with_pyproject_takes_precedence(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        (tmp_path / "main.py").write_text("print('hi')\n")

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.detected_stack == "python"
        assert "pyproject.toml" in inv.package_files
        assert inv.entrypoint == "main.py"

    def test_node_repo_reads_main_from_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "app", "main": "server.js"})
        )

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.detected_stack == "node"
        assert inv.entrypoint == "server.js"
        assert inv.hinted_port == 3000

    def test_node_repo_falls_back_to_start_script(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "app", "scripts": {"start": "node index.js"}})
        )

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.entrypoint == "package.json#start"

    def test_static_repo(self, tmp_path: Path) -> None:
        (tmp_path / "index.html").write_text("<!doctype html>")

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.detected_stack == "static"
        assert inv.entrypoint == "index.html"
        assert inv.hinted_port == 80

    def test_unknown_stack(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# hi\n")

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.detected_stack == "unknown"
        assert inv.package_files == []
        assert inv.entrypoint is None

    def test_detects_existing_dockerfile_and_compose(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM scratch\n")
        (tmp_path / "compose.yml").write_text("services: {}\n")
        (tmp_path / "requirements.txt").write_text("")

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.has_dockerfile is True
        assert inv.has_compose is True
        assert inv.compose_filename == "compose.yml"

    def test_compose_filename_precedence(self, tmp_path: Path) -> None:
        # compose.yml wins over docker-compose.yml when both present.
        (tmp_path / "compose.yml").write_text("services: {}\n")
        (tmp_path / "docker-compose.yml").write_text("services: {}\n")

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.compose_filename == "compose.yml"

    def test_env_file_port_hint(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("")
        (tmp_path / ".env").write_text("FOO=bar\nPORT=9090\n")

        inv = provisioning.inspect_project(str(tmp_path))

        assert inv.hinted_port == 9090
        assert inv.has_env_file is True

    def test_missing_root_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            provisioning.inspect_project(str(tmp_path / "does-not-exist"))


# -------------------------------------------------------- render_dockerfile
class TestRenderDockerfile:
    def test_python_with_requirements(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("flask\n")
        (tmp_path / "app.py").write_text("")
        inv = provisioning.inspect_project(str(tmp_path))

        rendered = provisioning.render_dockerfile("python", inv)

        assert "FROM python:3.11-slim" in rendered
        assert "pip install --no-cache-dir -r requirements.txt" in rendered
        assert 'CMD ["python", "app.py"]' in rendered
        assert "EXPOSE 8000" in rendered

    def test_python_with_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        (tmp_path / "main.py").write_text("")
        inv = provisioning.inspect_project(str(tmp_path))

        rendered = provisioning.render_dockerfile("python", inv)

        assert "pip install --no-cache-dir ." in rendered
        assert 'CMD ["python", "main.py"]' in rendered

    def test_node_default_start(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"start": "node ."}})
        )
        inv = provisioning.inspect_project(str(tmp_path))

        rendered = provisioning.render_dockerfile("node", inv)

        assert "FROM node:20-alpine" in rendered
        assert 'CMD ["npm", "start"]' in rendered
        assert "EXPOSE 3000" in rendered

    def test_node_with_main(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"main": "server.js"}))
        inv = provisioning.inspect_project(str(tmp_path))

        rendered = provisioning.render_dockerfile("node", inv)

        assert 'CMD ["node", "server.js"]' in rendered

    def test_static(self, tmp_path: Path) -> None:
        (tmp_path / "index.html").write_text("<html></html>")
        inv = provisioning.inspect_project(str(tmp_path))

        rendered = provisioning.render_dockerfile("static", inv)

        assert "FROM nginx:alpine" in rendered
        assert "EXPOSE 80" in rendered

    def test_unknown_stack_raises(self, tmp_path: Path) -> None:
        inv = provisioning.inspect_project(str(tmp_path))
        with pytest.raises(provisioning.UnknownStackError):
            provisioning.render_dockerfile("rust", inv)


# -------------------------------------------------------------- render_compose
class TestRenderCompose:
    def test_basic(self) -> None:
        out = provisioning.render_compose("myapp", 8000, has_env_file=False)
        assert "services:" in out
        assert "myapp:" in out
        assert "build: ." in out
        assert '"8000:8000"' in out
        assert "env_file" not in out

    def test_includes_env_file_block(self) -> None:
        out = provisioning.render_compose("myapp", 3000, has_env_file=True)
        assert "env_file:" in out
        assert "- .env" in out

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValueError):
            provisioning.render_compose("", 8000, has_env_file=False)


# --------------------------------------------------------------- write_scaffold
class TestWriteScaffold:
    def test_writes_new_files(self, tmp_path: Path) -> None:
        files = {"Dockerfile": "FROM scratch\n", "compose.yml": "services: {}\n"}
        results = provisioning.write_scaffold(str(tmp_path), files)

        assert results == {"Dockerfile": "written", "compose.yml": "written"}
        assert (tmp_path / "Dockerfile").read_text() == "FROM scratch\n"
        assert (tmp_path / "compose.yml").read_text() == "services: {}\n"

    def test_skips_existing_by_default(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("USER-OWNED\n")
        files = {"Dockerfile": "AUTO\n"}

        results = provisioning.write_scaffold(str(tmp_path), files)

        assert results == {"Dockerfile": "skipped_exists"}
        assert (tmp_path / "Dockerfile").read_text() == "USER-OWNED\n"

    def test_overwrite_true_replaces(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("USER-OWNED\n")
        files = {"Dockerfile": "AUTO\n"}

        results = provisioning.write_scaffold(str(tmp_path), files, overwrite=True)

        assert results == {"Dockerfile": "written"}
        assert (tmp_path / "Dockerfile").read_text() == "AUTO\n"


# ------------------------------------------------------------ default_service_name
class TestDefaultServiceName:
    def test_lowercases_and_sanitises(self, tmp_path: Path) -> None:
        weird = tmp_path / "My Cool App!"
        weird.mkdir()
        assert provisioning.default_service_name(str(weird)) == "my-cool-app"

    def test_falls_back_to_app_for_unnameable(self, tmp_path: Path) -> None:
        # A name that sanitises away completely should fall back.
        weird = tmp_path / "---"
        weird.mkdir()
        assert provisioning.default_service_name(str(weird)) == "app"
