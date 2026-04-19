"""Tests for GeminiCredentials loading in the CredentialManager."""

from __future__ import annotations

import json
import os

import pytest

from src.core.credentials import (
    CredentialError,
    CredentialManager,
    GeminiCredentials,
)


@pytest.fixture
def clean_env(monkeypatch):
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL", "GEMINI_API_BASE"):
        monkeypatch.delenv(var, raising=False)
    yield monkeypatch


class TestGeminiCredentials:
    def test_gemini_api_key_env_wins(self, clean_env):
        clean_env.setenv("GEMINI_API_KEY", "from-gemini-env")
        clean_env.setenv("GOOGLE_API_KEY", "from-google-env")
        manager = CredentialManager()
        creds = manager.get_gemini_credentials()
        assert creds.api_key == "from-gemini-env"
        assert creds.model == "gemini-2.5-flash"

    def test_falls_back_to_google_api_key(self, clean_env):
        clean_env.setenv("GOOGLE_API_KEY", "from-google-env")
        manager = CredentialManager()
        creds = manager.get_gemini_credentials()
        assert creds.api_key == "from-google-env"

    def test_reads_from_credentials_file(self, clean_env, tmp_path, monkeypatch):
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(
            json.dumps({"gemini": {"api_key": "file-key", "model": "gemini-2.5-pro"}})
        )
        monkeypatch.setattr(
            os.path,
            "expanduser",
            lambda p: str(creds_file) if p.endswith("credentials.json") else p,
        )
        manager = CredentialManager()
        creds = manager.get_gemini_credentials()
        assert creds.api_key == "file-key"
        assert creds.model == "gemini-2.5-pro"

    def test_env_overrides_file(self, clean_env, tmp_path, monkeypatch):
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({"gemini": {"api_key": "file-key"}}))
        monkeypatch.setattr(
            os.path,
            "expanduser",
            lambda p: str(creds_file) if p.endswith("credentials.json") else p,
        )
        clean_env.setenv("GEMINI_API_KEY", "env-key")
        manager = CredentialManager()
        creds = manager.get_gemini_credentials()
        assert creds.api_key == "env-key"

    def test_missing_key_raises_credential_error(
        self, clean_env, tmp_path, monkeypatch
    ):
        missing = tmp_path / "nope.json"
        monkeypatch.setattr(
            os.path,
            "expanduser",
            lambda p: str(missing) if p.endswith("credentials.json") else p,
        )
        manager = CredentialManager()
        with pytest.raises(CredentialError) as exc:
            manager.get_gemini_credentials()
        assert "No Gemini API key" in str(exc.value)

    def test_model_override_via_env(self, clean_env):
        clean_env.setenv("GEMINI_API_KEY", "k")
        clean_env.setenv("GEMINI_MODEL", "gemini-2.5-pro")
        manager = CredentialManager()
        creds = manager.get_gemini_credentials()
        assert creds.model == "gemini-2.5-pro"

    def test_caches_per_manager(self, clean_env):
        clean_env.setenv("GEMINI_API_KEY", "first")
        manager = CredentialManager()
        first = manager.get_gemini_credentials()
        clean_env.setenv("GEMINI_API_KEY", "second")
        # Should still return the cached credentials.
        second = manager.get_gemini_credentials()
        assert first is second

    def test_credentials_model_defaults(self):
        creds = GeminiCredentials(api_key="x")
        assert creds.model == "gemini-2.5-flash"
        assert creds.api_base is None
