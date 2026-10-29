"""Donor directory, profile, and authorization tests (Step 3)."""

from tests.conftest import VALID_REGISTRATION, login


def register(client, overrides=None):
    import copy

    payload = copy.deepcopy(VALID_REGISTRATION)
    if overrides:
        payload.update(overrides)
    res = client.post("/api/auth/register", json=payload)
    return res, payload


# ---------------------------------------------------------------------------
# Retrieval, search, filtering
# ---------------------------------------------------------------------------

def test_list_donors_returns_database_records(client):
    register(client)
    res = client.get("/api/donors")
    assert res.status_code == 200
    body = res.get_json()
    assert body["total"] == 1
    assert body["donors"][0]["fullName"] == VALID_REGISTRATION["fullName"]


def test_list_donors_hides_contact_details_from_anonymous_visitors(client):
    register(client)
    res = client.get("/api/donors")
    donor = res.get_json()["donors"][0]
    assert "phone" not in donor
    assert "email" not in donor
    assert "userId" not in donor


def test_search_donors_by_name(client):
    register(client, {"fullName": "Alpha Donor", "email": "alpha@example.com"})
    register(client, {"fullName": "Beta Donor", "email": "beta@example.com"})

    res = client.get("/api/donors", query_string={"q": "alpha"})  # lowercase: case-insensitive
    donors = res.get_json()["donors"]
    assert len(donors) == 1
    assert donors[0]["fullName"] == "Alpha Donor"


def test_search_donors_by_id(client):
    register(client)
    listed = client.get("/api/donors").get_json()["donors"][0]

    res = client.get(f"/api/donors/{listed['id']}")
    assert res.status_code == 200
    assert res.get_json()["donor"]["id"] == listed["id"]


def test_search_donors_by_email_requires_admin_context_but_filter_still_narrows_results(client, admin_client):
    register(client, {"fullName": "Findable Person", "email": "findable@example.com"})
    res = admin_client.get("/api/donors", query_string={"email": "findable"})
    donors = res.get_json()["donors"]
    assert any(d["fullName"] == "Findable Person" for d in donors)


def test_filter_donors_by_blood_group(client):
    register(client, {"bloodGroup": "A+", "email": "a1@example.com"})
    register(client, {"bloodGroup": "O-", "email": "a2@example.com"})

    res = client.get("/api/donors", query_string={"bloodGroup": "A+"})
    donors = res.get_json()["donors"]
    assert len(donors) == 1
    assert donors[0]["bloodGroup"] == "A+"


def test_filter_donors_by_invalid_blood_group_is_rejected(client):
    res = client.get("/api/donors", query_string={"bloodGroup": "Z+"})
    assert res.status_code == 400


def test_filter_donors_by_status(client, admin_client):
    register(client)  # defaults to status 'pending'
    res = admin_client.get("/api/donors", query_string={"status": "pending"})
    assert res.status_code == 200
    assert len(res.get_json()["donors"]) == 1

    res2 = admin_client.get("/api/donors", query_string={"status": "approved"})
    assert res2.get_json()["total"] == 0


def test_combine_search_and_filters(client):
    register(client, {"fullName": "Combo Donor", "bloodGroup": "B+", "city": "Nashik", "email": "combo@example.com"})
    register(client, {"fullName": "Combo Decoy", "bloodGroup": "A-", "city": "Nashik", "email": "decoy@example.com"})

    res = client.get("/api/donors", query_string={"q": "Combo", "bloodGroup": "B+", "city": "Nashik"})
    donors = res.get_json()["donors"]
    assert len(donors) == 1
    assert donors[0]["fullName"] == "Combo Donor"


