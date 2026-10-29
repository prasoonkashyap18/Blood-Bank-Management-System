"""Blood inventory endpoints: public summary + admin-only batch management.

GET /api/inventory/summary is public and read-only — just aggregated,
non-sensitive stock counts per blood group, which is normal information for
a blood bank's public site to show. Everything else here (raw batch
listing, creating, and editing) is restricted to administrators and
enforced with @admin_required on the server, independent of what the
frontend shows or hides.
"""

from __future__ import annotations

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from . import models
from .auth import admin_required
from .database import get_db
from .validators import BLOOD_GROUPS, INVENTORY_BATCH_STATUSES

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")

MAX_QUANTITY_UNITS = 100_000
MAX_NOTES_LENGTH = 500


def _thresholds() -> tuple[int, int]:
    return (
        current_app.config["INVENTORY_LOW_STOCK_THRESHOLD"],
        current_app.config["INVENTORY_NEAR_EXPIRY_DAYS"],
    )


@inventory_bp.get("/summary")
def summary():
    low_stock_threshold, near_expiry_days = _thresholds()
    data = models.get_inventory_summary(
        get_db(), low_stock_threshold=low_stock_threshold, near_expiry_days=near_expiry_days
    )
    return jsonify(summary=data)


@inventory_bp.get("")
@admin_required
def list_batches():
    blood_group = (request.args.get("bloodGroup") or "").strip() or None
    status = (request.args.get("status") or "").strip() or None

    if blood_group and blood_group not in BLOOD_GROUPS:
        return jsonify(error="Invalid blood group filter."), 400
    if status and status not in INVENTORY_BATCH_STATUSES:
        return jsonify(error="Invalid status filter."), 400

    _, near_expiry_days = _thresholds()
    batches = models.list_inventory_batches(get_db(), blood_group=blood_group, status=status)
    return jsonify(
        batches=[models.inventory_batch_view(b, near_expiry_days=near_expiry_days) for b in batches]
    )


@inventory_bp.get("/<int:batch_id>")
@admin_required
def get_batch(batch_id):
    batch = models.get_inventory_batch(get_db(), batch_id)
    if batch is None:
        return jsonify(error="Inventory batch not found."), 404
    _, near_expiry_days = _thresholds()
    return jsonify(batch=models.inventory_batch_view(batch, near_expiry_days=near_expiry_days))


def _parse_optional_date(data: dict, key: str, errors: dict) -> tuple[bool, str | None]:
    """Returns (was_present, value). value is None for "clear this date"."""
    if key not in data:
        return False, None
    raw = (data.get(key) or "").strip()
    if not raw:
        return True, None
    try:
        date.fromisoformat(raw)
    except ValueError:
        errors[key] = "Please enter a valid date (YYYY-MM-DD)."
        return True, None
    return True, raw


def _validate_batch_fields(data: dict, *, partial: bool) -> tuple[dict, dict]:
    """Validate individual fields only. Cross-field (date-range) checks happen
    in the route, which also knows any existing stored values for a PATCH."""
    errors: dict[str, str] = {}
    clean: dict = {}

    def present(key: str) -> bool:
        return key in data

    if not partial or present("bloodGroup"):
        blood_group = (data.get("bloodGroup") or "").strip()
        if blood_group not in BLOOD_GROUPS:
            errors["bloodGroup"] = "Please select a valid blood group."
        else:
            clean["blood_group"] = blood_group

    if not partial or present("quantityUnits"):
        raw_quantity = data.get("quantityUnits")
        min_allowed = 0 if partial else 1  # a correction may zero a batch out; creating one may not
        if not isinstance(raw_quantity, int) or isinstance(raw_quantity, bool):
            errors["quantityUnits"] = "Quantity must be a whole number."
        elif raw_quantity < min_allowed or raw_quantity > MAX_QUANTITY_UNITS:
            errors["quantityUnits"] = (
                f"Quantity must be between {min_allowed} and {MAX_QUANTITY_UNITS} units."
            )
        else:
            clean["quantity_units"] = raw_quantity

    collected_present, collected_value = _parse_optional_date(data, "collectedDate", errors)
    if collected_present:
        clean["collected_date"] = collected_value

    expiry_present, expiry_value = _parse_optional_date(data, "expiryDate", errors)
    if expiry_present:
        clean["expiry_date"] = expiry_value

    if present("notes"):
        notes = (data.get("notes") or "").strip()
        if len(notes) > MAX_NOTES_LENGTH:
            errors["notes"] = f"Notes must be at most {MAX_NOTES_LENGTH} characters."
        else:
            clean["notes"] = notes or None

    if partial and present("status"):
        status = (data.get("status") or "").strip()
        if status not in INVENTORY_BATCH_STATUSES:
            errors["status"] = "Invalid batch status."
        else:
            clean["status"] = status

    return clean, errors


def _check_date_range(clean: dict, errors: dict, *, existing_batch: dict | None) -> None:
    """Reject an expiry date on or before the collection date, using whichever
    side of the pair wasn't touched by this request (if any) from the
    existing stored batch."""
    collected = clean["collected_date"] if "collected_date" in clean else (
        existing_batch["collected_date"] if existing_batch else None
    )
    expiry = clean["expiry_date"] if "expiry_date" in clean else (
        existing_batch["expiry_date"] if existing_batch else None
    )
    if collected and expiry and expiry <= collected:
        errors.setdefault("expiryDate", "Expiry date must be after the collection date.")


@inventory_bp.post("")
@admin_required
def create_batch():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    clean, errors = _validate_batch_fields(data, partial=False)
    _check_date_range(clean, errors, existing_batch=None)
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    db = get_db()
    batch_id = models.create_inventory_batch(
        db,
        blood_group=clean["blood_group"],
        quantity_units=clean["quantity_units"],
        collected_date=clean.get("collected_date"),
        expiry_date=clean.get("expiry_date"),
        notes=clean.get("notes"),
    )
    batch = models.get_inventory_batch(db, batch_id)
    _, near_expiry_days = _thresholds()
    return jsonify(batch=models.inventory_batch_view(batch, near_expiry_days=near_expiry_days)), 201


@inventory_bp.patch("/<int:batch_id>")
@admin_required
def update_batch(batch_id):
    db = get_db()
    batch = models.get_inventory_batch(db, batch_id)
    if batch is None:
        return jsonify(error="Inventory batch not found."), 404

    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON."), 400

    clean, errors = _validate_batch_fields(data, partial=True)
    _check_date_range(clean, errors, existing_batch=batch)

    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400
    if not clean:
        return jsonify(error="No valid fields to update."), 400

    models.update_inventory_batch(db, batch_id, clean)
    batch = models.get_inventory_batch(db, batch_id)
    _, near_expiry_days = _thresholds()
    return jsonify(batch=models.inventory_batch_view(batch, near_expiry_days=near_expiry_days))
