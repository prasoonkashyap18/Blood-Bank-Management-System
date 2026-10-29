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
    if not set(fields).issubset(DONOR_EDITABLE_FIELDS):
        # A programming error, not user input: callers only ever pass keys
        # from their own whitelisted validation, never client-supplied keys
        # directly. Raised (not asserted) so this check still runs even if
        # the interpreter is started with -O, which strips assert statements.
        raise ValueError("attempted to update a non-whitelisted donor column")
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
    if not set(fields).issubset(INVENTORY_EDITABLE_FIELDS):
        # See the matching note in update_donor() above: raised rather than
        # asserted so this check isn't silently skipped under -O.
        raise ValueError("attempted to update a non-whitelisted inventory column")
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
# Blood requests
# ---------------------------------------------------------------------------

class InsufficientStockError(Exception):
    """Raised when a request can't be approved/fulfilled with current usable stock."""


def create_blood_request(
    db: sqlite3.Connection,
    *,
    user_id: int,
    requester_name: str,
    requester_contact: str,
    blood_group: str,
    quantity_units: int,
    location: str,
    urgency: str,
    notes: str | None = None,
) -> int:
    cursor = db.execute(
        """
        INSERT INTO blood_requests
            (user_id, requester_name, requester_contact, blood_group, quantity_units, location, urgency, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            requester_name.strip(),
            requester_contact.strip(),
            blood_group,
            quantity_units,
            location.strip(),
            urgency,
            (notes or "").strip() or None,
        ),
    )
    db.commit()
    return cursor.lastrowid


def get_request_by_id(db: sqlite3.Connection, request_id: int) -> dict | None:
    row = db.execute("SELECT * FROM blood_requests WHERE id = ?", (request_id,)).fetchone()
    return row_to_dict(row)


def list_requests(
    db: sqlite3.Connection,
    *,
    user_id: int | None = None,
    status: str | None = None,
    blood_group: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List/search requests. `user_id` set means "only this user's requests"
    (the owner view); leave it None for the admin, all-requests view."""
    clauses: list[str] = []
    params: list[Any] = []

    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if status:
        clauses.append("status = ?")
        params.append(status)
    if blood_group:
        clauses.append("blood_group = ?")
        params.append(blood_group)
    if q:
        clauses.append("requester_name LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(q)}%")
    if date_from:
        clauses.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        # created_at is a full ISO timestamp; make an inclusive end-of-day bound.
        clauses.append("created_at <= ?")
        params.append(f"{date_to}T23:59:59.999Z")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    total = db.execute(f"SELECT COUNT(*) AS n FROM blood_requests {where_sql}", params).fetchone()["n"]
    rows = db.execute(
        f"SELECT * FROM blood_requests {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()

    return [row_to_dict(row) for row in rows], total


def request_view(request: dict) -> dict:
    return {
        "id": request["id"],
        "userId": request["user_id"],
        "requesterName": request["requester_name"],
        "requesterContact": request["requester_contact"],
        "bloodGroup": request["blood_group"],
        "quantityUnits": request["quantity_units"],
        "location": request["location"],
        "urgency": request["urgency"],
        "status": request["status"],
        "notes": request["notes"],
        "rejectionReason": request["rejection_reason"],
        "decidedBy": request["decided_by"],
        "fulfilledAt": request["fulfilled_at"],
        "createdAt": request["created_at"],
        "updatedAt": request["updated_at"],
    }


def get_usable_stock_for_group(db: sqlite3.Connection, blood_group: str, *, today: date | None = None) -> int:
    """Sum of quantity across active, unexpired batches for one blood group."""
    today = (today or date.today()).isoformat()
    row = db.execute(
        """
        SELECT COALESCE(SUM(quantity_units), 0) AS total
        FROM blood_inventory
        WHERE blood_group = ? AND status = 'active' AND (expiry_date IS NULL OR expiry_date >= ?)
        """,
        (blood_group, today),
    ).fetchone()
    return row["total"]


def deduct_stock_for_request(
    db: sqlite3.Connection, blood_group: str, quantity_needed: int, *, today: date | None = None
) -> None:
    """Deduct quantity_needed units from active, unexpired batches of blood_group,
    earliest-expiry-first (so stock closest to expiring is used first).

    Raises InsufficientStockError and changes nothing if usable stock is too
    low. Does NOT commit: the caller is expected to update the request's
    status in the same transaction and commit (or roll back) both together.
    """
    today_iso = (today or date.today()).isoformat()
    batches = db.execute(
        """
        SELECT * FROM blood_inventory
        WHERE blood_group = ? AND status = 'active' AND (expiry_date IS NULL OR expiry_date >= ?)
        ORDER BY (expiry_date IS NULL), expiry_date ASC, id ASC
        """,
        (blood_group, today_iso),
    ).fetchall()

    available = sum(b["quantity_units"] for b in batches)
    if available < quantity_needed:
        raise InsufficientStockError(
            f"Only {available} usable unit(s) of {blood_group} available; {quantity_needed} requested."
        )

    remaining = quantity_needed
    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch["quantity_units"], remaining)
        if take <= 0:
            continue
        new_quantity = batch["quantity_units"] - take
        assert new_quantity >= 0  # guaranteed by take = min(...), kept as a defensive check
        db.execute(
            "UPDATE blood_inventory SET quantity_units = ?, updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (new_quantity, batch["id"]),
        )
        remaining -= take


def set_request_status(
    db: sqlite3.Connection,
    request_id: int,
    *,
    status: str,
    decided_by: int,
    rejection_reason: str | None = None,
    mark_fulfilled: bool = False,
    commit: bool = True,
) -> None:
    """Update a request's status. Does not commit when commit=False, so a
    caller performing a stock deduction in the same transaction can commit
    (or roll back) both changes together."""
    fulfilled_at_sql = ", fulfilled_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')" if mark_fulfilled else ""
    db.execute(
        f"""
        UPDATE blood_requests
        SET status = ?, decided_by = ?, rejection_reason = ?,
            updated_at = STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'){fulfilled_at_sql}
        WHERE id = ?
        """,
        (status, decided_by, rejection_reason, request_id),
    )
    if commit:
        db.commit()


def get_requests_status_breakdown(db: sqlite3.Connection, *, date_from: str | None = None, date_to: str | None = None) -> dict:
    clauses: list[str] = []
    params: list[Any] = []
    if date_from:
        clauses.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("created_at <= ?")
        params.append(f"{date_to}T23:59:59.999Z")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    rows = db.execute(
        f"SELECT status, COUNT(*) AS n, COALESCE(SUM(quantity_units), 0) AS units "
        f"FROM blood_requests {where_sql} GROUP BY status",
        params,
    ).fetchall()
    by_status = {row["status"]: {"count": row["n"], "units": row["units"]} for row in rows}
    for status in ("Pending", "Approved", "Fulfilled", "Rejected"):
        by_status.setdefault(status, {"count": 0, "units": 0})
    return by_status


# ---------------------------------------------------------------------------
# Donation reports (admin-wide; per-donor history lives in donors.py)
# ---------------------------------------------------------------------------

def list_donations_report(
    db: sqlite3.Connection, *, date_from: str | None = None, date_to: str | None = None, limit: int = 500
) -> list[dict]:
    clauses: list[str] = []
    params: list[Any] = []
    if date_from:
        clauses.append("d.donation_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("d.donation_date <= ?")
        params.append(date_to)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    rows = db.execute(
        f"""
        SELECT d.id, d.donor_id, dn.full_name AS donor_name, dn.blood_group,
               d.donation_date, d.quantity_units, d.created_at
        FROM donations d
        JOIN donors dn ON dn.id = d.donor_id
        {where_sql}
        ORDER BY d.donation_date DESC, d.id DESC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Admin summary counts (read-only; drives the admin dashboard)
# ---------------------------------------------------------------------------

def get_admin_summary(
    db: sqlite3.Connection, *, low_stock_threshold: int, near_expiry_days: int, recent_limit: int = 5
) -> dict:
    def count(table: str) -> int:
        return db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]

    status_breakdown = get_requests_status_breakdown(db)
    inventory_summary = get_inventory_summary(
        db, low_stock_threshold=low_stock_threshold, near_expiry_days=near_expiry_days
    )

    recent_rows = db.execute(
        "SELECT * FROM blood_requests ORDER BY id DESC LIMIT ?", (recent_limit,)
    ).fetchall()

    return {
        "totalUsers": count("users"),
        "totalDonors": count("donors"),
        "totalInventoryBatches": count("blood_inventory"),
        "totalRequests": count("blood_requests"),
        "pendingRequests": status_breakdown["Pending"]["count"],
        "approvedRequests": status_breakdown["Approved"]["count"],
        "fulfilledRequests": status_breakdown["Fulfilled"]["count"],
        "rejectedRequests": status_breakdown["Rejected"]["count"],
        "availableUnits": inventory_summary["totals"]["usableUnits"],
        "bloodGroupStock": inventory_summary["groups"],
        "lowStockGroups": inventory_summary["lowStockGroups"],
        "outOfStockGroups": inventory_summary["outOfStockGroups"],
        "nearExpiryUnits": inventory_summary["totals"]["nearExpiryUnits"],
        "recentRequests": [request_view(row_to_dict(row)) for row in recent_rows],
    }
