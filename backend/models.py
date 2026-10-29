"""Thin data-access helpers around raw, parameterized SQL.

Deliberately not a full ORM: for a student project, explicit SQL with named
parameters is easier to read, review, and explain in a viva than a mapping
layer, while still avoiding string-built queries (and SQL injection).
"""

from __future__ import annotations

import sqlite3
from typing import Any


def normalize_email(email: str) -> str:
    return email.strip().lower()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user_by_email(db: sqlite3.Connection, email: str) -> dict | None:
    row = db.execute(
        "SELECT * FROM users WHERE email = ?", (normalize_email(email),)
    ).fetchone()
    return row_to_dict(row)


def get_user_by_id(db: sqlite3.Connection, user_id: int) -> dict | None:
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_dict(row)


def create_user(
    db: sqlite3.Connection,
    *,
    full_name: str,
    email: str,
    password_hash: str,
    role: str = "user",
) -> int:
    cursor = db.execute(
        """
        INSERT INTO users (full_name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (full_name.strip(), normalize_email(email), password_hash, role),
    )
    db.commit()
    return cursor.lastrowid


def public_user_view(user: dict) -> dict:
    """Fields safe to send to the client: never the password hash."""
    return {
        "id": user["id"],
        "fullName": user["full_name"],
        "email": user["email"],
        "role": user["role"],
        "createdAt": user["created_at"],
    }


# ---------------------------------------------------------------------------
# Donors
# ---------------------------------------------------------------------------

def create_donor(
    db: sqlite3.Connection,
    *,
    user_id: int | None,
    full_name: str,
    blood_group: str,
    phone: str,
    city: str,
    last_donation_date: str | None,
    consent_given: bool,
) -> int:
    cursor = db.execute(
        """
        INSERT INTO donors
            (user_id, full_name, blood_group, phone, city, last_donation_date, consent_given)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            full_name.strip(),
            blood_group,
            phone.strip(),
            city.strip(),
            last_donation_date,
            1 if consent_given else 0,
        ),
    )
    db.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# Admin summary counts (read-only; used to demonstrate role-based access)
# ---------------------------------------------------------------------------

def get_admin_summary(db: sqlite3.Connection) -> dict:
    def count(table: str) -> int:
        return db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]

    pending_requests = db.execute(
        "SELECT COUNT(*) AS n FROM blood_requests WHERE status = 'Pending'"
    ).fetchone()["n"]

    return {
        "totalUsers": count("users"),
        "totalDonors": count("donors"),
        "totalInventoryBatches": count("blood_inventory"),
        "totalRequests": count("blood_requests"),
        "pendingRequests": pending_requests,
    }
