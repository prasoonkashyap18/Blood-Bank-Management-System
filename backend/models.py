"""Thin data-access helpers around raw, parameterized SQL.

Deliberately not a full ORM: for a student project, explicit SQL with named
parameters is easier to read, review, and explain in a viva than a mapping
layer, while still avoiding string-built queries (and SQL injection).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from .validators import BLOOD_GROUPS_ORDERED


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
    email: str | None = None,
) -> int:
    cursor = db.execute(
        """
        INSERT INTO donors
            (user_id, full_name, email, blood_group, phone, city, last_donation_date, consent_given)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            full_name.strip(),
            email,
            blood_group,
            phone.strip(),
            city.strip(),
            last_donation_date,
            1 if consent_given else 0,
        ),
    )
    db.commit()
    return cursor.lastrowid


def get_donor_by_id(db: sqlite3.Connection, donor_id: int) -> dict | None:
    row = db.execute("SELECT * FROM donors WHERE id = ?", (donor_id,)).fetchone()
    return row_to_dict(row)


def get_donor_by_user_id(db: sqlite3.Connection, user_id: int) -> dict | None:
    row = db.execute("SELECT * FROM donors WHERE user_id = ?", (user_id,)).fetchone()
    return row_to_dict(row)


# Columns an owner or an admin is allowed to change via update_donor(); keys
# here are the only names ever interpolated into the UPDATE statement below,
# and they are never taken from client input directly (see backend/donors.py).
DONOR_OWNER_EDITABLE_FIELDS = {"full_name", "email", "blood_group", "phone", "city", "last_donation_date"}
DONOR_ADMIN_ONLY_FIELDS = {"status"}
DONOR_EDITABLE_FIELDS = DONOR_OWNER_EDITABLE_FIELDS | DONOR_ADMIN_ONLY_FIELDS


def update_donor(db: sqlite3.Connection, donor_id: int, fields: dict) -> None:
    """Update only the given columns. `fields` keys must be a subset of DONOR_EDITABLE_FIELDS."""
    if not fields:
        return
    assert set(fields).issubset(DONOR_EDITABLE_FIELDS), "attempted to update a non-whitelisted donor column"
    assignments = ", ".join(f"{column} = ?" for column in fields)
    values = [*fields.values(), donor_id]
    db.execute(
        f"UPDATE donors SET {assignments}, updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
        values,
    )
    db.commit()


