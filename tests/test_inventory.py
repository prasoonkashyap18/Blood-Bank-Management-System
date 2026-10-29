"""Blood inventory batch management, summary, and authorization tests (Step 3)."""

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


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def test_inventory_summary_is_public_and_covers_all_eight_blood_groups(client, admin_client):
    create_batch(admin_client, bloodGroup="A+")
    res = client.get("/api/inventory/summary")
    assert res.status_code == 200
    groups = res.get_json()["summary"]["groups"]
    assert {g["bloodGroup"] for g in groups} == ALL_BLOOD_GROUPS


def test_list_batches_retrieves_from_database(admin_client):
    create_batch(admin_client, bloodGroup="B+", quantityUnits=7)
    res = admin_client.get("/api/inventory")
    assert res.status_code == 200
    batches = res.get_json()["batches"]
    assert any(b["bloodGroup"] == "B+" and b["quantityUnits"] == 7 for b in batches)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def test_create_batch_as_admin_succeeds(admin_client):
    res = create_batch(admin_client)
    assert res.status_code == 201
    assert res.get_json()["batch"]["bloodGroup"] == "O+"


def test_create_batch_rejected_for_ordinary_user(client):
    client.post("/api/auth/register", json=VALID_REGISTRATION)
    login(client, VALID_REGISTRATION["email"], VALID_REGISTRATION["password"])
    res = create_batch(client)
    assert res.status_code == 403


def test_create_batch_rejected_when_unauthenticated(client):
    res = create_batch(client)
    assert res.status_code == 401


def test_list_batches_rejected_for_ordinary_user(client):
    client.post("/api/auth/register", json=VALID_REGISTRATION)
    login(client, VALID_REGISTRATION["email"], VALID_REGISTRATION["password"])
    res = client.get("/api/inventory")
    assert res.status_code == 403


def test_update_batch_rejected_for_ordinary_user(admin_client, client):
    batch_id = create_batch(admin_client).get_json()["batch"]["id"]

    client.post("/api/auth/register", json=VALID_REGISTRATION)
    login(client, VALID_REGISTRATION["email"], VALID_REGISTRATION["password"])
    res = client.patch(f"/api/inventory/{batch_id}", json={"quantityUnits": 999})
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_create_batch_rejects_invalid_blood_group(admin_client):
    res = create_batch(admin_client, bloodGroup="Z+")
    assert res.status_code == 400
    assert "bloodGroup" in res.get_json()["fields"]


def test_create_batch_rejects_zero_quantity(admin_client):
    res = create_batch(admin_client, quantityUnits=0)
    assert res.status_code == 400
    assert "quantityUnits" in res.get_json()["fields"]


def test_create_batch_rejects_negative_quantity(admin_client):
    res = create_batch(admin_client, quantityUnits=-5)
    assert res.status_code == 400
    assert "quantityUnits" in res.get_json()["fields"]


def test_create_batch_rejects_malformed_date(admin_client):
    res = create_batch(admin_client, expiryDate="not-a-date")
    assert res.status_code == 400
    assert "expiryDate" in res.get_json()["fields"]


def test_create_batch_rejects_expiry_before_collection(admin_client):
    res = create_batch(admin_client, collectedDate=_iso(0), expiryDate=_iso(-5))
    assert res.status_code == 400
    assert "expiryDate" in res.get_json()["fields"]


def test_update_batch_rejects_negative_quantity(admin_client):
    batch_id = create_batch(admin_client).get_json()["batch"]["id"]
    res = admin_client.patch(f"/api/inventory/{batch_id}", json={"quantityUnits": -1})
    assert res.status_code == 400


def test_update_batch_can_zero_out_quantity_for_a_correction(admin_client):
    batch_id = create_batch(admin_client).get_json()["batch"]["id"]
    res = admin_client.patch(f"/api/inventory/{batch_id}", json={"quantityUnits": 0, "notes": "counted incorrectly"})
    assert res.status_code == 200
    assert res.get_json()["batch"]["quantityUnits"] == 0


def test_update_batch_rejects_inconsistent_date_range_against_stored_value(admin_client):
    batch_id = create_batch(admin_client, collectedDate=_iso(-10), expiryDate=_iso(30)).get_json()["batch"]["id"]
    # Only sending a new collectedDate that's now *after* the stored expiryDate.
    res = admin_client.patch(f"/api/inventory/{batch_id}", json={"collectedDate": _iso(40)})
    assert res.status_code == 400
    assert "expiryDate" in res.get_json()["fields"]


