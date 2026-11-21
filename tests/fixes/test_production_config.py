"""Regression tests for production configuration validation."""

import pytest

from src.app import create_app


@pytest.fixture
def production_env(monkeypatch):
    """Provide production settings without touching a live database."""
    values = {
        "SECRET_KEY": "test-session-secret-for-production-config",
        "JWT_SECRET_KEY": "test-jwt-secret-for-production-config",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return values


@pytest.mark.parametrize("name", ["SECRET_KEY", "JWT_SECRET_KEY"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_production_rejects_missing_settings(production_env, monkeypatch, name, value):
    """Production startup rejects absent or blank required settings."""
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        create_app("production")


def test_production_uses_current_environment(production_env):
    """Settings supplied after module import are used by the app factory."""
    app = create_app("production")
    assert app.config["SECRET_KEY"] == production_env["SECRET_KEY"]
    assert app.config["JWT_SECRET_KEY"] == production_env["JWT_SECRET_KEY"]
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///")
    assert app.debug is False


def test_production_accepts_database_url_override(production_env, monkeypatch):
    """An explicit DATABASE_URL takes precedence over the SQLite default."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/amoja-desk-production.db")
    app = create_app("production")
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:////tmp/amoja-desk-production.db"
