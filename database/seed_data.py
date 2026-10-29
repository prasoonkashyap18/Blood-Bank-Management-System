"""Insert fictional demonstration data: donors, inventory, requests, donations.

Idempotent: each table is only seeded if it is currently empty, so running
this script again after the app has been used will never duplicate rows or
touch real records that were created through the application.

Inventory expiry/collection dates are computed relative to the date the
script is run (see _relative_date below) rather than hardcoded, so the
low-stock, near-expiry, and expired demonstration batches stay meaningful
no matter when this is run - they don't go stale the way a fixed calendar
date would.

Usage (from the project root, after init_db.py):
    python database/seed_data.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import Config  # noqa: E402
from backend.database import init_db  # noqa: E402

import sqlite3  # noqa: E402

# All data below is fictional demonstration data for development only.


def _relative_date(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


# (full_name, blood_group, phone, city, last_donation_date, status)
DONORS = [
    ("Aarav Sharma", "O+", "98XXXXX101", "Pune", "2026-07-12", "approved"),
    ("Priya Nair", "A+", "98XXXXX102", "Mumbai", "2026-05-02", "approved"),
    ("Rohan Mehta", "B+", "98XXXXX103", "Pune", "2026-08-20", "approved"),
    ("Sneha Iyer", "AB+", "98XXXXX104", "Bengaluru", "2026-03-15", "approved"),
    ("Kabir Khan", "O-", "98XXXXX105", "Delhi", "2026-09-01", "approved"),
    ("Ishita Verma", "A-", "98XXXXX106", "Pune", "2026-06-18", "pending"),
    ("Dev Patel", "B-", "98XXXXX107", "Ahmedabad", "2026-01-29", "pending"),
    ("Ananya Reddy", "AB-", "98XXXXX108", "Hyderabad", "2026-04-22", "rejected"),
]

REQUESTS = [
    ("City Care Hospital", "contact@citycare.example", "O-", 4, "Pune", "Critical", "Pending"),
    ("Riya Deshmukh", "riya.deshmukh@example.com", "A+", 2, "Mumbai", "High", "Approved"),
    ("Sunrise Medical Center", "contact@sunrisemed.example", "B+", 6, "Delhi", "Medium", "Fulfilled"),
    ("Aditya Kulkarni", "aditya.kulkarni@example.com", "AB-", 1, "Hyderabad", "High", "Rejected"),
]

# (donor index into DONORS, donation_date, quantity_units)
DONATIONS = [
    (0, "2026-07-12", 1),
    (0, "2026-01-05", 1),
    (1, "2026-05-02", 1),
    (2, "2026-08-20", 1),
    (4, "2026-09-01", 1),
]


def _build_inventory():
    """One healthy baseline batch per blood group, plus explicit low-stock,
    near-expiry, and expired examples (including two groups with more than
    one batch, so usable stock is visibly a sum across batches, not just
    the first batch's quantity)."""
    baseline = [
        # (blood_group, quantity, collected N days ago, expires N days from now)
        ("A+", 42, -28, 60),
        ("A-", 9, -20, 65),    # low stock (below the default threshold of 10)
        ("B+", 35, -24, 58),
        ("B-", 6, -15, 70),    # low stock
        ("AB+", 18, -30, 55),
        ("AB-", 4, -10, 62),   # low stock
        ("O+", 51, -32, 59),
        ("O-", 7, -18, 63),    # low stock
    ]
    extra = [
        # A second O+ batch that's about to expire, and a second A+ batch
        # that already has, to exercise multi-batch aggregation + alerts.
        ("O+", 12, -60, 3),     # near expiry (within the default 7-day window)
        ("A+", 8, -90, -10),    # expired: must be excluded from usable stock
    ]
    rows = []
    for blood_group, quantity, collected_offset, expiry_offset in baseline + extra:
        rows.append(
            (blood_group, quantity, _relative_date(collected_offset), _relative_date(expiry_offset))
        )
    return rows


def seed(conn: sqlite3.Connection) -> None:
    donor_count = conn.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
    if donor_count == 0:
        conn.executemany(
            """
            INSERT INTO donors (full_name, blood_group, phone, city, last_donation_date, consent_given, status)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            DONORS,
        )
        print(f"Seeded {len(DONORS)} fictional donors (varied statuses).")
    else:
        print(f"Donors table already has {donor_count} row(s); skipping donor seed.")

    inventory_count = conn.execute("SELECT COUNT(*) AS n FROM blood_inventory").fetchone()["n"]
    if inventory_count == 0:
        inventory_rows = _build_inventory()
        conn.executemany(
            """
            INSERT INTO blood_inventory (blood_group, quantity_units, collected_date, expiry_date)
            VALUES (?, ?, ?, ?)
            """,
            inventory_rows,
        )
        print(
            f"Seeded {len(inventory_rows)} fictional inventory batches "
            "(includes low-stock, near-expiry, and expired examples)."
        )
    else:
        print(f"Inventory table already has {inventory_count} row(s); skipping inventory seed.")

    request_count = conn.execute("SELECT COUNT(*) AS n FROM blood_requests").fetchone()["n"]
    if request_count == 0:
        conn.executemany(
            """
            INSERT INTO blood_requests
                (requester_name, requester_contact, blood_group, quantity_units, location, urgency, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            REQUESTS,
        )
        print(f"Seeded {len(REQUESTS)} fictional blood requests.")
    else:
        print(f"Requests table already has {request_count} row(s); skipping request seed.")

    donation_count = conn.execute("SELECT COUNT(*) AS n FROM donations").fetchone()["n"]
    if donation_count == 0 and donor_count == 0:
        # Donor ids are only predictable right after a fresh donor seed in
        # this same run, since AUTOINCREMENT ids depend on insertion order.
        donor_rows = conn.execute("SELECT id FROM donors ORDER BY id").fetchall()
        donor_ids = [row["id"] for row in donor_rows]
        rows = [
            (donor_ids[idx], donation_date, quantity)
            for idx, donation_date, quantity in DONATIONS
            if idx < len(donor_ids)
        ]
        conn.executemany(
            "INSERT INTO donations (donor_id, donation_date, quantity_units) VALUES (?, ?, ?)",
            rows,
        )
        print(f"Seeded {len(rows)} fictional donation records.")
    else:
        print(f"Donations table already has {donation_count} row(s); skipping donation seed.")

    conn.commit()


if __name__ == "__main__":
    init_db(Config.DATABASE_PATH)
    connection = sqlite3.connect(str(Config.DATABASE_PATH))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        seed(connection)
    finally:
        connection.close()
    print("Seed data is fictional and for demonstration purposes only.")
