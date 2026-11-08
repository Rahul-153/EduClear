import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import settings
from backend.app.db import get_session
from backend.app.integrations import paypal as pp_mod
from backend.app.integrations.paypal import MockPayPal, get_paypal, inr_to_usd_cents
from backend.app.main import app
from backend.app.services import kit as kit_service
from backend.app.services.programs import PROGRAMS, slots

H = {"X-Client-Id": "browser-aaaa-1111"}
H2 = {"X-Client-Id": "browser-bbbb-2222"}


@pytest.fixture()
def env():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    mock = MockPayPal()

    def sess():
        with Session(eng) as s:
            yield s
    app.dependency_overrides[get_session] = sess
    app.dependency_overrides[get_paypal] = lambda: mock
    yield TestClient(app), mock
    app.dependency_overrides.clear()


def slot(pid="branch-vs-college", i=0):
    return slots(PROGRAMS[pid])[i].isoformat()


def book(c, pid="branch-vs-college", i=0, h=H):
    return c.post("/api/bookings", json={"program_id": pid, "slot_start": slot(pid, i)}, headers=h)


def pay(c, bid, h=H):
    assert c.post(f"/api/bookings/{bid}/mock-approve", json={}, headers=h).status_code == 200
    return c.post(f"/api/bookings/{bid}/capture", headers=h)


def test_usd_conversion_is_fixed_and_documented():
    assert inr_to_usd_cents(2499) == 2999 and inr_to_usd_cents(999) == 1199 and inr_to_usd_cents(3499) == 4199


def test_sandbox_only_guard(monkeypatch):
    monkeypatch.setattr(settings, "paypal_env", "live")
    with pytest.raises(RuntimeError):
        pp_mod.assert_sandbox()
    with pytest.raises(RuntimeError):
        get_paypal()
    assert pp_mod.SANDBOX_BASE == "https://api-m.sandbox.paypal.com"


def test_escrow_happy_path(env):
    c, _ = env
    b = book(c).json()
    assert b["status"] == "pending" and b["usd"] == "29.99" and b["paypal_order_id"].startswith("MOCK-ORDER")
    funded = pay(c, b["id"]).json()
    assert funded["status"] == "escrow_funded" and [e["kind"] for e in funded["ledger"]] == ["funded"]
    again = c.post(f"/api/bookings/{b['id']}/capture", headers=H).json()  # idempotent
    assert len(again["ledger"]) == 1
    done = c.post(f"/api/bookings/{b['id']}/complete", headers=H).json()
    assert done["status"] == "released" and [e["kind"] for e in done["ledger"]] == ["funded", "released"]
    assert len(c.post(f"/api/bookings/{b['id']}/complete", headers=H).json()["ledger"]) == 2  # no double payout


def test_capture_requires_buyer_approval_and_decline_path(env):
    c, _ = env
    b = book(c).json()
    assert c.post(f"/api/bookings/{b['id']}/capture", headers=H).status_code == 402  # not approved
    c.post(f"/api/bookings/{b['id']}/mock-approve", json={"approve": False}, headers=H)
    assert c.post(f"/api/bookings/{b['id']}/capture", headers=H).status_code == 402  # declined
    assert c.post(f"/api/bookings/{b['id']}/cancel", headers=H).json()["status"] == "cancelled"
    assert c.post(f"/api/bookings/{b['id']}/capture", headers=H).status_code == 409


def test_cannot_release_before_funding_and_owner_scoping(env):
    c, _ = env
    b = book(c).json()
    assert c.post(f"/api/bookings/{b['id']}/complete", headers=H).status_code == 409
    assert c.post(f"/api/bookings/{b['id']}/capture", headers=H2).status_code == 404  # another visitor
    assert c.get("/api/bookings", headers=H2).json() == []
    assert c.get("/api/bookings").status_code == 400


def test_payout_failure_then_retry(env):
    c, mock = env
    b = book(c).json()
    pay(c, b["id"])
    mock.fail_payout = True
    assert c.post(f"/api/bookings/{b['id']}/complete", headers=H).status_code == 502
    assert c.get("/api/bookings", headers=H).json()[0]["status"] == "payout_failed"
    mock.fail_payout = False
    ok = c.post(f"/api/bookings/{b['id']}/complete", headers=H).json()
    assert ok["status"] == "released" and sum(e["kind"] == "released" for e in ok["ledger"]) == 1


