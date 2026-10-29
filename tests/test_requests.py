"""Blood request submission, access control, status transitions, and
inventory-deduction tests (Step 4)."""

from datetime import date, timedelta

from tests.conftest import VALID_REGISTRATION, login

ALL_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


def _iso(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def create_batch(client, **overrides):
    payload = {
        "bloodGroup": "O+",
        "quantityUnits": 20,
        "collectedDate": _iso(-10),
        "expiryDate": _iso(30),
    }
    payload.update(overrides)
    return client.post("/api/inventory", json=payload)


def submit_request(client, **overrides):
    payload = {
        "requesterName": "City Hospital",
        "requesterContact": "contact@cityhospital.example",
        "bloodGroup": "O+",
        "quantityUnits": 5,
        "location": "Pune",
        "urgency": "High",
        "notes": "",
    }
    payload.update(overrides)
    return client.post("/api/requests", json=payload)


def login_regular_user(client, email="requester@example.com"):
    payload = dict(VALID_REGISTRATION, email=email, fullName="Requester User")
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    login(client, email, VALID_REGISTRATION["password"])
    return res.get_json()["user"]


# ---------------------------------------------------------------------------
# Creation / validation
# ---------------------------------------------------------------------------

def test_create_request_requires_authentication(client):
    res = submit_request(client)
    assert res.status_code == 401


def test_create_request_succeeds_for_authenticated_user(client):
    login_regular_user(client)
    res = submit_request(client)
    assert res.status_code == 201
    body = res.get_json()["request"]
    assert body["status"] == "Pending"
    assert body["bloodGroup"] == "O+"
    assert body["id"] is not None


def test_create_request_generates_unique_ids_and_timestamp(client):
    login_regular_user(client)
    res1 = submit_request(client, requesterName="Req One")
    res2 = submit_request(client, requesterName="Req Two")
    id1 = res1.get_json()["request"]["id"]
    id2 = res2.get_json()["request"]["id"]
    assert id1 != id2
    assert res2.get_json()["request"]["createdAt"]


def test_create_request_rejects_invalid_blood_group(client):
    login_regular_user(client)
    res = submit_request(client, bloodGroup="ZZ")
    assert res.status_code == 400
    assert "bloodGroup" in res.get_json()["fields"]


def test_create_request_rejects_non_positive_quantity(client):
    login_regular_user(client)
    res = submit_request(client, quantityUnits=0)
    assert res.status_code == 400
    assert "quantityUnits" in res.get_json()["fields"]


def test_create_request_rejects_excessive_quantity(client):
    login_regular_user(client)
    res = submit_request(client, quantityUnits=999)
    assert res.status_code == 400
    assert "quantityUnits" in res.get_json()["fields"]


def test_create_request_rejects_invalid_urgency(client):
    login_regular_user(client)
    res = submit_request(client, urgency="Whenever")
    assert res.status_code == 400
    assert "urgency" in res.get_json()["fields"]


def test_create_request_rejects_missing_required_fields(client):
    login_regular_user(client)
    res = client.post("/api/requests", json={})
    assert res.status_code == 400
    fields = res.get_json()["fields"]
    assert {"requesterName", "requesterContact", "bloodGroup", "location", "urgency"}.issubset(fields.keys())


# ---------------------------------------------------------------------------
# Visibility / access control
# ---------------------------------------------------------------------------

def test_user_sees_only_their_own_requests(client):
    login_regular_user(client, email="userA@example.com")
    submit_request(client, requesterName="User A Request")

    client.post("/api/auth/logout")
    login_regular_user(client, email="userB@example.com")
    submit_request(client, requesterName="User B Request")

    res = client.get("/api/requests")
    body = res.get_json()
    assert body["total"] == 1
    assert body["requests"][0]["requesterName"] == "User B Request"


def test_admin_sees_all_requests(client, admin_client):
    login_regular_user(client, email="userA@example.com")
    submit_request(client, requesterName="User A Request")
    client.post("/api/auth/logout")
    login_regular_user(client, email="userB@example.com")
    submit_request(client, requesterName="User B Request")

    res = admin_client.get("/api/requests")
    assert res.get_json()["total"] == 2


def test_user_cannot_view_another_users_request_by_id(client):
    login_regular_user(client, email="userA@example.com")
    request_id = submit_request(client).get_json()["request"]["id"]

    client.post("/api/auth/logout")
    login_regular_user(client, email="userB@example.com")
    res = client.get(f"/api/requests/{request_id}")
    assert res.status_code == 403


def test_admin_can_view_any_request_by_id(client, admin_client):
    login_regular_user(client)
    request_id = submit_request(client).get_json()["request"]["id"]

    res = admin_client.get(f"/api/requests/{request_id}")
    assert res.status_code == 200


def test_unauthenticated_user_cannot_list_or_create_requests(client):
    assert client.get("/api/requests").status_code == 401
    assert submit_request(client).status_code == 401


# ---------------------------------------------------------------------------
# Status transitions and authorization
# ---------------------------------------------------------------------------

def test_regular_user_cannot_change_request_status(client):
    login_regular_user(client)
    request_id = submit_request(client).get_json()["request"]["id"]
    res = client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    assert res.status_code == 403


def test_unauthenticated_cannot_change_request_status(client, admin_client):
    request_id = submit_request(admin_client).get_json()["request"]["id"]
    client.post("/api/auth/logout")
    res = client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    assert res.status_code == 401


def test_admin_approve_with_sufficient_stock_succeeds(admin_client):
    create_batch(admin_client, bloodGroup="A+", quantityUnits=10)
    request_id = submit_request(admin_client, bloodGroup="A+", quantityUnits=5).get_json()["request"]["id"]

    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    assert res.status_code == 200
    assert res.get_json()["request"]["status"] == "Approved"


def test_admin_approve_with_insufficient_stock_is_rejected(admin_client):
    # No batches created: zero usable stock for this blood group.
    request_id = submit_request(admin_client, bloodGroup="AB-", quantityUnits=5).get_json()["request"]["id"]
    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    assert res.status_code == 409

    # The request must remain untouched (still Pending).
    get_res = admin_client.get(f"/api/requests/{request_id}")
    assert get_res.get_json()["request"]["status"] == "Pending"


def test_reject_requires_a_reason(admin_client):
    request_id = submit_request(admin_client).get_json()["request"]["id"]
    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Rejected"})
    assert res.status_code == 400
    assert "rejectionReason" in res.get_json()["fields"]


def test_reject_with_reason_succeeds(admin_client):
    request_id = submit_request(admin_client).get_json()["request"]["id"]
    res = admin_client.patch(
        f"/api/requests/{request_id}", json={"status": "Rejected", "rejectionReason": "Out of stock"}
    )
    assert res.status_code == 200
    body = res.get_json()["request"]
    assert body["status"] == "Rejected"
    assert body["rejectionReason"] == "Out of stock"


def test_invalid_transition_pending_to_fulfilled_is_rejected(admin_client):
    create_batch(admin_client, bloodGroup="B+", quantityUnits=10)
    request_id = submit_request(admin_client, bloodGroup="B+").get_json()["request"]["id"]
    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})
    assert res.status_code == 409


