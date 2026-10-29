"""Authentication endpoints and role-based authorization helpers."""

from __future__ import annotations

import re
from datetime import date
from functools import wraps

from flask import Blueprint, jsonify, request, session
from flask_wtf.csrf import generate_csrf
from werkzeug.security import check_password_hash, generate_password_hash

from . import models
from .database import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{7,15}$")
BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


# ---------------------------------------------------------------------------
# Session / authorization helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(error="Authentication required."), 401
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify(error="Authentication required."), 401
        db = get_db()
        user = models.get_user_by_id(db, user_id)
        # The role is re-read from the database on every request rather than
        # trusted from the session, so a role change takes effect immediately
        # and the frontend can never grant itself admin access.
        if not user or user["role"] != "admin" or not user["is_active"]:
            return jsonify(error="Administrator access required."), 403
        return view(*args, **kwargs)

    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return models.get_user_by_id(get_db(), user_id)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_registration(data: dict) -> dict[str, str]:
    errors: dict[str, str] = {}

    full_name = (data.get("fullName") or "").strip()
    if len(full_name) < 2:
        errors["fullName"] = "Please enter your full name."

    email = (data.get("email") or "").strip()
    if not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email address."

    phone = (data.get("phone") or "").strip()
    if not PHONE_RE.match(phone):
        errors["phone"] = "Please enter a valid phone number (7-15 digits)."

    blood_group = (data.get("bloodGroup") or "").strip()
    if blood_group not in BLOOD_GROUPS:
        errors["bloodGroup"] = "Please select a valid blood group."

    city = (data.get("city") or "").strip()
    if not city:
        errors["city"] = "Please enter your city or location."

    last_donation_date = (data.get("lastDonationDate") or "").strip() or None
    if last_donation_date:
        try:
            parsed = date.fromisoformat(last_donation_date)
            if parsed > date.today():
                errors["lastDonationDate"] = "Last donation date cannot be in the future."
        except ValueError:
            errors["lastDonationDate"] = "Please enter a valid date."

    password = data.get("password") or ""
    if len(password) < 6:
        errors["password"] = "Password must be at least 6 characters."

    confirm_password = data.get("confirmPassword") or ""
    if password and confirm_password and password != confirm_password:
        errors["confirmPassword"] = "Passwords do not match."

    if not data.get("consent"):
        errors["consent"] = "You must provide consent to register."

    return errors


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.get("/csrf-token")
def csrf_token():
    """Issue a CSRF token the frontend must echo back on state-changing requests."""
    return jsonify(csrfToken=generate_csrf())


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    errors = _validate_registration(data)
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    db = get_db()
    email = models.normalize_email(data["email"])

    if models.get_user_by_email(db, email) is not None:
        # Same message as any other validation error: we don't want to let
        # an attacker enumerate which emails already have accounts via a
        # different status code or wording.
        return (
            jsonify(
                error="Please correct the highlighted fields.",
                fields={"email": "An account with this email already exists."},
            ),
            409,
        )

    password_hash = generate_password_hash(data["password"])

    # Public registration always creates a regular 'user' account. Any
    # "role" field the client might send is ignored entirely below.
    user_id = models.create_user(
        db,
        full_name=data["fullName"].strip(),
        email=email,
        password_hash=password_hash,
        role="user",
    )

    models.create_donor(
        db,
        user_id=user_id,
        full_name=data["fullName"].strip(),
        blood_group=data["bloodGroup"].strip(),
        phone=data["phone"].strip(),
        city=data["city"].strip(),
        last_donation_date=(data.get("lastDonationDate") or "").strip() or None,
        consent_given=bool(data.get("consent")),
    )

    user = models.get_user_by_id(db, user_id)
    return jsonify(user=models.public_user_view(user)), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    generic_error = jsonify(error="Invalid email or password."), 401
    if not email or not password:
        return generic_error

    db = get_db()
    user = models.get_user_by_email(db, email)

    # Checking the hash even when no user was found keeps the response time
    # closer to constant, so a timing difference can't reveal whether the
    # account exists.
    hash_to_check = user["password_hash"] if user else generate_password_hash("placeholder")
    password_ok = check_password_hash(hash_to_check, password)

    if not user or not password_ok or not user["is_active"]:
        return generic_error

    session.clear()
    session["user_id"] = user["id"]
    session.permanent = bool(data.get("rememberMe"))

    return jsonify(user=models.public_user_view(user))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(message="Logged out.")


@auth_bp.get("/me")
def me():
    user = current_user()
    if user is None:
        return jsonify(error="Authentication required."), 401
    return jsonify(user=models.public_user_view(user))