def test_one_to_one_slot_cannot_be_double_booked(env):
    c, _ = env
    a, b = book(c).json(), book(c, h=H2).json()
    assert pay(c, a["id"]).status_code == 200
    assert c.post(f"/api/bookings/{b['id']}/mock-approve", json={}, headers=H2).status_code == 200
    assert c.post(f"/api/bookings/{b['id']}/capture", headers=H2).status_code == 409  # taken before payment completed
    assert book(c, h=H2).status_code == 409  # slot now full
    first = c.get(f"/api/programs/branch-vs-college/slots").json()[0]
    assert first["left"] == 0


def test_cohort_capacity_and_direct_payment(env, monkeypatch):
    c, _ = env
    from dataclasses import replace
    monkeypatch.setitem(PROGRAMS, "year1-roadmap", replace(PROGRAMS["year1-roadmap"], capacity=2))
    ids = []
    for h in (H, H2):
        b = book(c, "year1-roadmap", 0, h).json()
        assert pay(c, b["id"], h).json()["status"] == "paid"  # direct, no escrow
        ids.append(b["id"])
    assert book(c, "year1-roadmap", 0, {"X-Client-Id": "browser-cccc-3333"}).status_code == 409
    assert c.post(f"/api/bookings/{ids[0]}/complete", headers=H).status_code == 409  # nothing to release


def test_invalid_slot_rejected(env):
    c, _ = env
    r = c.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": "2020-01-01T10:00:00"}, headers=H)
    assert r.status_code == 422
    assert c.post("/api/bookings", json={"program_id": "nope", "slot_start": slot()}, headers=H).status_code == 404


def _capture_event(eid, order_id, cap="CAP-WH-1"):
    return {"id": eid, "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {
        "id": cap, "amount": {"value": "29.99", "currency_code": "USD"}, "supplementary_data": {"related_ids": {"order_id": order_id}}}}


def test_webhook_signature_idempotency_and_funding(env):
    c, _ = env
    b = book(c).json()
    ev = _capture_event("WH-1", b["paypal_order_id"])
    assert c.post("/api/webhooks/paypal", json=ev).status_code == 401  # no valid signature
    ok = {"x-mock-signature": "valid"}
    assert c.post("/api/webhooks/paypal", json=ev, headers=ok).json()["status"] == "funded"
    assert c.post("/api/webhooks/paypal", json=ev, headers=ok).json() == {"status": "duplicate"}  # replay ignored
    replay_new_id = _capture_event("WH-2", b["paypal_order_id"])  # same capture, different event id
    c.post("/api/webhooks/paypal", json=replay_new_id, headers=ok)
    mine = c.get("/api/bookings", headers=H).json()[0]
    assert mine["status"] == "escrow_funded" and len(mine["ledger"]) == 1
    other = {"id": "WH-3", "event_type": "CHECKOUT.ORDER.APPROVED", "resource": {}}
    assert c.post("/api/webhooks/paypal", json=other, headers=ok).json()["status"] == "ignored"


def test_tech_kit_sample_fallback_and_order(env):
    c, _ = env
    k = c.get("/api/kit").json()
    assert k["supported"] and k["sample_data"] is True and "Sample" in k["items"][0]["title"] and k["total_inr"] == 88_500
    o = c.post("/api/kit/order", json={"item_ids": ["laptop", "peripherals"]}, headers=H).json()
    assert o["amount_inr"] == 88_500 and o["usd"] == "1062.00" and o["pay_in_4_usd"] == "265.50"
    assert pay(c, o["id"]).json()["status"] == "paid"
    assert c.post("/api/kit/order", json={"item_ids": ["nope"]}, headers=H).status_code == 422
    assert c.get("/api/kit?stream=MBA").json()["supported"] is False


