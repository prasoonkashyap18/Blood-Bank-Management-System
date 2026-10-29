"""Minimal administrator-only endpoints.

Step 2 only needs enough here to prove role-based authorization end to end;
the real admin-dashboard data wiring (editing inventory, approving donors,
processing requests) belongs to Steps 3 and 4.
"""

from flask import Blueprint, jsonify

from . import models
from .auth import admin_required
from .database import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/summary")
@admin_required
def summary():
    return jsonify(summary=models.get_admin_summary(get_db()))
