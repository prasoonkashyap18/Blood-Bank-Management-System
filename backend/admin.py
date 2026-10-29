"""Administrator-only endpoints: the real-data admin dashboard summary."""

from flask import Blueprint, current_app, jsonify

from . import models
from .auth import admin_required
from .database import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/summary")
@admin_required
def summary():
    summary_data = models.get_admin_summary(
        get_db(),
        low_stock_threshold=current_app.config["INVENTORY_LOW_STOCK_THRESHOLD"],
        near_expiry_days=current_app.config["INVENTORY_NEAR_EXPIRY_DAYS"],
    )
    return jsonify(summary=summary_data)
