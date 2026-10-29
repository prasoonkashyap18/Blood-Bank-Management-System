"""SQLite connection handling and schema management.

All timestamps are stored as ISO-8601 UTC strings, e.g. "2026-10-29T12:34:56.789Z"
(produced by SQLite's STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')). Plain dates
(last_donation_date, collected_date, expiry_date, donation_date) are stored as
ISO-8601 date strings, e.g. "2026-10-29".
"""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS donors (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    full_name           TEXT NOT NULL,
    blood_group         TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    phone               TEXT NOT NULL,
    city                TEXT NOT NULL,
    last_donation_date  TEXT,
    consent_given       INTEGER NOT NULL DEFAULT 0 CHECK (consent_given IN (0, 1)),
    status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at          TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_donors_blood_group ON donors(blood_group);
CREATE INDEX IF NOT EXISTS idx_donors_city ON donors(city);

CREATE TABLE IF NOT EXISTS blood_inventory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_group     TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    quantity_units  INTEGER NOT NULL DEFAULT 0 CHECK (quantity_units >= 0),
    collected_date  TEXT,
    expiry_date     TEXT,
    created_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_inventory_blood_group ON blood_inventory(blood_group);

CREATE TABLE IF NOT EXISTS blood_requests (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER REFERENCES users(id) ON DELETE SET NULL,
    requester_name      TEXT NOT NULL,
    requester_contact   TEXT NOT NULL,
    blood_group         TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    quantity_units      INTEGER NOT NULL CHECK (quantity_units > 0),
    location            TEXT NOT NULL,
    urgency             TEXT NOT NULL CHECK (urgency IN ('Critical','High','Medium','Low')),
    status              TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Approved','Fulfilled','Rejected')),
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at          TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_requests_status ON blood_requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_blood_group ON blood_requests(blood_group);

CREATE TABLE IF NOT EXISTS donations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id        INTEGER NOT NULL REFERENCES donors(id) ON DELETE CASCADE,
    donation_date   TEXT NOT NULL,
    quantity_units  INTEGER NOT NULL DEFAULT 1 CHECK (quantity_units > 0),
    created_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_donations_donor_id ON donations(donor_id);
"""


def _connect(db_path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path) -> None:
    """Create the database file and tables if they do not already exist.

    Safe to call every time the application starts: CREATE TABLE IF NOT
    EXISTS never touches existing tables or rows.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db() -> sqlite3.Connection:
    """Return a request-scoped SQLite connection, creating it if needed."""
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app) -> None:
    """Wire the database into the Flask app's lifecycle."""
    app.teardown_appcontext(close_db)
    init_db(app.config["DATABASE_PATH"])
