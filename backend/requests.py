"""Blood request endpoints: submission, viewing, search/filter, and
admin status transitions (Approve / Reject / Fulfilled) wired to inventory.

Named requests.py for the blood_requests domain — unrelated to the
third-party "requests" HTTP library, which this module does not import.
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request

from . import models
from .auth import admin_required, current_user, login_required
from .database import get_db
from .validators import BLOOD_GROUPS, REQUEST_STATUSES, REQUEST_TRANSITIONS, URGENCY_LEVELS

requests_bp = Blueprint("requests", __name__, url_prefix="/api/requests")

MAX_NAME_LENGTH = 120
MAX_CONTACT_LENGTH = 120
MAX_LOCATION_LENGTH = 120
MAX_NOTES_LENGTH = 500
MAX_REJECTION_REASON_LENGTH = 500
MAX_QUANTITY_UNITS = 20  # matches the existing frontend form's cap
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _parse_pagination() -> tuple[int, int]:
    try:
        limit = int(request.args.get("limit", DEFAULT_PAGE_SIZE))
    except ValueError:
        limit = DEFAULT_PAGE_SIZE
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        offset = 0
    return max(1, min(limit, MAX_PAGE_SIZE)), max(0, offset)


def _validate_new_request(data: dict) -> tuple[dict, dict]:
    errors: dict[str, str] = {}
    clean: dict = {}

    requester_name = (data.get("requesterName") or "").strip()
    if not requester_name:
        errors["requesterName"] = "Please enter a requester name."
    elif len(requester_name) > MAX_NAME_LENGTH:
        errors["requesterName"] = f"Requester name must be at most {MAX_NAME_LENGTH} characters."
    else:
        clean["requester_name"] = requester_name

    requester_contact = (data.get("requesterContact") or "").strip()
    if not requester_contact:
        errors["requesterContact"] = "Please enter a contact email or phone number."
    elif len(requester_contact) > MAX_CONTACT_LENGTH:
        errors["requesterContact"] = f"Contact must be at most {MAX_CONTACT_LENGTH} characters."
    else:
        clean["requester_contact"] = requester_contact

    blood_group = (data.get("bloodGroup") or "").strip()
    if blood_group not in BLOOD_GROUPS:
        errors["bloodGroup"] = "Please select a valid blood group."
    else:
        clean["blood_group"] = blood_group

    quantity = data.get("quantityUnits")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or not (1 <= quantity <= MAX_QUANTITY_UNITS):
        errors["quantityUnits"] = f"Quantity must be a whole number from 1 to {MAX_QUANTITY_UNITS}."
    else:
        clean["quantity_units"] = quantity

    location = (data.get("location") or "").strip()
    if not location:
        errors["location"] = "Please enter a city or location."
    elif len(location) > MAX_LOCATION_LENGTH:
        errors["location"] = f"Location must be at most {MAX_LOCATION_LENGTH} characters."
    else:
        clean["location"] = location

    urgency = (data.get("urgency") or "").strip()
    if urgency not in URGENCY_LEVELS:
        errors["urgency"] = "Please select a valid urgency level."
    else:
        clean["urgency"] = urgency

    notes = (data.get("notes") or "").strip()
    if len(notes) > MAX_NOTES_LENGTH:
        errors["notes"] = f"Notes must be at most {MAX_NOTES_LENGTH} characters."
    else:
        clean["notes"] = notes or None

    return clean, errors


@requests_bp.post("")
@login_required
def create_request():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    clean, errors = _validate_new_request(data)
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    db = get_db()
    user = current_user()
    request_id = models.create_blood_request(db, user_id=user["id"], **clean)
    created = models.get_request_by_id(db, request_id)
    return jsonify(request=models.request_view(created)), 201


@requests_bp.get("")
@login_required
def list_requests():
    db = get_db()
    user = current_user()
    is_admin = user["role"] == "admin"

    status = (request.args.get("status") or "").strip() or None
    blood_group = (request.args.get("bloodGroup") or "").strip() or None
    q = (request.args.get("q") or "").strip() or None
    date_from = (request.args.get("dateFrom") or "").strip() or None
    date_to = (request.args.get("dateTo") or "").strip() or None

    if status and status not in REQUEST_STATUSES:
        return jsonify(error="Invalid status filter."), 400
    if blood_group and blood_group not in BLOOD_GROUPS:
        return jsonify(error="Invalid blood group filter."), 400

    limit, offset = _parse_pagination()

    # A regular user only ever sees their own requests, regardless of what
    # filters they pass — ownership is enforced here, not left to the UI to
    # simply not ask for someone else's data.
    owner_filter = None if is_admin else user["id"]

    rows, total = models.list_requests(
        db,
        user_id=owner_filter,
        status=status,
        blood_group=blood_group,
        q=q if is_admin else None,  # name search only makes sense across all requests (admin view)
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    return jsonify(
        requests=[models.request_view(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@requests_bp.get("/<int:request_id>")
@login_required
def get_request(request_id):
    db = get_db()
    req = models.get_request_by_id(db, request_id)
    if req is None:
        return jsonify(error="Request not found."), 404

    user = current_user()
    if user["role"] != "admin" and req["user_id"] != user["id"]:
        return jsonify(error="You do not have permission to view this request."), 403

    return jsonify(request=models.request_view(req))


@requests_bp.patch("/<int:request_id>")
@admin_required
def update_request_status(request_id):
    db = get_db()
    req = models.get_request_by_id(db, request_id)
    if req is None:
        return jsonify(error="Request not found."), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    new_status = (data.get("status") or "").strip()
    if new_status not in REQUEST_STATUSES:
        return jsonify(error="Please correct the highlighted fields.", fields={"status": "Invalid status."}), 400

    current_status = req["status"]
    allowed_next = REQUEST_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_next:
        return (
            jsonify(
                error=f"Cannot change status from {current_status} to {new_status}.",
                fields={"status": f"'{current_status}' requests can only move to: {', '.join(sorted(allowed_next)) or 'nothing (final state)'}."},
            ),
            409,
        )

    admin_user = current_user()

    if new_status == "Rejected":
        reason = (data.get("rejectionReason") or "").strip()
        if not reason:
            return (
                jsonify(
                    error="Please correct the highlighted fields.",
                    fields={"rejectionReason": "A reason is required when rejecting a request."},
                ),
                400,
            )
        if len(reason) > MAX_REJECTION_REASON_LENGTH:
            return (
                jsonify(
                    error="Please correct the highlighted fields.",
                    fields={"rejectionReason": f"Reason must be at most {MAX_REJECTION_REASON_LENGTH} characters."},
                ),
                400,
            )
        models.set_request_status(db, request_id, status="Rejected", decided_by=admin_user["id"], rejection_reason=reason)
        updated = models.get_request_by_id(db, request_id)
        return jsonify(request=models.request_view(updated))

    if new_status == "Approved":
        # Not a stock deduction — just an administrative check so an admin
        # doesn't approve a request that can't realistically be fulfilled.
        available = models.get_usable_stock_for_group(db, req["blood_group"])
        if available < req["quantity_units"]:
            return (
                jsonify(
                    error=(
                        f"Only {available} usable unit(s) of {req['blood_group']} are currently available; "
                        f"this request needs {req['quantity_units']}."
                    )
                ),
                409,
            )
        models.set_request_status(db, request_id, status="Approved", decided_by=admin_user["id"])
        updated = models.get_request_by_id(db, request_id)
        return jsonify(request=models.request_view(updated))

    if new_status == "Fulfilled":
        # Deduct stock and mark the request fulfilled in a single
        # transaction: if the deduction fails, nothing is committed, so the
        # request stays "Approved" and inventory is untouched. Re-checking
        # req["status"] == "Approved" (already guaranteed by the transition
        # map above, since only Approved -> Fulfilled is allowed) also means
        # a repeated "fulfill" click on an already-fulfilled request is
        # rejected by the transition check before this code ever runs again.
        try:
            models.deduct_stock_for_request(db, req["blood_group"], req["quantity_units"])
            models.set_request_status(
                db, request_id, status="Fulfilled", decided_by=admin_user["id"], mark_fulfilled=True, commit=False
            )
            db.commit()
        except models.InsufficientStockError as exc:
            db.rollback()
            return jsonify(error=str(exc)), 409
        except Exception:
            db.rollback()
            raise
        updated = models.get_request_by_id(db, request_id)
        return jsonify(request=models.request_view(updated))

    # REQUEST_STATUSES / REQUEST_TRANSITIONS only ever name these three as a
    # reachable "next" status, so this is unreachable in practice.
    return jsonify(error="Unsupported status transition."), 400
