"""Reporting endpoint tests (Step 4): request/donation summaries, date
filters, and CSV export, including access control."""

import csv
import io
from datetime import date, timedelta

from tests.conftest import VALID_REGISTRATION, login


def _iso(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


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


def test_requests_report_requires_admin(client):
    assert client.get("/api/reports/requests").status_code == 401

    client.post("/api/auth/register", json=VALID_REGISTRATION)
    login(client, VALID_REGISTRATION["email"], VALID_REGISTRATION["password"])
    assert client.get("/api/reports/requests").status_code == 403


def test_requests_report_groups_by_status(admin_client):
    r1 = submit_request(admin_client).get_json()["request"]["id"]
    submit_request(admin_client, bloodGroup="A+")
    admin_client.patch(f"/api/requests/{r1}", json={"status": "Rejected", "rejectionReason": "x"})

    report = admin_client.get("/api/reports/requests").get_json()
    assert report["totalRequests"] == 2
    assert report["statusBreakdown"]["Rejected"]["count"] == 1
    assert report["statusBreakdown"]["Pending"]["count"] == 1


def test_requests_report_filters_by_status(admin_client):
    r1 = submit_request(admin_client).get_json()["request"]["id"]
    submit_request(admin_client, bloodGroup="A+")
    admin_client.patch(f"/api/requests/{r1}", json={"status": "Rejected", "rejectionReason": "x"})

    report = admin_client.get("/api/reports/requests", query_string={"status": "Rejected"}).get_json()
    assert len(report["requests"]) == 1
    assert report["requests"][0]["status"] == "Rejected"


def test_requests_report_filters_by_blood_group(admin_client):
    submit_request(admin_client, bloodGroup="O+")
    submit_request(admin_client, bloodGroup="A-")

    report = admin_client.get("/api/reports/requests", query_string={"bloodGroup": "A-"}).get_json()
    assert len(report["requests"]) == 1
    assert report["requests"][0]["bloodGroup"] == "A-"


def test_requests_report_rejects_invalid_date(admin_client):
    res = admin_client.get("/api/reports/requests", query_string={"dateFrom": "not-a-date"})
    assert res.status_code == 400
    assert "dateFrom" in res.get_json()["fields"]


def test_requests_report_rejects_inverted_date_range(admin_client):
    res = admin_client.get(
        "/api/reports/requests", query_string={"dateFrom": _iso(0), "dateTo": _iso(-10)}
    )
    assert res.status_code == 400


def test_requests_report_date_range_excludes_out_of_range_requests(admin_client, app):
    submit_request(admin_client, requesterName="In Range")
    report = admin_client.get(
        "/api/reports/requests", query_string={"dateFrom": _iso(-1), "dateTo": _iso(1)}
    ).get_json()
    assert any(r["requesterName"] == "In Range" for r in report["requests"])

    report_excluding = admin_client.get(
        "/api/reports/requests", query_string={"dateFrom": _iso(5), "dateTo": _iso(10)}
    ).get_json()
    assert report_excluding["totalRequests"] == 0


def test_requests_csv_export_requires_admin(client):
    assert client.get("/api/reports/requests/export").status_code == 401


def test_requests_csv_export_returns_valid_csv(admin_client):
    submit_request(admin_client, requesterName="CSV Test Hospital")
    res = admin_client.get("/api/reports/requests/export")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert "attachment" in res.headers["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(res.get_data(as_text=True))))
    assert rows[0][0] == "Request ID"
    assert any("CSV Test Hospital" in row for row in rows[1:])


def test_donations_report_requires_admin(client):
    assert client.get("/api/reports/donations").status_code == 401


def test_donations_report_returns_real_donation_records(admin_client, app, registered_user, client):
    with app.app_context():
        from backend.database import get_db

        get_db().execute(
            "INSERT INTO donations (donor_id, donation_date, quantity_units) VALUES (?, ?, ?)",
            (registered_user["donorId"], _iso(-5), 2),
        )
        get_db().commit()

    report = admin_client.get("/api/reports/donations").get_json()
    assert report["totalDonations"] == 1
    assert report["totalUnits"] == 2
    assert report["donations"][0]["donorName"]


def test_donations_report_csv_never_includes_donor_contact_details(admin_client, app, registered_user):
    with app.app_context():
        from backend.database import get_db

        get_db().execute(
            "INSERT INTO donations (donor_id, donation_date, quantity_units) VALUES (?, ?, ?)",
            (registered_user["donorId"], _iso(-5), 2),
        )
        get_db().commit()

    res = admin_client.get("/api/reports/donations/export")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "phone" not in body.lower()
    assert "@" not in body  # no email addresses leaked into the export


def test_donations_report_date_filter(admin_client, app, registered_user):
    with app.app_context():
        from backend.database import get_db

        get_db().execute(
            "INSERT INTO donations (donor_id, donation_date, quantity_units) VALUES (?, ?, ?)",
            (registered_user["donorId"], _iso(-100), 1),
        )
        get_db().commit()

    report = admin_client.get(
        "/api/reports/donations", query_string={"dateFrom": _iso(-5), "dateTo": _iso(0)}
    ).get_json()
    assert report["totalDonations"] == 0
