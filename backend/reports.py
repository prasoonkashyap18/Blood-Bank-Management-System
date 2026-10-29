"""Reporting endpoints: request/donation summaries and CSV exports.

All of these read across every user's/donor's records, so every endpoint
here is admin-only. The blood-inventory summary used by the reports page
is intentionally *not* duplicated here — it already exists, public and
tested, at GET /api/inventory/summary (backend/inventory.py), and the
reports page simply calls that directly.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from flask import Blueprint, Response, jsonify, request

from . import models
from .auth import admin_required
from .database import get_db
from .validators import BLOOD_GROUPS, REQUEST_STATUSES

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

REQUEST_REPORT_LIMIT = 1000
DONATION_REPORT_LIMIT = 1000


def _parse_date_filters() -> tuple[dict, dict]:
    """Validate the optional dateFrom/dateTo query params shared by every
    report endpoint. Returns (clean, errors)."""
    errors: dict[str, str] = {}
    clean: dict = {}

    for key in ("dateFrom", "dateTo"):
        raw = (request.args.get(key) or "").strip()
        if not raw:
            continue
        try:
            date.fromisoformat(raw)
        except ValueError:
            errors[key] = "Please provide a valid date (YYYY-MM-DD)."
        else:
            clean[key] = raw

    if "dateFrom" in clean and "dateTo" in clean and clean["dateFrom"] > clean["dateTo"]:
        errors["dateTo"] = "End date must be on or after the start date."

    return clean, errors


def _requests_report_data():
    """Shared by the JSON and CSV request-report endpoints. Returns
    (clean_filters, errors, rows, breakdown) or (clean_filters, errors, None, None) on error."""
    date_filters, errors = _parse_date_filters()

    status = (request.args.get("status") or "").strip() or None
    blood_group = (request.args.get("bloodGroup") or "").strip() or None
    if status and status not in REQUEST_STATUSES:
        errors["status"] = "Invalid status filter."
    if blood_group and blood_group not in BLOOD_GROUPS:
        errors["bloodGroup"] = "Invalid blood group filter."

    if errors:
        return date_filters, errors, None, None

    db = get_db()
    rows, _total = models.list_requests(
        db,
        status=status,
        blood_group=blood_group,
        date_from=date_filters.get("dateFrom"),
        date_to=date_filters.get("dateTo"),
        limit=REQUEST_REPORT_LIMIT,
        offset=0,
    )
    breakdown = models.get_requests_status_breakdown(
        db, date_from=date_filters.get("dateFrom"), date_to=date_filters.get("dateTo")
    )
    return date_filters, errors, rows, breakdown


@reports_bp.get("/requests")
@admin_required
def requests_report():
    date_filters, errors, rows, breakdown = _requests_report_data()
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    return jsonify(
        filters={**date_filters},
        statusBreakdown=breakdown,
        totalRequests=sum(s["count"] for s in breakdown.values()),
        requests=[models.request_view(r) for r in rows],
    )


@reports_bp.get("/requests/export")
@admin_required
def requests_report_export():
    _date_filters, errors, rows, _breakdown = _requests_report_data()
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Request ID", "Requester Name", "Requester Contact", "Blood Group", "Units",
         "Location", "Urgency", "Status", "Rejection Reason", "Created At", "Fulfilled At"]
    )
    for r in rows:
        writer.writerow(
            [r["id"], r["requester_name"], r["requester_contact"], r["blood_group"], r["quantity_units"],
             r["location"], r["urgency"], r["status"], r["rejection_reason"] or "", r["created_at"], r["fulfilled_at"] or ""]
        )

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=blood_requests_report.csv"},
    )


@reports_bp.get("/donations")
@admin_required
def donations_report():
    date_filters, errors = _parse_date_filters()
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    db = get_db()
    rows = models.list_donations_report(
        db, date_from=date_filters.get("dateFrom"), date_to=date_filters.get("dateTo"), limit=DONATION_REPORT_LIMIT
    )
    total_units = sum(r["quantity_units"] for r in rows)

    return jsonify(
        filters={**date_filters},
        totalDonations=len(rows),
        totalUnits=total_units,
        donations=[
            {
                "id": r["id"],
                "donorId": r["donor_id"],
                "donorName": r["donor_name"],
                "bloodGroup": r["blood_group"],
                "donationDate": r["donation_date"],
                "quantityUnits": r["quantity_units"],
            }
            for r in rows
        ],
    )


@reports_bp.get("/donations/export")
@admin_required
def donations_report_export():
    date_filters, errors = _parse_date_filters()
    if errors:
        return jsonify(error="Please correct the highlighted fields.", fields=errors), 400

    db = get_db()
    rows = models.list_donations_report(
        db, date_from=date_filters.get("dateFrom"), date_to=date_filters.get("dateTo"), limit=DONATION_REPORT_LIMIT
    )

    # Donor name and blood group only — never the donor's phone/email in a
    # bulk export, even though the requester is an admin who could otherwise
    # view an individual donor's contact details one at a time.
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Donation ID", "Donor ID", "Donor Name", "Blood Group", "Donation Date", "Units"])
    for r in rows:
        writer.writerow([r["id"], r["donor_id"], r["donor_name"], r["blood_group"], r["donation_date"], r["quantity_units"]])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=donations_report.csv"},
    )
