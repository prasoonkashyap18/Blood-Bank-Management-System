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
    email               TEXT,
    blood_group         TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    phone               TEXT NOT NULL,
    city                TEXT NOT NULL,
    last_donation_date  TEXT,
    consent_given       INTEGER NOT NULL DEFAULT 0 CHECK (consent_given IN (0, 1)),
    status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at          TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at          TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_donors_blood_group ON donors(blood_group);
CREATE INDEX IF NOT EXISTS idx_donors_city ON donors(city);
CREATE INDEX IF NOT EXISTS idx_donors_status ON donors(status);

CREATE TABLE IF NOT EXISTS blood_inventory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_group     TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    quantity_units  INTEGER NOT NULL DEFAULT 0 CHECK (quantity_units >= 0),
    collected_date  TEXT,
    expiry_date     TEXT,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_inventory_blood_group ON blood_inventory(blood_group);
CREATE INDEX IF NOT EXISTS idx_inventory_status ON blood_inventory(status);

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
    rejection_reason    TEXT,
    decided_by          INTEGER REFERENCES users(id) ON DELETE SET NULL,
    fulfilled_at        TEXT,
    created_at          TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at          TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_requests_status ON blood_requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_blood_group ON blood_requests(blood_group);
CREATE INDEX IF NOT EXISTS idx_requests_user_id ON blood_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_created_at ON blood_requests(created_at);

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


# Columns added after a table's initial release, for databases created by an
# earlier version of the app. Each entry is plain "ADD COLUMN" DDL — additive
# only, never a destructive rebuild, and safe to attempt on every startup
# since _migrate() only applies a column that is actually missing.
MIGRATIONS = {
    "donors": [
        "ALTER TABLE donors ADD COLUMN email TEXT",
        # SQLite's ADD COLUMN only accepts a constant default, so this one is
        # added nullable and backfilled with an UPDATE just below.
        "ALTER TABLE donors ADD COLUMN updated_at TEXT",
    ],
    "blood_inventory": [
        "ALTER TABLE blood_inventory ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
        "ALTER TABLE blood_inventory ADD COLUMN notes TEXT",
    ],
    "blood_requests": [
        "ALTER TABLE blood_requests ADD COLUMN rejection_reason TEXT",
        "ALTER TABLE blood_requests ADD COLUMN decided_by INTEGER",
        "ALTER TABLE blood_requests ADD COLUMN fulfilled_at TEXT",
    ],
}

# Backfill for columns above that couldn't use a computed default inline.
BACKFILLS = [
    "UPDATE donors SET updated_at = created_at WHERE updated_at IS NULL",
]


def _migrate(conn: sqlite3.Connection) -> None:
    """Add any columns introduced after a table was first created.

    Reads each table's current columns with PRAGMA table_info and only runs
    the ALTER TABLE statements for columns that are actually missing, so
    re-running this against an already-migrated or brand-new database (where
    executescript(SCHEMA) already created the columns) is a no-op.
    """
    for table, statements in MIGRATIONS.items():
        existing_tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        if not existing_tables:
            continue  # a brand-new database: executescript(SCHEMA) already has the final shape

        existing_columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for statement in statements:
            # Each statement is "ALTER TABLE <table> ADD COLUMN <col> ..."; pull <col> out to check it.
            column_name = statement.split("ADD COLUMN", 1)[1].strip().split()[0]
            if column_name not in existing_columns:
                conn.execute(statement)
    conn.commit()


def _backfill(conn: sqlite3.Connection) -> None:
    """Fill in values for columns added by _migrate(), after tables are guaranteed to exist."""
    for statement in BACKFILLS:
        conn.execute(statement)
    conn.commit()


def init_db(db_path) -> None:
    """Create the database file and tables if they do not already exist,
    then apply any additive column migrations for pre-existing databases.

    Safe to call every time the application starts: CREATE TABLE IF NOT
    EXISTS and the additive ALTER TABLE migrations never touch existing
    rows, and never run twice for the same column.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        # Add any columns a pre-existing table is missing *before* running
        # the schema script, since that script's CREATE INDEX statements
        # reference columns (e.g. blood_inventory.status) that only exist
        # on an old database once the migration below has added them.
        _migrate(conn)
        conn.executescript(SCHEMA)
        conn.commit()
        _backfill(conn)
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
