"""Flask application factory and entry point.

Run locally with:
    python -m flask --app backend.app run
"""

from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_session import Session
from flask_wtf import CSRFProtect

from . import database
from .admin import admin_bp
from .auth import auth_bp
from .config import Config
from .donors import donors_bp
from .inventory import inventory_bp
from .reports import reports_bp
from .requests import requests_bp

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)

    database.init_app(app)
    Session(app)
    CSRFProtect(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(donors_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(reports_bp)

    _register_frontend_routes(app)
    _register_error_handlers(app)

    return app


def _register_frontend_routes(app: Flask) -> None:
    """Serve the existing Step 1 static frontend from the project root."""

    @app.get("/")
    @app.get("/index.html")
    def serve_index():
        return send_from_directory(PROJECT_ROOT, "index.html")

    @app.get("/pages/<path:filename>")
    def serve_pages(filename):
        return send_from_directory(PROJECT_ROOT / "pages", filename)

    @app.get("/assets/<path:filename>")
    def serve_assets(filename):
        return send_from_directory(PROJECT_ROOT / "assets", filename)


def _register_error_handlers(app: Flask) -> None:
    """Return consistent JSON errors for API routes without leaking internals."""

    @app.errorhandler(400)
    def bad_request(_err):
        return jsonify(error="Bad request."), 400

    @app.errorhandler(401)
    def unauthorized(_err):
        return jsonify(error="Authentication required."), 401

    @app.errorhandler(403)
    def forbidden(_err):
        return jsonify(error="You do not have permission to do that."), 403

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="Not found."), 404

    @app.errorhandler(500)
    def server_error(err):
        app.logger.exception(err)
        return jsonify(error="An unexpected error occurred."), 500


if __name__ == "__main__":
    create_app().run(debug=True)
