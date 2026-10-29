"""Provision (create or promote) an administrator account.

There is no public API to become an admin, by design: an administrator
account is created only through this script, run locally by a developer who
already has shell access to the machine.

Reads credentials from environment variables (see .env.example):
    ADMIN_NAME      optional, defaults to "Administrator"
    ADMIN_EMAIL     required
    ADMIN_PASSWORD  required, must be at least 8 characters

Usage (from the project root, after init_db.py):
    python database/create_admin.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from backend.config import BASE_DIR, Config  # noqa: E402
from backend.database import init_db  # noqa: E402

import sqlite3  # noqa: E402

PLACEHOLDER_PASSWORDS = {"", "change-me-now", "changeme", "admin", "password"}


def main() -> int:
    load_dotenv(BASE_DIR / ".env")

    name = os.environ.get("ADMIN_NAME", "Administrator").strip() or "Administrator"
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")

    if not email or "@" not in email:
        print("ERROR: Set ADMIN_EMAIL to a valid email address in your .env file.")
        return 1

    if len(password) < 8 or password.lower() in PLACEHOLDER_PASSWORDS:
        print(
            "ERROR: Set ADMIN_PASSWORD in your .env file to a real password "
            "of at least 8 characters (not the placeholder value)."
        )
        return 1

    init_db(Config.DATABASE_PATH)
    conn = sqlite3.connect(str(Config.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        password_hash = generate_password_hash(password)
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET role = 'admin', password_hash = ?, full_name = ?, is_active = 1 WHERE id = ?",
                (password_hash, name, existing["id"]),
            )
            print(f"Updated existing account '{email}' and promoted it to admin.")
        else:
            conn.execute(
                "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (name, email, password_hash),
            )
            print(f"Created new admin account '{email}'.")
        conn.commit()
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
