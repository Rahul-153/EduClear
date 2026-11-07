from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from backend.app.db import get_session
from backend.app.engines import refund as R
from backend.app.main import app
from backend.app.services import admissions

POL = admissions.refund_policy()
CLOSE = date(2026, 7, 20)


@pytest.mark.parametrize("notice,tier,pct", [
    (date(2026, 7, 5), "t1", 100),    # 15 days before
    (date(2026, 7, 6), "t2", 90),     # 14 days before
    (date(2026, 7, 20), "t2", 90),    # the last date itself
    (date(2026, 7, 21), "t3", 80),
    (date(2026, 8, 4), "t3", 80),     # +15
    (date(2026, 8, 5), "t4", 50),     # +16
    (date(2026, 8, 19), "t4", 50),    # +30
    (date(2026, 8, 20), "t5", 0),     # +31
])
def test_tier_boundaries(notice, tier, pct):
    r = R.refund(POL, 100_000, CLOSE, notice)
    assert (r["tier_id"], r["refund_percent"]) == (tier, pct)


def test_refund_amounts_and_processing_fee():
    r = R.refund(POL, 30_000, CLOSE, date(2026, 7, 5))
    assert (r["gross_refund_inr"], r["max_processing_fee_inr"], r["minimum_net_refund_inr"]) == (30_000, 1_500, 28_500)
    assert R.refund(POL, 200_000, CLOSE, date(2026, 7, 5))["max_processing_fee_inr"] == 5_000  # 5% capped at Rs 5,000
    assert R.refund(POL, 30_000, CLOSE, date(2026, 7, 6))["minimum_net_refund_inr"] == 27_000  # no fee outside tier 1


def test_milestones():
    ms = R.milestones(POL, CLOSE, today=date(2026, 7, 1))
    assert ms[0] == {"tier_id": "t1", "refund_percent": 100, "last_day": "2026-07-05", "days_left": 4}


def test_timeline_statuses_and_no_empty_events():
    t = admissions.timeline(today=date(2026, 7, 1))
    by = {e["id"]: e for e in t["events"]}
    assert by["josaa-r1-allotment"]["status"] == "past" and by["josaa-r3-allotment"]["status"] == "upcoming"
    assert all(e["start"] for e in t["events"]) and "latest published cycle" in t["disclaimer"]
    assert t["seat_acceptance_fee"]["generalInr"] == 30_000


@pytest.fixture()
def client():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)

    def override():
        with Session(eng) as s:
            yield s
    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_deposit_lifecycle_and_alert(client):
    body = {"college_id": "nit-calicut", "amount_inr": 30000, "paid_on": "2026-06-20", "closure_date": date.today().isoformat()}
    H = {"X-Client-Id": "browser-aaaa-1111"}
    d = client.post("/api/deposits", json=body, headers=H).json()
    assert d["refund_if_withdrawn_today"]["tier_id"] == "t2" and d["alert"] is True  # tier 1 passed; the 90% tier ends today (days_left 0)
    assert len(client.get("/api/deposits", headers=H).json()) == 1
    assert client.get("/api/deposits", headers={"X-Client-Id": "browser-bbbb-2222"}).json() == []  # not shared across visitors
    assert client.get("/api/deposits").status_code == 400
    assert client.delete(f"/api/deposits/{d['id']}", headers={"X-Client-Id": "browser-bbbb-2222"}).status_code == 404
    assert client.post("/api/deposits", json={**body, "college_id": "nope"}, headers=H).status_code == 404
    assert client.delete(f"/api/deposits/{d['id']}", headers=H).json() == {"deleted": d["id"]}
    assert client.delete("/api/deposits/999", headers=H).status_code == 404


def test_refund_letter(client):
    r = client.post("/api/refund-letter", json={"student_name": "A Student", "college_name": "Test Institute", "amount_inr": 30000,
                                                "paid_on": "2026-06-20", "closure_date": "2026-07-20", "notice_date": "2026-07-05"}).json()
    assert r["calculation"]["refund_percent"] == 100 and "Rs 30,000" in r["letter"] and "within 15 days" in r["letter"]
    assert "A Student" in r["letter"] and "not legal advice" in r["disclaimer"]
    assert client.get("/api/admissions/timeline").status_code == 200
