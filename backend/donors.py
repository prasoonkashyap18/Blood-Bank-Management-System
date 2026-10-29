"""Donor directory, profile, and donation-history endpoints.

Public (unauthenticated) requests can search/browse the directory but only
ever see non-contact fields (see models.donor_public_view). Phone/email and
other private fields are only included for the donor's own account or an
administrator (models.donor_private_view) — enforced here, server-side, on
every request; nothing relies on the frontend hiding anything.
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request

from . import models
from .auth import current_user, login_required
from .database import get_db
from .validators import BLOOD_GROUPS, DONOR_STATUSES, EMAIL_RE, PHONE_RE

donors_bp = Blueprint("donors", __name__, url_prefix="/api/donors")

MAX_NAME_LENGTH = 120
MAX_CITY_LENGTH = 80
MAX_PHONE_LENGTH = 20
MAX_EMAIL_LENGTH = 254

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _can_view_private(donor: dict, user: dict | None) -> bool:
    if user is None:
        return False
    if user["role"] == "admin":
        return True
    return donor["user_id"] == user["id"]


def _serialize(donor: dict, user: dict | None) -> dict:
    if _can_view_private(donor, user):
        return models.donor_private_view(donor)
    return models.donor_public_view(donor)


def _parse_pagination() -> tuple[int, int]:
    try:
        limit = int(request.args.get("limit", DEFAULT_PAGE_SIZE))
    except ValueError:
        limit = DEFAULT_PAGE_SIZE
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = max(0, offset)
    return limit, offset


@donors_bp.get("")
def list_donors():
    db = get_db()
    user = current_user()

    q = (request.args.get("q") or "").strip() or None
    blood_group = (request.args.get("bloodGroup") or "").strip() or None
    city = (request.args.get("city") or "").strip() or None
    status = (request.args.get("status") or "").strip() or None
    email = (request.args.get("email") or "").strip() or None
    phone = (request.args.get("phone") or "").strip() or None

    if blood_group and blood_group not in BLOOD_GROUPS:
        return jsonify(error="Invalid blood group filter."), 400
    if status and status not in DONOR_STATUSES:
        return jsonify(error="Invalid status filter."), 400

    limit, offset = _parse_pagination()

    donors, total = models.list_donors(
        db,
        q=q,
        blood_group=blood_group,
        city=city,
        status=status,
        email=email,
        phone=phone,
        limit=limit,
        offset=offset,
    )

    return jsonify(
        donors=[_serialize(donor, user) for donor in donors],
        total=total,
        limit=limit,
        offset=offset,
    )


@donors_bp.get("/<int:donor_id>")
def get_donor(donor_id):
    donor = models.get_donor_by_id(get_db(), donor_id)
    if donor is None:
        return jsonify(error="Donor not found."), 404
    return jsonify(donor=_serialize(donor, current_user()))


def _validate_donor_fields(data: dict, *, partial: bool) -> tuple[dict, dict]:
    """Validate donor fields from client JSON, returning (clean_db_fields, errors).

    When partial=True (PATCH), a field is only validated if the client
    actually included it; when partial=False (POST/create), every required
    field must be present and valid.
    """
    errors: dict[str, str] = {}
    clean: dict = {}

    def present(key: str) -> bool:
        return key in data

    if not partial or present("fullName"):
        full_name = (data.get("fullName") or "").strip()
        if len(full_name) < 2:
            errors["fullName"] = "Please enter a full name."
        elif len(full_name) > MAX_NAME_LENGTH:
            errors["fullName"] = f"Full name must be at most {MAX_NAME_LENGTH} characters."
        else:
            clean["full_name"] = full_name

    if not partial or present("bloodGroup"):
        blood_group = (data.get("bloodGroup") or "").strip()
        if blood_group not in BLOOD_GROUPS:
            errors["bloodGroup"] = "Please select a valid blood group."
        else:
            clean["blood_group"] = blood_group

    if not partial or present("phone"):
        phone = (data.get("phone") or "").strip()
        if not PHONE_RE.match(phone) or len(phone) > MAX_PHONE_LENGTH:
            errors["phone"] = "Please enter a valid phone number (7-15 digits)."
        else:
            clean["phone"] = phone

    if not partial or present("city"):
        city = (data.get("city") or "").strip()
        if not city:
            errors["city"] = "Please enter a city or location."
        elif len(city) > MAX_CITY_LENGTH:
            errors["city"] = f"City must be at most {MAX_CITY_LENGTH} characters."
        else:
            clean["city"] = city

    if present("email"):
        email = (data.get("email") or "").strip()
        if email:
            if not EMAIL_RE.match(email) or len(email) > MAX_EMAIL_LENGTH:
                errors["email"] = "Please enter a valid email address."
            else:
                clean["email"] = email
        else:
            clean["email"] = None

    if present("lastDonationDate"):
        raw = (data.get("lastDonationDate") or "").strip()
        if raw:
            try:
                parsed = date.fromisoformat(raw)
            except ValueError:
                errors["lastDonationDate"] = "Please enter a valid date (YYYY-MM-DD)."
            else:
                if parsed > date.today():
                    errors["lastDonationDate"] = "Last donation date cannot be in the future."
                else:
                    clean["last_donation_date"] = raw
        else:
            clean["last_donation_date"] = None

    return clean, errors


@donors_bp.post("")
@login_required
def create_donor():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    user = current_user()
    db = get_db()

    # Step 2 already creates a donor profile automatically on registration,
    # so this only ever completes a *missing* profile — one donor per user.
    existing = models.get_donor_by_user_id(db, user["id"])
    if existing is not None:
        return (
            jsonify(
                error="You already have a donor profile. Use PATCH to update it.",
                donorId=existing["id"],
            ),
            409,
        )

    clean, errors = _validate_donor_fields(data, partial=False)
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    donor_id = models.create_donor(
        db,
        user_id=user["id"],
        full_name=clean["full_name"],
        blood_group=clean["blood_group"],
        phone=clean["phone"],
        city=clean["city"],
        last_donation_date=clean.get("last_donation_date"),
        consent_given=bool(data.get("consent", True)),
        email=clean.get("email"),
    )
    donor = models.get_donor_by_id(db, donor_id)
    return jsonify(donor=models.donor_private_view(donor)), 201


@donors_bp.patch("/<int:donor_id>")
@login_required
def update_donor(donor_id):
    db = get_db()
    donor = models.get_donor_by_id(db, donor_id)
    if donor is None:
        return jsonify(error="Donor not found."), 404

    user = current_user()
    is_admin = user["role"] == "admin"
    is_owner = donor["user_id"] == user["id"]
    if not (is_admin or is_owner):
        # Changing the donor id in the URL never grants access to someone
        # else's record: ownership is checked against the database row, not
        # anything the client claims.
        return jsonify(error="You do not have permission to edit this donor record."), 403

    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    clean, errors = _validate_donor_fields(data, partial=True)

    if "status" in data:
        if not is_admin:
            errors["status"] = "Only an administrator can change donor status."
        else:
            status = (data.get("status") or "").strip()
            if status not in DONOR_STATUSES:
                errors["status"] = "Invalid donor status."
            else:
                clean["status"] = status

    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400
    if not clean:
        return jsonify(error="No valid fields to update."), 400

    models.update_donor(db, donor_id, clean)
    donor = models.get_donor_by_id(db, donor_id)
    return jsonify(donor=_serialize(donor, user))


@donors_bp.get("/<int:donor_id>/donations")
@login_required
def donor_donations(donor_id):
    db = get_db()
    donor = models.get_donor_by_id(db, donor_id)
    if donor is None:
        return jsonify(error="Donor not found."), 404

    user = current_user()
    if not _can_view_private(donor, user):
        return (
            jsonify(error="You do not have permission to view this donor's donation history."),
            403,
        )

    donations = models.list_donations_for_donor(db, donor_id)
    return jsonify(donations=[models.donation_view(d) for d in donations])
