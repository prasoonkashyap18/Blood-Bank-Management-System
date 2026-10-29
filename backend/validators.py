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

URGENCY_LEVELS = {"Critical", "High", "Medium", "Low"}
REQUEST_STATUSES = {"Pending", "Approved", "Fulfilled", "Rejected"}

# Which statuses a blood request may move to from its current one. Anything
# not listed as a key (or not in the value set for a given key) is rejected
# by backend/requests.py regardless of who is asking — this is the single
# source of truth for valid request-status transitions.
REQUEST_TRANSITIONS = {
    "Pending": {"Approved", "Rejected"},
    "Approved": {"Fulfilled", "Rejected"},
    "Rejected": set(),
    "Fulfilled": set(),
}
