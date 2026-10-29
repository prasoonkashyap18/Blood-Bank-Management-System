"""Insert fictional demonstration data: donors, inventory, requests, donations.

Idempotent: each table is only seeded if it is currently empty, so running
this script again after the app has been used will never duplicate rows or
touch real records that were created through the application.

Usage (from the project root, after init_db.py):
    python database/seed_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import Config  # noqa: E402
from backend.database import init_db  # noqa: E402

import sqlite3  # noqa: E402

# All data below is fictional demonstration data for development only.

DONORS = [
    ("Aarav Sharma", "O+", "98XXXXX101", "Pune", "2026-07-12"),
    ("Priya Nair", "A+", "98XXXXX102", "Mumbai", "2026-05-02"),
    ("Rohan Mehta", "B+", "98XXXXX103", "Pune", "2026-08-20"),
    ("Sneha Iyer", "AB+", "98XXXXX104", "Bengaluru", "2026-03-15"),
    ("Kabir Khan", "O-", "98XXXXX105", "Delhi", "2026-09-01"),
    ("Ishita Verma", "A-", "98XXXXX106", "Pune", "2026-06-18"),
    ("Dev Patel", "B-", "98XXXXX107", "Ahmedabad", "2026-01-29"),
    ("Ananya Reddy", "AB-", "98XXXXX108", "Hyderabad", "2026-04-22"),
]

INVENTORY = [
    ("A+", 42, "2026-10-01", "2026-12-01"),
    ("A-", 9, "2026-09-20", "2026-11-20"),
    ("B+", 35, "2026-10-05", "2026-12-05"),
    ("B-", 6, "2026-09-15", "2026-11-15"),
    ("AB+", 18, "2026-10-10", "2026-12-10"),
    ("AB-", 4, "2026-09-25", "2026-11-25"),
    ("O+", 51, "2026-10-12", "2026-12-12"),
    ("O-", 7, "2026-09-18", "2026-11-18"),
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
    (1, "2026-05-02", 1),
    (2, "2026-08-20", 1),
]


def seed(conn: sqlite3.Connection) -> None:
    donor_count = conn.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
    if donor_count == 0:
        conn.executemany(
            """
            INSERT INTO donors (full_name, blood_group, phone, city, last_donation_date, consent_given, status)
            VALUES (?, ?, ?, ?, ?, 1, 'approved')
            """,
            DONORS,
        )
        print(f"Seeded {len(DONORS)} fictional donors.")
    else:
        print(f"Donors table already has {donor_count} row(s); skipping donor seed.")

    inventory_count = conn.execute("SELECT COUNT(*) AS n FROM blood_inventory").fetchone()["n"]
    if inventory_count == 0:
        conn.executemany(
            """
            INSERT INTO blood_inventory (blood_group, quantity_units, collected_date, expiry_date)
            VALUES (?, ?, ?, ?)
            """,
            INVENTORY,
        )
        print(f"Seeded {len(INVENTORY)} fictional inventory batches.")
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