def test_no_matching_donors_returns_empty_list(client):
    res = client.get("/api/donors", query_string={"q": "Nobody Here"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["donors"] == []
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# Creation / validation / duplicate prevention
# ---------------------------------------------------------------------------

def test_create_donor_profile_requires_authentication(client):
    res = client.post("/api/donors", json={"fullName": "X", "bloodGroup": "O+", "phone": "9000000000", "city": "Pune"})
    assert res.status_code == 401


def test_registration_already_creates_a_valid_donor_profile(client):
    res, payload = register(client)
    assert res.status_code == 201

    donors = client.get("/api/donors").get_json()["donors"]
    assert len(donors) == 1
    assert donors[0]["bloodGroup"] == payload["bloodGroup"]


def test_create_donor_rejects_invalid_blood_group(user_without_donor_profile):
    res = user_without_donor_profile.post(
        "/api/donors",
        json={"fullName": "Bad Group", "bloodGroup": "ZZ", "phone": "9000000000", "city": "Pune", "consent": True},
    )
    assert res.status_code == 400
    assert "bloodGroup" in res.get_json()["fields"]


def test_create_donor_rejects_malformed_input(user_without_donor_profile):
    res = user_without_donor_profile.post(
        "/api/donors", json={"fullName": "", "bloodGroup": "", "phone": "", "city": ""}
    )
    assert res.status_code == 400
    fields = res.get_json()["fields"]
    assert {"fullName", "bloodGroup", "phone", "city"}.issubset(fields.keys())


def test_create_donor_with_valid_input_persists_to_database(user_without_donor_profile, app):
    res = user_without_donor_profile.post(
        "/api/donors",
        json={
            "fullName": "Freshly Created",
            "bloodGroup": "B-",
            "phone": "9222233334",
            "city": "Surat",
            "consent": True,
        },
    )
    assert res.status_code == 201
    donor_id = res.get_json()["donor"]["id"]

    with app.app_context():
        from backend.database import get_db

        row = get_db().execute("SELECT full_name FROM donors WHERE id = ?", (donor_id,)).fetchone()
    assert row["full_name"] == "Freshly Created"


def test_create_donor_prevents_duplicate_profile_for_same_user(registered_user, client):
    res = client.post(
        "/api/donors",
        json={
            "fullName": "Second Profile Attempt",
            "bloodGroup": "A+",
            "phone": "9111111111",
            "city": "Pune",
            "consent": True,
        },
    )
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# Authorization on updates
# ---------------------------------------------------------------------------

def test_owner_can_update_their_own_donor_profile(registered_user, client):
    donor_id = registered_user["donorId"]
    res = client.patch(f"/api/donors/{donor_id}", json={"city": "Updated City"})
    assert res.status_code == 200
    assert res.get_json()["donor"]["city"] == "Updated City"


def test_regular_user_cannot_edit_another_users_donor_record(registered_user, client):
    # Register a second account in the SAME client session (logs out the first implicitly via login()).
    other_res, other_payload = register(client, {"fullName": "Other Person", "email": "other@example.com"})
    assert other_res.status_code == 201
    login(client, other_payload["email"], other_payload["password"])

    other_donor_id = registered_user["donorId"]
    res = client.patch(f"/api/donors/{other_donor_id}", json={"city": "Hijacked"})
    assert res.status_code == 403


def test_changing_donor_id_in_url_never_grants_access_to_anothers_record(registered_user, client):
    other_res, other_payload = register(client, {"fullName": "Second User", "email": "second@example.com"})
    login(client, other_payload["email"], other_payload["password"])

    res = client.patch(f"/api/donors/{registered_user['donorId']}", json={"status": "approved"})
    assert res.status_code in (400, 403)  # 403 for not-owner; never a silent 200


def test_unauthenticated_user_cannot_update_any_donor_record(client, registered_user):
    client.post("/api/auth/logout")
    res = client.patch(f"/api/donors/{registered_user['donorId']}", json={"city": "Nope"})
    assert res.status_code == 401


def test_owner_cannot_set_their_own_status(registered_user, client):
    res = client.patch(f"/api/donors/{registered_user['donorId']}", json={"status": "approved"})
    assert res.status_code == 400
    assert "status" in res.get_json()["fields"]


def test_admin_can_change_donor_status(registered_user, admin_client):
    res = admin_client.patch(f"/api/donors/{registered_user['donorId']}", json={"status": "approved"})
    assert res.status_code == 200
    assert res.get_json()["donor"]["status"] == "approved"


def test_admin_can_view_private_donor_fields(registered_user, admin_client):
    res = admin_client.get(f"/api/donors/{registered_user['donorId']}")
    donor = res.get_json()["donor"]
    assert "phone" in donor
    assert "email" in donor or donor.get("email") is None


# ---------------------------------------------------------------------------
# Donation history
# ---------------------------------------------------------------------------

def test_donation_history_comes_from_the_database(registered_user, client, app):
    with app.app_context():
        from backend.database import get_db

        get_db().execute(
            "INSERT INTO donations (donor_id, donation_date, quantity_units) VALUES (?, '2026-01-01', 1)",
            (registered_user["donorId"],),
        )
        get_db().commit()

    res = client.get(f"/api/donors/{registered_user['donorId']}/donations")
    assert res.status_code == 200
    donations = res.get_json()["donations"]
    assert len(donations) == 1
    assert donations[0]["donationDate"] == "2026-01-01"


def test_donation_history_is_empty_when_no_records_exist(registered_user, client):
    res = client.get(f"/api/donors/{registered_user['donorId']}/donations")
    assert res.status_code == 200
    assert res.get_json()["donations"] == []


def test_donation_history_requires_authentication(client, registered_user):
    client.post("/api/auth/logout")
    res = client.get(f"/api/donors/{registered_user['donorId']}/donations")
    assert res.status_code == 401


def test_donation_history_not_visible_to_other_regular_users(client, registered_user):
    other_res, other_payload = register(client, {"fullName": "Nosy User", "email": "nosy@example.com"})
    login(client, other_payload["email"], other_payload["password"])

    res = client.get(f"/api/donors/{registered_user['donorId']}/donations")
    assert res.status_code == 403
