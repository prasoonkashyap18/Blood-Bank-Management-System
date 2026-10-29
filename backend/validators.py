"""Validation constants shared by auth, donors, and inventory endpoints.

Centralized here so the set of supported blood groups (and the email/phone
patterns) are defined exactly once and stay consistent across the backend,
instead of being copy-pasted into every blueprint.
"""

import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{7,15}$")
BLOOD_GROUPS_ORDERED = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
BLOOD_GROUPS = set(BLOOD_GROUPS_ORDERED)
DONOR_STATUSES = {"pending", "approved", "rejected"}
INVENTORY_BATCH_STATUSES = {"active", "archived"}
