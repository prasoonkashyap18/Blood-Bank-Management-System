"""Database schema, foreign-key enforcement, persistence, and seed-data tests."""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db  # noqa: E402

EXPECTED_TABLES = {"users", "donors", "blood_inventory", "blood_requests", "donations"}


def _connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def test_init_db_creates_all_tables(tmp_path):
    db_path = tmp_path / "schema.db"
    init_db(db_path)

    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    finally:
        conn.close()

    table_names = {row["name"] for row in rows}
    assert EXPECTED_TABLES.issubset(table_names)


def test_foreign_key_violation_is_rejected(tmp_path):
    db_path = tmp_path / "fk.db"
    init_db(db_path)
    conn = _connect(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO donations (donor_id, donation_date) VALUES (?, ?)",
                (999999, "2026-01-01"),
            )
    finally:
        conn.close()


def test_data_persists_across_connections(tmp_path):
    db_path = tmp_path / "persist.db"
    init_db(db_path)

    conn1 = _connect(db_path)
    conn1.execute(
        """
        INSERT INTO donors (full_name, blood_group, phone, city, consent_given)
        VALUES ('Persist Test', 'O+', '9000000000', 'Pune', 1)
        """
    )
    conn1.commit()
    conn1.close()

    conn2 = _connect(db_path)
    try:
        row = conn2.execute("SELECT full_name FROM donors WHERE full_name = 'Persist Test'").fetchone()
    finally:
        conn2.close()

    assert row is not None
    assert row["full_name"] == "Persist Test"


def test_init_db_does_not_delete_existing_records(tmp_path):
    db_path = tmp_path / "idempotent.db"
    init_db(db_path)

    conn = _connect(db_path)
    conn.execute(
        """
        INSERT INTO donors (full_name, blood_group, phone, city, consent_given)
        VALUES ('Should Survive', 'A+', '9111111111', 'Mumbai', 1)
        """
    )
    conn.commit()
    conn.close()

    # Re-run initialization, as the app does on every startup.
    init_db(db_path)

    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT full_name FROM donors WHERE full_name = 'Should Survive'").fetchone()
    finally:
        conn.close()

    assert row is not None


def test_seed_data_is_not_duplicated_on_repeat_run(tmp_path, monkeypatch):
    db_path = tmp_path / "seed.db"
    init_db(db_path)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "database"))
    import seed_data  # noqa: E402

    conn = _connect(db_path)
    try:
        seed_data.seed(conn)
        first_count = conn.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
        assert first_count == len(seed_data.DONORS)

        seed_data.seed(conn)
        second_count = conn.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
        assert second_count == first_count
    finally:
        conn.close()