def list_donors(
    db: sqlite3.Connection,
    *,
    q: str | None = None,
    blood_group: str | None = None,
    city: str | None = None,
    status: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Search/filter donors. Returns (rows, total_matching_count) for pagination.

    Every value is passed as a bound parameter; only fixed column names ever
    appear in the SQL text itself, so this is not vulnerable to SQL injection
    regardless of what a caller passes as q/blood_group/city/etc.
    """
    clauses: list[str] = []
    params: list[Any] = []

    if q:
        clauses.append("full_name LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(q)}%")
    if blood_group:
        clauses.append("blood_group = ?")
        params.append(blood_group)
    if city:
        clauses.append("city LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(city)}%")
    if status:
        clauses.append("status = ?")
        params.append(status)
    if email:
        clauses.append("email LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(email)}%")
    if phone:
        clauses.append("phone LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(phone)}%")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    total = db.execute(f"SELECT COUNT(*) AS n FROM donors {where_sql}", params).fetchone()["n"]
    rows = db.execute(
        f"""
        SELECT * FROM donors {where_sql}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()

    return [row_to_dict(row) for row in rows], total


def _escape_like(value: str) -> str:
    """Escape SQL LIKE wildcards in user input so a search for e.g. "50%" or "a_b" is literal."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def donor_public_view(donor: dict) -> dict:
    """Fields safe to show to anyone, including anonymous visitors: no contact details."""
    return {
        "id": donor["id"],
        "fullName": donor["full_name"],
        "bloodGroup": donor["blood_group"],
        "city": donor["city"],
        "status": donor["status"],
        "lastDonationDate": donor["last_donation_date"],
        "createdAt": donor["created_at"],
    }


def donor_private_view(donor: dict) -> dict:
    """Fields visible to the donor's own account or an administrator: adds contact details."""
    view = donor_public_view(donor)
    view.update(
        {
            "email": donor["email"],
            "phone": donor["phone"],
            "userId": donor["user_id"],
            "consentGiven": bool(donor["consent_given"]),
            "updatedAt": donor["updated_at"],
        }
    )
    return view


# ---------------------------------------------------------------------------
# Donations (read-only in Step 3 — recording donations is Step 4 scope)
# ---------------------------------------------------------------------------

def list_donations_for_donor(db: sqlite3.Connection, donor_id: int) -> list[dict]:
    rows = db.execute(
        "SELECT * FROM donations WHERE donor_id = ? ORDER BY donation_date DESC, id DESC",
        (donor_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def donation_view(donation: dict) -> dict:
    return {
        "id": donation["id"],
        "donorId": donation["donor_id"],
        "donationDate": donation["donation_date"],
        "quantityUnits": donation["quantity_units"],
        "createdAt": donation["created_at"],
    }


# ---------------------------------------------------------------------------
# Blood inventory
# ---------------------------------------------------------------------------

INVENTORY_EDITABLE_FIELDS = {
    "blood_group",
    "quantity_units",
    "collected_date",
    "expiry_date",
    "status",
    "notes",
}


def create_inventory_batch(
    db: sqlite3.Connection,
    *,
    blood_group: str,
    quantity_units: int,
    collected_date: str | None,
    expiry_date: str | None,
    notes: str | None = None,
) -> int:
    cursor = db.execute(
        """
        INSERT INTO blood_inventory (blood_group, quantity_units, collected_date, expiry_date, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (blood_group, quantity_units, collected_date, expiry_date, notes),
    )
    db.commit()
    return cursor.lastrowid


def get_inventory_batch(db: sqlite3.Connection, batch_id: int) -> dict | None:
    row = db.execute("SELECT * FROM blood_inventory WHERE id = ?", (batch_id,)).fetchone()
    return row_to_dict(row)


def list_inventory_batches(
    db: sqlite3.Connection, *, blood_group: str | None = None, status: str | None = None
) -> list[dict]:
    clauses: list[str] = []
    params: list[Any] = []
    if blood_group:
        clauses.append("blood_group = ?")
        params.append(blood_group)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        f"SELECT * FROM blood_inventory {where_sql} ORDER BY blood_group, expiry_date IS NULL, expiry_date",
        params,
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def update_inventory_batch(db: sqlite3.Connection, batch_id: int, fields: dict) -> None:
    if not fields:
        return
    assert set(fields).issubset(
        INVENTORY_EDITABLE_FIELDS
    ), "attempted to update a non-whitelisted inventory column"
    assignments = ", ".join(f"{column} = ?" for column in fields)
    values = [*fields.values(), batch_id]
    db.execute(
        f"UPDATE blood_inventory SET {assignments}, updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
        values,
    )
    db.commit()


def inventory_batch_view(batch: dict, *, today: date | None = None, near_expiry_days: int = 7) -> dict:
    today = today or date.today()
    expiry_status = _expiry_status(batch["expiry_date"], today=today, near_expiry_days=near_expiry_days)
    return {
        "id": batch["id"],
        "bloodGroup": batch["blood_group"],
        "quantityUnits": batch["quantity_units"],
        "collectedDate": batch["collected_date"],
        "expiryDate": batch["expiry_date"],
        "status": batch["status"],
        "notes": batch["notes"],
        "expiryStatus": expiry_status,
        "createdAt": batch["created_at"],
        "updatedAt": batch["updated_at"],
    }


def _expiry_status(expiry_date: str | None, *, today: date, near_expiry_days: int) -> str:
    if not expiry_date:
        return "usable"
    expiry = date.fromisoformat(expiry_date)
    if expiry < today:
        return "expired"
    if expiry <= today + timedelta(days=near_expiry_days):
        return "near_expiry"
    return "usable"


def get_inventory_summary(
    db: sqlite3.Connection, *, low_stock_threshold: int, near_expiry_days: int
) -> dict:
    """Aggregate active batches into per-blood-group usable/expired/near-expiry totals.

    Only "active" batches count toward any total; an archived batch is
    excluded entirely (it's been administratively taken out of service, not
    merely expired). An expired batch is excluded from usableUnits but is
    still reflected in totalRecordedUnits and expiredUnits, so stock is
    never silently lost from the books, just correctly marked unusable.
    """
    today = date.today()

    groups = {
        bg: {
            "bloodGroup": bg,
            "totalRecordedUnits": 0,
            "usableUnits": 0,
            "expiredUnits": 0,
            "nearExpiryUnits": 0,
            "batchCount": 0,
        }
        for bg in BLOOD_GROUPS_ORDERED
    }

    rows = db.execute("SELECT * FROM blood_inventory WHERE status = 'active'").fetchall()
    for row in rows:
        group = groups[row["blood_group"]]
        quantity = row["quantity_units"]
        group["totalRecordedUnits"] += quantity
        group["batchCount"] += 1

        status = _expiry_status(row["expiry_date"], today=today, near_expiry_days=near_expiry_days)
        if status == "expired":
            group["expiredUnits"] += quantity
        else:
            group["usableUnits"] += quantity
            if status == "near_expiry":
                group["nearExpiryUnits"] += quantity

    for group in groups.values():
        group["lowStock"] = 0 < group["usableUnits"] < low_stock_threshold
        group["outOfStock"] = group["usableUnits"] == 0

    ordered_groups = [groups[bg] for bg in BLOOD_GROUPS_ORDERED]

    return {
        "groups": ordered_groups,
        "totals": {
            "totalRecordedUnits": sum(g["totalRecordedUnits"] for g in ordered_groups),
            "usableUnits": sum(g["usableUnits"] for g in ordered_groups),
            "expiredUnits": sum(g["expiredUnits"] for g in ordered_groups),
            "nearExpiryUnits": sum(g["nearExpiryUnits"] for g in ordered_groups),
        },
        "thresholds": {
            "lowStockThreshold": low_stock_threshold,
            "nearExpiryDays": near_expiry_days,
        },
        "lowStockGroups": [g["bloodGroup"] for g in ordered_groups if g["lowStock"]],
        "outOfStockGroups": [g["bloodGroup"] for g in ordered_groups if g["outOfStock"]],
    }


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
