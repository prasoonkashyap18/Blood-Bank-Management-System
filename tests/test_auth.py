"""Registration, login, logout, /me, and authorization tests."""

import copy

from werkzeug.security import check_password_hash

from tests.conftest import VALID_REGISTRATION


def register(client, overrides=None):
    payload = copy.deepcopy(VALID_REGISTRATION)
    if overrides:
        payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_valid_registration_succeeds(client):
    res = register(client)
    assert res.status_code == 201
    body = res.get_json()
    assert body["user"]["email"] == VALID_REGISTRATION["email"]
    assert body["user"]["role"] == "user"
    assert "password" not in body["user"]
    assert "passwordHash" not in body["user"]


def test_duplicate_email_registration_is_rejected(client):
    first = register(client)
    assert first.status_code == 201

    second = register(client, {"fullName": "Another Person"})
    assert second.status_code == 409
    assert "email" in second.get_json()["fields"]


def test_registration_rejects_invalid_email(client):
    res = register(client, {"email": "not-an-email"})
    assert res.status_code == 400
    assert "email" in res.get_json()["fields"]


def test_registration_rejects_short_password(client):
    res = register(client, {"password": "123", "confirmPassword": "123"})
    assert res.status_code == 400
    assert "password" in res.get_json()["fields"]


def test_registration_rejects_mismatched_passwords(client):
    res = register(client, {"confirmPassword": "different-password"})
    assert res.status_code == 400
    assert "confirmPassword" in res.get_json()["fields"]


def test_registration_rejects_missing_consent(client):
    res = register(client, {"consent": False})
    assert res.status_code == 400
    assert "consent" in res.get_json()["fields"]


def test_registration_rejects_invalid_blood_group(client):
    res = register(client, {"bloodGroup": "Z+"})
    assert res.status_code == 400
    assert "bloodGroup" in res.get_json()["fields"]


def test_password_is_stored_hashed_not_plaintext(client, app):
    register(client)
    with app.app_context():
        from backend.database import get_db

        row = get_db().execute(
            "SELECT password_hash FROM users WHERE email = ?",
            (VALID_REGISTRATION["email"],),
        ).fetchone()
    assert row["password_hash"] != VALID_REGISTRATION["password"]
    assert check_password_hash(row["password_hash"], VALID_REGISTRATION["password"])


def test_public_registration_cannot_assign_admin_role(client, app):
    payload = copy.deepcopy(VALID_REGISTRATION)
    payload["role"] = "admin"  # an attacker-supplied field; must be ignored
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    assert res.get_json()["user"]["role"] == "user"

    with app.app_context():
        from backend.database import get_db

        row = get_db().execute(
            "SELECT role FROM users WHERE email = ?", (VALID_REGISTRATION["email"],)
        ).fetchone()
    assert row["role"] == "user"


def test_malformed_json_is_rejected_gracefully(client):
    res = client.post(
        "/api/auth/register",
        data="not json",
        content_type="application/json",
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Login / logout / current user
# ---------------------------------------------------------------------------

def test_login_with_valid_credentials_succeeds(client):
    register(client)
    res = client.post(
        "/api/auth/login",
        json={"email": VALID_REGISTRATION["email"], "password": VALID_REGISTRATION["password"]},
    )
    assert res.status_code == 200
    assert res.get_json()["user"]["email"] == VALID_REGISTRATION["email"]


def test_login_with_invalid_password_is_rejected(client):
    register(client)
    res = client.post(
        "/api/auth/login",
        json={"email": VALID_REGISTRATION["email"], "password": "wrong-password"},
    )
    assert res.status_code == 401


def test_login_with_unknown_email_is_rejected(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert res.status_code == 401


def test_me_requires_authentication(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user_when_authenticated(client):
    register(client)
    client.post(
        "/api/auth/login",
        json={"email": VALID_REGISTRATION["email"], "password": VALID_REGISTRATION["password"]},
    )
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.get_json()["user"]["email"] == VALID_REGISTRATION["email"]


def test_logout_ends_the_session(client):
    register(client)
    client.post(
        "/api/auth/login",
        json={"email": VALID_REGISTRATION["email"], "password": VALID_REGISTRATION["password"]},
    )
    assert client.get("/api/auth/me").status_code == 200

    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    assert client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def test_regular_user_cannot_access_admin_endpoint(client):
    register(client)
    client.post(
        "/api/auth/login",
        json={"email": VALID_REGISTRATION["email"], "password": VALID_REGISTRATION["password"]},
    )
    res = client.get("/api/admin/summary")
    assert res.status_code == 403


def test_anonymous_user_cannot_access_admin_endpoint(client):
    res = client.get("/api/admin/summary")
    assert res.status_code == 401


def test_admin_user_can_access_admin_endpoint(client, make_admin):
    admin = make_admin()
    res = client.post(
        "/api/auth/login", json={"email": admin["email"], "password": admin["password"]}
    )
    assert res.status_code == 200
    assert res.get_json()["user"]["role"] == "admin"

    summary_res = client.get("/api/admin/summary")
    assert summary_res.status_code == 200
    assert "totalUsers" in summary_res.get_json()["summary"]
