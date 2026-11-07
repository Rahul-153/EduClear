import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.app.db import get_session
from backend.app.engines.assumptions import Assumptions
from backend.app.engines.emi import funding_plan
from backend.app.integrations.paypal import MockPayPal, get_paypal
from backend.app.llm.client import get_llm, redact
from backend.app.main import app
from backend.app.services import agent as ag
from backend.app.services import intake
from backend.app.data import get_college

H = {"X-Client-Id": "browser-aaaa-1111"}
H2 = {"X-Client-Id": "browser-bbbb-2222"}


class FakeLLM:
    name = "fake"

    def __init__(self, json_out=None, text_out=None):
        self.json_out, self.text_out, self.calls = json_out, text_out, []

    def json(self, system, user, schema):
        self.calls.append(("json", user))
        return self.json_out

    def text(self, system, user):
        self.calls.append(("text", user))
        return self.text_out


# ---------- intake ----------
def test_intake_english_rules():
    r = intake.parse("I got 93 percentile in JEE Main, our budget is 18 Lakhs total, and we want North or West India")
    assert r["profile"]["percentile"] == 93 and r["profile"]["budget_lakhs"] == 18 and r["profile"]["region"] == "All"  # two regions -> All
    assert r["language"] == "en" and r["sources"]["percentile"] == "rules" and r["llm_used"] is False


def test_intake_hindi_devanagari_digits():
    r = intake.parse("मेरे JEE Main में 99.5 पर्सेंटाइल हैं, बजट १८ लाख है, दक्षिण भारत में कंप्यूटर साइंस चाहिए")
    p = r["profile"]
    assert (p["percentile"], p["budget_lakhs"], p["region"], p["stream"]) == (99.5, 18, "South", "Computer Science") and r["language"] == "hi"


def test_intake_crore_state_advanced_bitsat_and_bounds():
    p = intake.parse("99.2 percentile, budget 0.3 crore, from Kerala, CSE, advanced rank 1200, bitsat 310")["profile"]
    assert p["budget_lakhs"] == 30 and p["home_state"] == "Kerala" and p["jee_advanced_rank"] == 1200 and p["bitsat_score"] == 310
    assert intake.parse("150 percentile")["profile"]["percentile"] is None
    assert intake.parse("West Bengal please")["profile"]["region"] is None  # 'west' belongs to the state name


def test_intake_llm_fills_only_missing_and_is_guarded():
    # rules miss everything; the LLM invents numbers that are not in the text -> discarded, supported semantics kept
    llm = FakeLLM({"percentile": 99.9, "budget_lakhs": 25, "region": "South", "stream": "Computer Science", "home_state": "Kerala"})
    r = intake.parse("looking for something near Chennai for computers, budget is twenty lakhs", llm)
    assert r["profile"]["percentile"] is None and r["profile"]["budget_lakhs"] is None  # not in text
    assert r["profile"]["region"] == "South" and r["sources"]["region"] == "llm" and r["profile"]["home_state"] is None
    llm2 = FakeLLM({"percentile": 98, "budget_lakhs": None, "region": None, "stream": None, "home_state": None})
    assert intake.parse("my score is 98 in the main exam", llm2)["profile"]["percentile"] == 98  # number literally appears
    over = FakeLLM({"percentile": 50, "budget_lakhs": 99, "region": "North", "stream": None, "home_state": None})
    assert intake.parse("99.5 percentile, budget 18 lakhs, south", over)["profile"]["region"] == "South"  # rules never overridden


def test_redact_strips_pii():
    assert "[email]" in redact("mail me at a.b@x.com") and "[phone]" in redact("call 9876543210 or +91 98765 43210")


# ---------- routing / tools ----------
@pytest.mark.parametrize("msg,tool", [
    ("Can I afford NIT Calicut with 8 lakh savings?", "affordability"),
    ("What would the EMI be for DTU?", "emi_compare"),
    ("Is MNIT Jaipur worth it?", "payback"),
    ("tell me about NIT Calicut placement", "explain_college"),
    ("book a counselling session", "propose_booking"),
    ("what sessions do you have for josaa", "list_slots"),
    ("suggest colleges for me", "recommend"),
    ("hello", "help"),
])
def test_rule_router(msg, tool):
    assert ag.route_rules(msg, {}) == tool


