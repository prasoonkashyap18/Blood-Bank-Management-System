"""Shared pytest fixtures: an isolated Flask app + SQLite database per test.

Every test gets its own temporary SQLite file and session-file directory
(via pytest's tmp_path fixture), so tests never touch the real development
database at instance/bloodbank.db and never leave data behind.
"""

import sys
from pathlib import Path

import pytest
from cachelib import FileSystemCache

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app import create_app  # noqa: E402
from backend.config import TestConfig  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    session_dir = tmp_path / "flask_session"

    class CurrentTestConfig(TestConfig):
        DATABASE_PATH = db_path
        SESSION_CACHELIB = FileSystemCache(str(session_dir), threshold=500)

    application = create_app(CurrentTestConfig)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_admin(app):
    """Insert an admin user directly into the test database and return their credentials.

    This bypasses the public registration endpoint on purpose: it is the
    same trusted, non-public pathway database/create_admin.py uses, and lets
    tests exercise admin-only behaviour without a public "become admin" API.
    """

    def _make_admin(email="admin@example.com", password="adminpass123", full_name="Admin User"):
        with app.app_context():
            from backend.database import get_db

            db = get_db()
            db.execute(
                "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (full_name, email, generate_password_hash(password)),
            )
            db.commit()
        return {"email": email, "password": password, "fullName": full_name}

    return _make_admin


VALID_REGISTRATION = {
    "fullName": "Test Donor",
    "email": "test.donor@example.com",
    "phone": "9876543210",
    "bloodGroup": "O+",
    "city": "Pune",
    "lastDonationDate": "",
    "password": "secret123",
    "confirmPassword": "secret123",
    "consent": True,
}