def test_rejected_request_is_a_terminal_state(admin_client):
    request_id = submit_request(admin_client).get_json()["request"]["id"]
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Rejected", "rejectionReason": "No stock"})
    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    assert res.status_code == 409


def test_fulfilled_request_is_a_terminal_state(admin_client):
    create_batch(admin_client, bloodGroup="O+", quantityUnits=10)
    request_id = submit_request(admin_client, bloodGroup="O+", quantityUnits=5).get_json()["request"]["id"]
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})

    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Rejected", "rejectionReason": "x"})
    assert res.status_code == 409


def test_invalid_status_value_is_rejected(admin_client):
    request_id = submit_request(admin_client).get_json()["request"]["id"]
    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Cancelled"})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Inventory integration: successful fulfillment, insufficient stock, duplicates
# ---------------------------------------------------------------------------

def _usable_units(client, blood_group):
    summary = client.get("/api/inventory/summary").get_json()["summary"]
    return next(g for g in summary["groups"] if g["bloodGroup"] == blood_group)["usableUnits"]


def test_fulfillment_deducts_stock_and_marks_fulfilled(admin_client):
    create_batch(admin_client, bloodGroup="A-", quantityUnits=20)
    request_id = submit_request(admin_client, bloodGroup="A-", quantityUnits=7).get_json()["request"]["id"]

    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})

    assert res.status_code == 200
    body = res.get_json()["request"]
    assert body["status"] == "Fulfilled"
    assert body["fulfilledAt"] is not None
    assert _usable_units(admin_client, "A-") == 13


