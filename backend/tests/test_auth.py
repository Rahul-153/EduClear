"""Accounts (PLAN_AUTH.md phases 1 and 2): codes, sessions, roles, family linking, and the guest path staying open."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.auth.deps import SESSION_COOKIE
from backend.app.config import settings
from backend.app.db import AuthCode, Booking, Consent, Deposit, Family, FamilyMember, Invite, get_session
from backend.app.integrations.mailer import MockMailer, get_mailer
from backend.app.integrations.paypal import MockPayPal, get_paypal
from backend.app.main import app
from backend.app.services.programs import PROGRAMS, slots

X = {"X-Requested-With": "educlear"}
GUEST = {"X-Client-Id": "browser-aaaa-1111"}


@pytest.fixture()
def env():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    mailer, pp = MockMailer(), MockPayPal()

    def sess():
        with Session(eng) as s:
            yield s
    app.dependency_overrides[get_session] = sess
    app.dependency_overrides[get_mailer] = lambda: mailer
    app.dependency_overrides[get_paypal] = lambda: pp
    yield eng, mailer, pp
    app.dependency_overrides.clear()


def browser():
    return TestClient(app)  # each client keeps its own cookie jar, like a separate browser profile


def sign_in(c, mailer, email, role, over18=True, name=""):
    assert c.post("/api/auth/start", json={"email": email, "role": role, "over18": over18, "display_name": name}, headers=X).status_code == 200
    code = mailer.outbox[-1][1]
    r = c.post("/api/auth/verify", json={"email": email, "code": code}, headers=X)
    assert r.status_code == 200, r.text
    return r.json()


def slot():
    return slots(PROGRAMS["branch-vs-college"])[0].isoformat()


def family(env):
    """A parent and an under-18 student in one family, each in their own browser."""
    _, mailer, _ = env
    p, st = browser(), browser()
    sign_in(p, mailer, "mum@example.com", "parent")
    sign_in(st, mailer, "kid@example.com", "student", over18=False)
    code = p.post("/api/family/invite", headers=X).json()["code"]
    assert st.post("/api/family/join", json={"code": code}, headers=X).status_code == 200
    return p, st


# ---- sign-in ----
def test_parent_signs_in_gets_a_family_and_an_http_only_cookie(env):
    _, mailer, _ = env
    c = browser()
    me = sign_in(c, mailer, "Mum@Example.com ", "parent")
    assert me["user"]["role"] == "parent" and me["user"]["email"] == "mum@example.com"
    assert len(me["family"]["members"]) == 1 and me["family"]["members"][0]["role"] == "parent"
    set_cookie = c.post("/api/auth/start", json={"email": "x@example.com", "role": "parent"}).headers.get("set-cookie", "")
    assert SESSION_COOKIE not in set_cookie  # only verify starts a session
    assert c.get("/api/auth/me").json()["user"]["id"] == me["user"]["id"]


def test_cookie_flags(env):
    _, mailer, _ = env
    c = browser()
    c.post("/api/auth/start", json={"email": "a@example.com", "role": "parent"})
    r = c.post("/api/auth/verify", json={"email": "a@example.com", "code": mailer.outbox[-1][1]})
    ck = r.headers["set-cookie"].lower()
    assert "httponly" in ck and "samesite=lax" in ck and r.headers["cache-control"] == "no-store"


def test_start_gives_identical_answers_for_known_and_unknown_emails(env):
    _, mailer, _ = env
    sign_in(browser(), mailer, "known@example.com", "parent")
    a = browser().post("/api/auth/start", json={"email": "known@example.com", "role": "parent"})
    b = browser().post("/api/auth/start", json={"email": "nobody@example.com", "role": "parent"})
    assert a.status_code == b.status_code == 200 and a.json() == b.json()


def test_codes_are_not_stored_in_clear_and_demo_code_is_off_by_default(env):
    eng, mailer, _ = env
    r = browser().post("/api/auth/start", json={"email": "a@example.com", "role": "parent"})
    assert "demo_code" not in r.json()
    with Session(eng) as s:
        row = s.exec(select(AuthCode)).one()
    assert mailer.outbox[-1][1] not in row.code_hash and len(row.code_hash) == 64


def test_demo_code_only_when_enabled_and_never_in_production(env, monkeypatch):
    monkeypatch.setattr(settings, "auth_show_code", True)
    assert "demo_code" in browser().post("/api/auth/start", json={"email": "a@example.com", "role": "parent"}).json()
    monkeypatch.setattr(settings, "env", "production")
    assert browser().post("/api/auth/start", json={"email": "b@example.com", "role": "parent"}).status_code == 503  # mock mailer is not a real channel


def test_wrong_code_five_times_burns_the_code(env):
    _, mailer, _ = env
    c = browser()
    c.post("/api/auth/start", json={"email": "a@example.com", "role": "parent"})
    good = mailer.outbox[-1][1]
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        assert c.post("/api/auth/verify", json={"email": "a@example.com", "code": bad}).status_code == 400
    assert c.post("/api/auth/verify", json={"email": "a@example.com", "code": good}).status_code == 400


def test_expired_and_reused_codes_fail(env):
    eng, mailer, _ = env
    c = browser()
    c.post("/api/auth/start", json={"email": "a@example.com", "role": "parent"})
    good = mailer.outbox[-1][1]
    with Session(eng) as s:
        row = s.exec(select(AuthCode)).one(); row.expires_at = datetime.utcnow() - timedelta(seconds=1); s.add(row); s.commit()
    assert c.post("/api/auth/verify", json={"email": "a@example.com", "code": good}).status_code == 400
    sign_in(c, mailer, "b@example.com", "parent")
    assert c.post("/api/auth/verify", json={"email": "b@example.com", "code": mailer.outbox[-1][1]}, headers=X).status_code == 400  # already used


def test_rate_limit_per_email(env):
    c = browser()
    codes = [c.post("/api/auth/start", json={"email": "a@example.com", "role": "parent"}).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]


def test_role_is_fixed_at_first_sign_in(env):
    _, mailer, _ = env
    sign_in(browser(), mailer, "a@example.com", "parent")
    again = sign_in(browser(), mailer, "a@example.com", "student", over18=False)
    assert again["user"]["role"] == "parent"


def test_every_sign_in_gets_a_new_session_and_logout_ends_it(env):
    _, mailer, _ = env
    c = browser()
    sign_in(c, mailer, "a@example.com", "parent")
    first = c.cookies.get(SESSION_COOKIE)
    sign_in(c, mailer, "a@example.com", "parent")
    assert c.cookies.get(SESSION_COOKIE) != first
    old = browser(); old.cookies.set(SESSION_COOKIE, first)
    assert old.get("/api/auth/me").json()["user"] is not None  # the earlier session is a separate, still valid one
    assert c.post("/api/auth/logout", headers=X).status_code == 200
    assert c.get("/api/auth/me").json()["user"] is None


def test_expired_session_is_rejected(env):
    eng, mailer, _ = env
    c = browser()
    sign_in(c, mailer, "a@example.com", "parent")
    from backend.app.db import LoginSession
    with Session(eng) as s:
        row = s.exec(select(LoginSession)).one(); row.expires_at = datetime.utcnow() - timedelta(seconds=1); s.add(row); s.commit()
    assert c.get("/api/auth/me").json()["user"] is None


# ---- CSRF ----
def test_signed_in_writes_need_the_custom_header_but_webhooks_do_not(env):
    _, mailer, _ = env
    c = browser()
    sign_in(c, mailer, "a@example.com", "parent")
    assert c.post("/api/family/invite").status_code == 403
    assert c.post("/api/family/invite", headers=X).status_code == 200
    assert c.post("/api/webhooks/paypal", content=b"{}").status_code != 403  # signature check decides, not the session


# ---- guests keep working ----
def test_guest_can_still_book_while_guest_checkout_is_on_and_not_when_off(env, monkeypatch):
    c = browser()
    assert c.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot()}, headers=GUEST).status_code == 200
    monkeypatch.setattr(settings, "guest_checkout", False)
    r = c.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot(), }, headers=GUEST)
    assert r.status_code == 401
    assert c.get("/api/bookings", headers=GUEST).status_code == 200  # reading stays open to guests


def test_a_guest_cannot_pose_as_a_family_through_the_header(env):
    r = browser().get("/api/bookings", headers={"X-Client-Id": "family:1"})
    assert r.status_code == 400


# ---- parent and student ----
def test_parent_books_and_student_sees_it_read_only(env):
    p, st = family(env)
    b = p.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot()}, headers=X)
    assert b.status_code == 200
    bid = b.json()["id"]
    assert [x["id"] for x in st.get("/api/bookings").json()] == [bid]
    for method, url, body in [("post", "/api/bookings", {"program_id": "branch-vs-college", "slot_start": slot()}),
                              ("post", f"/api/bookings/{bid}/capture", None), ("post", f"/api/bookings/{bid}/complete", None),
                              ("post", f"/api/bookings/{bid}/cancel", None), ("post", "/api/kit/order", {"item_ids": ["x"]}),
                              ("post", f"/api/bookings/{bid}/mock-approve", {"approve": True})]:
        r = getattr(st, method)(url, json=body, headers=X)
        assert r.status_code == 403, (url, r.status_code)


def test_student_cannot_write_deposits_but_can_read_them(env):
    p, st = family(env)
    dep = {"college_id": "nit-calicut", "amount_inr": 30000, "paid_on": "2026-06-20", "closure_date": "2026-08-01"}
    assert p.post("/api/deposits", json=dep, headers=X).status_code == 200
    assert len(st.get("/api/deposits").json()) == 1
    assert st.post("/api/deposits", json=dep, headers=X).status_code == 403
    did = st.get("/api/deposits").json()[0]["id"]
    assert st.delete(f"/api/deposits/{did}", headers=X).status_code == 403


def test_another_family_sees_nothing(env):
    p, _ = family(env)
    p.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot()}, headers=X)
    _, mailer, _ = env
    other = browser()
    sign_in(other, mailer, "other@example.com", "parent")
    assert other.get("/api/bookings").json() == []
    bid = p.get("/api/bookings").json()[0]["id"]
    assert other.post(f"/api/bookings/{bid}/cancel", headers=X).status_code == 404


def test_signed_in_student_without_a_family_cannot_pay_and_guest_header_is_ignored(env):
    _, mailer, _ = env
    st = browser()
    sign_in(st, mailer, "kid@example.com", "student", over18=False)
    assert st.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot()}, headers={**X, **GUEST}).status_code == 403
    assert st.get("/api/bookings", headers=GUEST).json() == []


def test_agent_confirm_needs_a_parent(env):
    p, st = family(env)
    a = st.post("/api/agent/chat", json={"message": "book branch vs college session", "profile": {}, "lang": "en"}, headers=X)
    assert a.status_code == 200
    pending = a.json().get("pending_action")
    if pending:
        assert st.post("/api/agent/confirm", json={"action_id": pending["id"]}, headers=X).status_code == 403


# ---- family linking ----
def test_invite_is_single_use_and_records_consent_for_a_minor(env):
    eng, mailer, _ = env
    p, st = family(env)
    with Session(eng) as s:
        c = s.exec(select(Consent)).one()
        inv = s.exec(select(Invite)).one()
    assert c.parent_user_id != c.student_user_id and inv.used_at is not None and len(inv.code_hash) == 64
    sibling = browser()
    sign_in(sibling, mailer, "kid2@example.com", "student", over18=False)
    code = p.post("/api/family/invite", headers=X)
    assert code.status_code == 409  # v1: one student per family


def test_invite_code_is_not_reusable_and_wrong_role_fails(env):
    _, mailer, _ = env
    p = browser(); sign_in(p, mailer, "mum@example.com", "parent")
    code = p.post("/api/family/invite", headers=X).json()["code"]
    dad = browser(); sign_in(dad, mailer, "dad@example.com", "parent")
    assert dad.post("/api/family/join", json={"code": code}, headers=X).status_code == 400  # the invite is for a student
    kid = browser(); sign_in(kid, mailer, "kid@example.com", "student", over18=False)
    assert kid.post("/api/family/join", json={"code": code}, headers=X).status_code == 200
    kid2 = browser(); sign_in(kid2, mailer, "kid2@example.com", "student", over18=False)
    assert kid2.post("/api/family/join", json={"code": code}, headers=X).status_code == 400
    assert kid2.post("/api/family/join", json={"code": "ZZZZZZZZ"}, headers=X).status_code == 400


def test_expired_invite_fails(env):
    eng, mailer, _ = env
    p = browser(); sign_in(p, mailer, "mum@example.com", "parent")
    code = p.post("/api/family/invite", headers=X).json()["code"]
    with Session(eng) as s:
        i = s.exec(select(Invite)).one(); i.expires_at = datetime.utcnow() - timedelta(seconds=1); s.add(i); s.commit()
    kid = browser(); sign_in(kid, mailer, "kid@example.com", "student", over18=False)
    assert kid.post("/api/family/join", json={"code": code}, headers=X).status_code == 400


def test_minor_cannot_create_or_invite_but_an_adult_student_can_invite_a_parent(env):
    _, mailer, _ = env
    minor = browser(); sign_in(minor, mailer, "kid@example.com", "student", over18=False)
    assert minor.post("/api/family", headers=X).status_code == 403
    adult = browser(); sign_in(adult, mailer, "adult@example.com", "student", over18=True)
    assert adult.post("/api/family", headers=X).status_code == 200
    code = adult.post("/api/family/invite", headers=X).json()
    assert code["role_to_join"] == "parent"
    mum = browser(); sign_in(mum, mailer, "mum@example.com", "parent")
    assert mum.post("/api/family/join", json={"code": code["code"]}, headers=X).status_code == 200  # her empty family is dropped
    me = mum.get("/api/auth/me").json()
    assert {m["role"] for m in me["family"]["members"]} == {"parent", "student"}


def test_parent_with_records_cannot_join_another_family(env):
    _, mailer, _ = env
    adult = browser(); sign_in(adult, mailer, "adult@example.com", "student", over18=True); adult.post("/api/family", headers=X)
    code = adult.post("/api/family/invite", headers=X).json()["code"]
    mum = browser(); sign_in(mum, mailer, "mum@example.com", "parent")
    mum.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot()}, headers=X)
    assert mum.post("/api/family/join", json={"code": code}, headers=X).status_code == 409


def test_parent_removes_student_student_cannot_remove_parent_and_anyone_can_leave(env):
    p, st = family(env)
    pid = p.get("/api/auth/me").json()["user"]["id"]
    sid = st.get("/api/auth/me").json()["user"]["id"]
    assert st.delete(f"/api/family/members/{pid}", headers=X).status_code == 403
    assert p.delete(f"/api/family/members/{sid}", headers=X).status_code == 200
    assert st.get("/api/auth/me").json()["family"] is None  # back to the waiting state
    assert st.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot()}, headers=X).status_code == 403


def test_parent_cannot_leave_a_student_behind_and_bookings_survive_leaving(env):
    eng, _, _ = env
    p, st = family(env)
    p.post("/api/bookings", json={"program_id": "branch-vs-college", "slot_start": slot()}, headers=X)
    pid = p.get("/api/auth/me").json()["user"]["id"]
    sid = st.get("/api/auth/me").json()["user"]["id"]
    assert p.delete(f"/api/family/members/{pid}", headers=X).status_code == 409  # nobody could release the booking
    assert len(st.get("/api/bookings").json()) == 1
    assert p.delete(f"/api/family/members/{sid}", headers=X).status_code == 200
    assert p.delete(f"/api/family/members/{pid}", headers=X).status_code == 200
    with Session(eng) as s:
        assert s.exec(select(Booking)).first() is not None  # payment records are never deleted by leaving


def test_production_needs_a_real_mailer_and_says_so_in_me(env, monkeypatch):
    monkeypatch.setattr(settings, "env", "production")
    c = browser()
    assert c.get("/api/auth/me").json()["sign_in_available"] is False
    assert c.post("/api/auth/start", json={"email": "mum@example.com", "role": "parent"}, headers=X).status_code == 503


def test_last_member_leaving_removes_the_family_and_its_invites(env):
    eng, mailer, _ = env
    p = browser(); sign_in(p, mailer, "mum@example.com", "parent")
    p.post("/api/family/invite", headers=X)
    pid = p.get("/api/auth/me").json()["user"]["id"]
    assert p.delete(f"/api/family/members/{pid}", headers=X).status_code == 200
    with Session(eng) as s:
        assert s.exec(select(Family)).first() is None and s.exec(select(Invite)).first() is None and s.exec(select(FamilyMember)).first() is None
    assert p.post("/api/family", headers=X).status_code == 200  # can start a new one


def test_deposit_records_are_scoped_by_owner_string(env):
    eng, mailer, _ = env
    p = browser(); sign_in(p, mailer, "mum@example.com", "parent")
    dep = {"college_id": "nit-calicut", "amount_inr": 30000, "paid_on": "2026-06-20", "closure_date": "2026-08-01"}
    p.post("/api/deposits", json=dep, headers=X)
    browser().post("/api/deposits", json=dep, headers=GUEST)
    with Session(eng) as s:
        owners = sorted(d.owner for d in s.exec(select(Deposit)).all())
    assert GUEST["X-Client-Id"] in owners and sum(o.startswith("family:") for o in owners) == 1


def test_display_name_is_kept_and_emails_are_masked_to_family_members(env):
    _, mailer, _ = env
    p = browser(); sign_in(p, mailer, "mum@example.com", "parent", name="Mum")
    st = browser(); sign_in(st, mailer, "kid@example.com", "student", over18=False)
    code = p.post("/api/family/invite", headers=X).json()["code"]
    st.post("/api/family/join", json={"code": code}, headers=X)
    names = {m["role"]: m["name"] for m in p.get("/api/auth/me").json()["family"]["members"]}
    assert names["parent"] == "Mum" and names["student"] == "k***@example.com"
    assert "kid@example.com" not in p.get("/api/auth/me").text  # a family member never sees the other's email