def test_kit_live_parsing_and_failure_fallback(monkeypatch):
    monkeypatch.setattr(settings, "channel3_api_key", "test-key")
    kit_service._cache.clear()

    class R:
        def raise_for_status(self): pass
        def json(self): return {"products": [{"title": "A", "price": {"price": 1200.0, "currency": "USD"}, "url": "https://x"},
                                             {"title": "B", "price": {"price": 900.0, "currency": "USD"}, "url": "https://y"}]}
    monkeypatch.setattr(kit_service.httpx, "post", lambda *a, **k: R())
    k = kit_service.kit()
    assert k["sources"] == ["channel3-live"] and k["items"][0]["title"] == "B" and k["items"][0]["price_inr"] == 75_000
    assert "converted" in k["items"][0]["currency_note"]
    monkeypatch.setattr(kit_service.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    assert kit_service.kit()["sources"] == ["channel3-cached"]  # last good response
    kit_service._cache.clear()
    assert kit_service.kit()["sources"] == ["sample"]


def test_config_endpoint_discloses_mode_and_rate(env):
    c, _ = env
    j = c.get("/api/payments/config").json()
    assert j["mode"] == "mock" and j["client_id"] is None and "0.012" in j["currency_note"] and "no separate escrow product" in j["escrow_note"]


def test_render_postgres_url_is_normalised():
    from backend.app.config import Settings
    assert Settings(database_url="postgres://u:p@h:5432/d").database_url == "postgresql+psycopg://u:p@h:5432/d"
    assert Settings(database_url="postgresql://u:p@h/d").database_url == "postgresql+psycopg://u:p@h/d"
    assert Settings(database_url="sqlite:///x.db").database_url == "sqlite:///x.db"


def test_zapier_hook_is_best_effort_and_pii_free(env, monkeypatch):
    from backend.app.integrations import zapier
    sent = []
    monkeypatch.setattr(settings, "zapier_webhook_url", "https://hooks.zapier.test/x")
    monkeypatch.setattr(zapier.httpx, "post", lambda url, json, timeout: sent.append(json) or type("R", (), {"status_code": 200})())
    c, _ = env
    b = book(c).json()
    assert pay(c, b["id"]).json()["status"] == "escrow_funded"
    assert len(sent) == 1 and set(sent[0]) == {"event", "booking_id", "program", "title", "slot_start_ist", "amount_inr"}
    # a failing Zap must not break the booking
    monkeypatch.setattr(zapier.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    b2 = book(c, i=1, h=H2).json()
    assert pay(c, b2["id"], H2).json()["status"] == "escrow_funded"
    monkeypatch.setattr(settings, "zapier_webhook_url", "")
    assert zapier.notify_booked(1, "p", "t", "2026-01-01T10:00:00", 1) == "not-configured"


def _age(c, bid, minutes):
    from datetime import datetime, timedelta
    from backend.app.db import Booking
    gen = app.dependency_overrides[get_session]()
    s = next(gen)
    b = s.get(Booking, bid)
    b.created_at = datetime.utcnow() - timedelta(minutes=minutes)
    s.add(b); s.commit()


def test_unpaid_booking_expires_and_frees_its_row(env):
    c, _ = env
    old, fresh = book(c, i=0).json(), book(c, i=1).json()
    _age(c, old["id"], 20)
    rows = {b["id"]: b["status"] for b in c.get("/api/bookings", headers=H).json()}
    assert rows[old["id"]] == "cancelled" and rows[fresh["id"]] == "pending"


def test_approved_but_uncaptured_booking_is_funded_not_cancelled(env):
    c, mock = env
    b = book(c).json()
    mock.approve(b["paypal_order_id"])  # buyer approved, but the pop-up hung before the app captured
    _age(c, b["id"], 20)
    rows = {r["id"]: r["status"] for r in c.get("/api/bookings", headers=H).json()}
    assert rows[b["id"]] == "escrow_funded"


def test_kit_parses_channel3_nested_offers_and_price_floor(monkeypatch):
    monkeypatch.setattr(settings, "channel3_api_key", "test-key")
    kit_service._cache.clear()
    offer = lambda price, avail="InStock": [{"url": "https://shop/x", "availability": avail, "price": {"price": price, "currency": "USD"}}]

    class R:
        def raise_for_status(self): pass
        def json(self): return {"products": [{"title": "Laptop sleeve", "offers": offer(15)},
                                             {"title": "Sold out laptop", "offers": offer(700, "OutOfStock")},
                                             {"title": "GPU laptop", "offers": offer(1000)}]}
    monkeypatch.setattr(kit_service.httpx, "post", lambda *a, **k: R())
    k = kit_service.kit()
    assert k["items"][0]["title"] == "GPU laptop" and k["items"][0]["url"] == "https://shop/x"