def test_rules_first_llm_only_for_ambiguous_and_cannot_book_or_invent():
    spy = FakeLLM({"tool": "payback"})
    assert ag.choose_tool("is it worth it, MNIT", {}, spy) == ("payback", "rules") and spy.calls == []  # rules handled it, no model call
    assert ag.choose_tool("hmm tell me something", {}, FakeLLM({"tool": "recommend"})) == ("recommend", "llm")
    assert ag.choose_tool("hmm tell me something", {}, FakeLLM({"tool": "propose_booking"})) == ("help", "rules")  # no booking words
    assert ag.choose_tool("hello", {}, FakeLLM({"tool": "transfer_money"})) == ("help", "rules")  # not in the tool list


def test_affordability_numbers_come_from_engine():
    a = Assumptions()
    out = ag.handle("Can I afford NIT Calicut with 8 lakh savings?", {}, "en", a, "o1", None)
    plan = funding_plan(get_college("nit-calicut").fees.totalFourYearCostINR, 800_000, 0, a)
    assert out["tool"] == "affordability" and f"{plan['total_deficit_inr']:,}" in out["reply"] and f"{plan['loan']['emi_inr']:,}" in out["reply"]
    assert 360_000 < plan["total_deficit_inr"] < 370_000  # hand check: 11,63,500 - 8,00,000 = 3,63,500 (+-rounding)


def test_hindi_message_gets_hindi_reply():
    out = ag.handle("NIT Calicut के बारे में बताओ", {}, "en", Assumptions(), "o1", None)
    assert out["language"] == "hi" and "लागत" in out["reply"]


def test_phrasing_guard_rejects_changed_numbers():
    base = "NIT Calicut: total cost ₹11,63,500 and EMI ₹12,000."
    assert ag.phrase(base, FakeLLM(text_out="Calicut costs ₹11,63,500 overall; the EMI is ₹12,000."))[1] is True
    assert ag.phrase(base, FakeLLM(text_out="Calicut costs ₹10,00,000; EMI ₹12,000."))[1] is False
    assert ag.phrase(base, FakeLLM(text_out="Calicut costs ₹11,63,500, EMI ₹12,000 and 5 years."))[1] is False
    assert ag.phrase(base, FakeLLM(text_out=None)) == (base, False)
    assert ag.phrase(base, None) == (base, False)


def test_unknown_college_asks_instead_of_guessing():
    assert "Which college" in ag.handle("can I afford it with 5 lakh savings", {}, "en", Assumptions(), "o1", None)["reply"]


# ---------- API: human-in-the-loop booking ----------
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
    app.dependency_overrides[get_llm] = lambda: None
    ag.PENDING.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_agent_never_creates_an_order_without_confirmation(env):
    c = env
    r = c.post("/api/agent/chat", json={"message": "Please book a JoSAA session for me"}, headers=H).json()
    assert r["tool"] == "propose_booking" and r["pending_action"]["program_id"] == "josaa-audit"
    assert c.get("/api/bookings", headers=H).json() == []  # nothing created yet
    assert c.post("/api/agent/confirm", json={"action_id": r["pending_action"]["id"]}, headers=H2).status_code == 404  # wrong visitor
    ok = c.post("/api/agent/confirm", json={"action_id": r["pending_action"]["id"]}, headers=H).json()
    assert ok["booking"]["status"] == "pending" and ok["booking"]["usd"] == "35.99" and ok["booking"]["paypal_order_id"].startswith("MOCK-ORDER")
    assert c.post("/api/agent/confirm", json={"action_id": r["pending_action"]["id"]}, headers=H).status_code == 404  # single use


def test_pending_action_expires(env):
    c = env
    r = c.post("/api/agent/chat", json={"message": "book a session"}, headers=H).json()
    ag.PENDING[r["pending_action"]["id"]]["exp"] = time.time() - 1
    assert c.post("/api/agent/confirm", json={"action_id": r["pending_action"]["id"]}, headers=H).status_code == 404


def test_intake_endpoint_and_requires_client_id_for_chat(env):
    c = env
    assert c.post("/api/intake", json={"text": "99 percentile budget 15 lakh south"}).json()["profile"]["region"] == "South"
    assert c.post("/api/agent/chat", json={"message": "hi"}).status_code == 400
