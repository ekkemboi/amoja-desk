"""Configuration for Amoja Desk."""

import os
from datetime import timedelta
from pathlib import Path


class Config:
    """Base configuration."""

    BASE_DIR = Path(__file__).parent.parent
    DEFAULT_SQLITE_PATH = BASE_DIR / "instance" / "amoja-desk.db"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCREENSHOT_DIR = BASE_DIR / "screenshots"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "jwt-secret-key-change-in-production-min-32-chars"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.environ.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:5000/api/auth/callback"
    )

    # Cookie Security
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    JWT_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///:memory:"
    )
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    def __init__(self):
        """Validate required configuration."""
        super().__init__()
        for name in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = os.environ.get(name)
            if not value or not value.strip():
                raise ValueError(
                    f"{name} environment variable must be set in production"
                )
            setattr(self, name, value)

        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            self.SQLALCHEMY_DATABASE_URI = database_url


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
