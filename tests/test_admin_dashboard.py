"""Admin dashboard summary tests (Step 4): real database-backed statistics."""

from datetime import date, timedelta

from tests.conftest import VALID_REGISTRATION, login


def _iso(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def create_batch(client, **overrides):
    payload = {"bloodGroup": "O+", "quantityUnits": 20, "collectedDate": _iso(-10), "expiryDate": _iso(30)}
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
    }
    payload.update(overrides)
    return client.post("/api/requests", json=payload)


def test_admin_summary_requires_admin(client):
    assert client.get("/api/admin/summary").status_code == 401

    client.post("/api/auth/register", json=VALID_REGISTRATION)
    login(client, VALID_REGISTRATION["email"], VALID_REGISTRATION["password"])
    assert client.get("/api/admin/summary").status_code == 403


def test_admin_summary_reflects_real_database_counts(admin_client):
    create_batch(admin_client, bloodGroup="A+", quantityUnits=30)
    req1 = submit_request(admin_client, bloodGroup="A+", quantityUnits=5).get_json()["request"]["id"]
    submit_request(admin_client, bloodGroup="A+", quantityUnits=3)  # stays Pending

    admin_client.patch(f"/api/requests/{req1}", json={"status": "Approved"})
    admin_client.patch(f"/api/requests/{req1}", json={"status": "Fulfilled"})

    summary = admin_client.get("/api/admin/summary").get_json()["summary"]

    assert summary["totalRequests"] == 2
    assert summary["pendingRequests"] == 1
    assert summary["fulfilledRequests"] == 1
    assert summary["availableUnits"] == 25  # 30 - 5 fulfilled
    assert any(g["bloodGroup"] == "A+" and g["usableUnits"] == 25 for g in summary["bloodGroupStock"])
    assert len(summary["recentRequests"]) >= 1


def test_admin_summary_has_useful_empty_state_with_no_data(admin_client):
    summary = admin_client.get("/api/admin/summary").get_json()["summary"]
    assert summary["totalRequests"] == 0
    assert summary["pendingRequests"] == 0
    assert summary["availableUnits"] == 0
    assert summary["recentRequests"] == []
    assert len(summary["bloodGroupStock"]) == 8  # all eight groups still listed, just zeroed


def test_admin_summary_updates_after_inventory_archive(admin_client):
    batch_res = create_batch(admin_client, bloodGroup="B+", quantityUnits=10)
    batch_id = batch_res.get_json()["batch"]["id"]

    before = admin_client.get("/api/admin/summary").get_json()["summary"]
    assert before["availableUnits"] == 10

    admin_client.patch(f"/api/inventory/{batch_id}", json={"status": "archived"})

    after = admin_client.get("/api/admin/summary").get_json()["summary"]
    assert after["availableUnits"] == 0
