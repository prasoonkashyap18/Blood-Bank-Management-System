"""Application configuration loaded from environment variables (.env)."""

import os
from datetime import timedelta
from pathlib import Path

from cachelib import FileSystemCache
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

INSTANCE_DIR = BASE_DIR / "instance"


class Config:
    """Default configuration for local development."""

    # Flask uses this to sign session cookies and CSRF tokens. Set
    # FLASK_SECRET_KEY in a local .env file (see .env.example). The fallback
    # below is only for convenience when no .env is present and must never
    # be relied on outside a local student demo.
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-insecure-secret-key-change-me")

    DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", INSTANCE_DIR / "bloodbank.db"))

    # Server-side sessions: the browser only ever holds a signed session id,
    # the actual session data lives in files under instance/flask_session.
    SESSION_TYPE = "cachelib"
    SESSION_CACHELIB = FileSystemCache(str(INSTANCE_DIR / "flask_session"), threshold=500)
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # only applies when "remember me" is checked
    SESSION_COOKIE_NAME = "bloodbank_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Only set this to true once the app is served over HTTPS.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # tokens stay valid for the whole session

    JSON_SORT_KEYS = False


class TestConfig(Config):
    """Configuration used by the automated test suite."""

    TESTING = True
    WTF_CSRF_ENABLED = False  # tests exercise the API directly, not CSRF itself
    SESSION_COOKIE_SECURE = False