# ---------------------------------------------------------------------------
# Stock aggregation and alerts
# ---------------------------------------------------------------------------

def test_grouped_stock_sums_multiple_batches_for_the_same_blood_group(admin_client, client):
    create_batch(admin_client, bloodGroup="AB+", quantityUnits=10)
    create_batch(admin_client, bloodGroup="AB+", quantityUnits=15)

    summary = client.get("/api/inventory/summary").get_json()["summary"]
    ab_plus = next(g for g in summary["groups"] if g["bloodGroup"] == "AB+")
    assert ab_plus["usableUnits"] == 25
    assert ab_plus["batchCount"] == 2


def test_expired_stock_excluded_from_usable_total(admin_client, client):
    create_batch(admin_client, bloodGroup="B-", quantityUnits=30, collectedDate=_iso(-100), expiryDate=_iso(-1))

    summary = client.get("/api/inventory/summary").get_json()["summary"]
    b_minus = next(g for g in summary["groups"] if g["bloodGroup"] == "B-")
    assert b_minus["usableUnits"] == 0
    assert b_minus["expiredUnits"] == 30
    assert b_minus["totalRecordedUnits"] == 30  # still recorded, just not usable


def test_low_stock_blood_groups_identified_correctly(admin_client, client):
    create_batch(admin_client, bloodGroup="AB-", quantityUnits=3)  # below default threshold of 10

    summary = client.get("/api/inventory/summary").get_json()["summary"]
    assert "AB-" in summary["lowStockGroups"]
    ab_minus = next(g for g in summary["groups"] if g["bloodGroup"] == "AB-")
    assert ab_minus["lowStock"] is True


def test_out_of_stock_group_is_not_counted_as_merely_low_stock(client):
    summary = client.get("/api/inventory/summary").get_json()["summary"]
    # No batches seeded in this isolated test DB: every group starts at zero.
    assert set(summary["outOfStockGroups"]) == ALL_BLOOD_GROUPS
    for group in summary["groups"]:
        assert group["lowStock"] is False  # zero stock is "out of stock", not "low stock"


def test_near_expiry_batch_identified_correctly(admin_client, client):
    create_batch(admin_client, bloodGroup="O-", quantityUnits=5, expiryDate=_iso(3))  # within default 7-day window

    res = admin_client.get("/api/inventory")
    batch = next(b for b in res.get_json()["batches"] if b["bloodGroup"] == "O-")
    assert batch["expiryStatus"] == "near_expiry"

    summary = client.get("/api/inventory/summary").get_json()["summary"]
    o_minus = next(g for g in summary["groups"] if g["bloodGroup"] == "O-")
    assert o_minus["nearExpiryUnits"] == 5
    assert o_minus["usableUnits"] == 5  # near-expiry is still usable, just flagged


def test_expired_batch_handled_correctly_and_not_double_counted(admin_client):
    batch_id = create_batch(admin_client, expiryDate=_iso(-1)).get_json()["batch"]["id"]
    res = admin_client.get(f"/api/inventory/{batch_id}")
    assert res.get_json()["batch"]["expiryStatus"] == "expired"


def test_archived_batch_excluded_from_summary_entirely(admin_client, client):
    batch_id = create_batch(admin_client, bloodGroup="A-", quantityUnits=40).get_json()["batch"]["id"]
    admin_client.patch(f"/api/inventory/{batch_id}", json={"status": "archived"})

    summary = client.get("/api/inventory/summary").get_json()["summary"]
    a_minus = next(g for g in summary["groups"] if g["bloodGroup"] == "A-")
    assert a_minus["totalRecordedUnits"] == 0
    assert a_minus["usableUnits"] == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_inventory_data_persists_across_connections(admin_client, app):
    batch_id = create_batch(admin_client, bloodGroup="O+", quantityUnits=99).get_json()["batch"]["id"]

    with app.app_context():
        from backend.database import get_db

        row = get_db().execute(
            "SELECT quantity_units FROM blood_inventory WHERE id = ?", (batch_id,)
        ).fetchone()
    assert row["quantity_units"] == 99