def test_fulfillment_draws_from_earliest_expiring_batch_first(admin_client):
    create_batch(admin_client, bloodGroup="B-", quantityUnits=10, expiryDate=_iso(60))
    create_batch(admin_client, bloodGroup="B-", quantityUnits=5, expiryDate=_iso(3))  # expires sooner

    request_id = submit_request(admin_client, bloodGroup="B-", quantityUnits=5).get_json()["request"]["id"]
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})

    batches = admin_client.get("/api/inventory", query_string={"bloodGroup": "B-"}).get_json()["batches"]
    sooner_expiring = next(b for b in batches if b["expiryDate"] == _iso(3))
    later_expiring = next(b for b in batches if b["expiryDate"] == _iso(60))
    assert sooner_expiring["quantityUnits"] == 0  # fully drawn down first
    assert later_expiring["quantityUnits"] == 10  # untouched


def test_fulfillment_with_insufficient_stock_rolls_back_everything(admin_client):
    create_batch(admin_client, bloodGroup="AB+", quantityUnits=5)
    request_id = submit_request(admin_client, bloodGroup="AB+", quantityUnits=5).get_json()["request"]["id"]
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})

    # Stock drops below what's needed between approval and fulfillment
    # (e.g. another request consumed it) — simulate by archiving the batch.
    batch_id = admin_client.get("/api/inventory", query_string={"bloodGroup": "AB+"}).get_json()["batches"][0]["id"]
    admin_client.patch(f"/api/inventory/{batch_id}", json={"status": "archived"})

    res = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})
    assert res.status_code == 409

    # Nothing changed: request still Approved, batch still archived with its original quantity.
    get_res = admin_client.get(f"/api/requests/{request_id}")
    assert get_res.get_json()["request"]["status"] == "Approved"
    batch = admin_client.get(f"/api/inventory/{batch_id}").get_json()["batch"]
    assert batch["quantityUnits"] == 5
    assert batch["status"] == "archived"


def test_repeated_fulfill_action_does_not_double_deduct_stock(admin_client):
    create_batch(admin_client, bloodGroup="O-", quantityUnits=10)
    request_id = submit_request(admin_client, bloodGroup="O-", quantityUnits=4).get_json()["request"]["id"]
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})

    first = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})
    assert first.status_code == 200
    assert _usable_units(admin_client, "O-") == 6

    second = admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})
    assert second.status_code == 409
    assert _usable_units(admin_client, "O-") == 6  # unchanged — no second deduction


def test_inventory_never_goes_negative_on_fulfillment(admin_client):
    create_batch(admin_client, bloodGroup="AB-", quantityUnits=3)
    request_id = submit_request(admin_client, bloodGroup="AB-", quantityUnits=3).get_json()["request"]["id"]
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Approved"})
    admin_client.patch(f"/api/requests/{request_id}", json={"status": "Fulfilled"})
    assert _usable_units(admin_client, "AB-") == 0  # exactly zero, never negative
