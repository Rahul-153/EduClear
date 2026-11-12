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
    assert r["profile"]["region"] is None and r["profile"]["home_state"] is None  # 'Chennai' is not a region word (T-15.07)
    assert r["profile"]["stream"] == "Computer Science"  # 'computers' names the stream (rules read it)
    r2 = intake.parse("looking for colleges in the south, whatever the fee", FakeLLM({"percentile": None, "budget_lakhs": None, "region": "South", "stream": None, "home_state": None}))
    assert r2["sources"].get("region") == "rules"
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
    cost = get_college("nit-calicut").fees.totalFourYearCostINR
    assert abs(plan["total_deficit_inr"] - (cost - 800_000)) <= 8  # hand check: cost minus savings (+-rounding)


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


def test_intake_reads_every_branch_and_flags_salary_and_mba():
    r = intake.parse("Electrical, 10 lpa in north india with JEE advanced rank 1")
    assert r["profile"]["stream"] == "Electrical" and r["profile"]["region"] == "North" and r["profile"]["jee_advanced_rank"] == 1
    assert r["profile"]["budget_lakhs"] is None and r["salary_not_budget"] and not r["unsupported_stream"]  # LPA is a salary, never a budget
    for text, want in (("mechanical engineering please", "Mechanical"), ("civil, 20 lakh budget", "Civil"), ("I want ECE", "Electronics & Communication"),
                       ("मैकेनिकल चाहिए", "Mechanical"), ("tell me about CSE", "Computer Science"), ("tell me about me", None)):
        assert intake.parse(text)["profile"]["stream"] == want, text
    assert intake.parse("MBA please")["unsupported_stream"] is True



# ---------- Phase 15: router, branch, memory, matching ----------
@pytest.mark.parametrize("msg", ["what is the weather today", "tell me a joke", "who won the match"])
def test_off_topic_with_percentile_is_help_not_recommend(msg):
    assert ag.route_rules(msg, {"percentile": 94}) == "help"
    assert ag.choose_tool(msg, {"percentile": 94}, FakeLLM({"tool": "payback"}))[0] == "payback"  # model gets the call


def test_copilot_uses_chosen_branch_and_mba_is_unavailable():
    from backend.app.services.recommend import recommend
    prof = {"percentile": 94, "budget_lakhs": 18, "stream": "Mechanical"}
    out = ag.handle("suggest colleges for me", prof, "en", Assumptions(), "o1", None)
    ref = recommend("Mechanical", 18, "All", Assumptions(), {}, percentile=94)
    names = [v["short_name"] for v in ref["deck"].values() if v] or [i["institute"] for i in ref["cutoff_only"]["items"][:3]]
    assert names and all(n in out["reply"] for n in names)
    assert "not available" in ag.handle("suggest colleges", {**prof, "stream": "MBA"}, "en", Assumptions(), "o1", None)["reply"]


def test_memory_between_turns():
    first = ag.handle("Tell me about NIT Calicut", {}, "en", Assumptions(), "o1", None)
    assert first["profile"]["last_college"] == "nit-calicut"
    second = ag.handle("can I afford it with 5 lakh savings", first["profile"], "en", Assumptions(), "o1", None)
    assert second["tool"] == "affordability" and "NIT Calicut" in second["reply"]


@pytest.mark.parametrize("msg,cid", [("tell me about IIIT Hyderabad", "iiit-hyderabad"), ("tell me about IIT Hyderabad", "iit-hyderabad"),
                                     ("IIIT Delhi fees", "iiit-delhi"), ("IIT Delhi fees", "iit-delhi"), ("is DTU worth it", "dtu-delhi")])
def test_college_matching_is_exact(msg, cid):
    assert ag._find_colleges(msg) == [cid]


def test_bare_city_asks_which_one():
    r = ag.handle("tell me about Hyderabad placement", {}, "en", Assumptions(), "o1", None)["reply"]
    assert "Which one" in r and "IIT Hyderabad" in r and "IIIT Hyderabad" in r


# ---------- T-15.05: deadlines, refund, choice order, compare ----------
@pytest.mark.parametrize("msg,tool", [
    ("What is the refund deadline for JoSAA?", "refund"), ("how do I withdraw my seat", "refund"), ("रिफंड कैसे मिलेगा", "refund"),
    ("Is my choice order ok? IIT Delhi then IIT Bombay", "check_choice_order"),
    ("when is the next JoSAA round", "deadlines"), ("last date for registration", "deadlines"),
    ("compare NIT Calicut vs MNIT Jaipur", "compare"), ("NIT Calicut तुलना MNIT Jaipur", "compare"),
])
def test_new_tool_routing(msg, tool):
    assert ag.route_rules(msg, {"percentile": 94}) == tool


def test_refund_reply_uses_policy_tiers_and_amount():
    from backend.app.engines.refund import usable_tiers
    from backend.app.services.admissions import refund_policy
    out = ag.handle("refund rules for my 2 lakh deposit", {}, "en", Assumptions(), "o1", None)
    for t in usable_tiers(refund_policy()):
        assert f"{t['refund_percent']}%" in out["reply"] and f"₹{round(200000 * t['refund_percent'] / 100):,}" in out["reply"]


def test_deadlines_reply_matches_timeline():
    from backend.app.services.admissions import timeline
    out = ag.handle("what is the next deadline", {}, "en", Assumptions(), "o1", None)
    nxt = [e for e in timeline()["events"] if e["status"] != "past"][:3]
    assert out["tool"] == "deadlines" and (all(e["label"] in out["reply"] for e in nxt) if nxt else "passed" in out["reply"])


def test_choice_order_alert_equals_engine_and_needs_two_colleges():
    from backend.app.engines.choice import analyse
    prof = {"percentile": 99.5}
    out = ag.handle("is my choice order ok: NIT Calicut then NIT Surathkal", prof, "en", Assumptions(), "o1", None)
    ref = analyse(["nit-calicut", "nit-surathkal"], Assumptions(), percentile=99.5)
    assert out["tool"] == "check_choice_order" and all(x["message"] in out["reply"] for x in ref["alerts"])
    assert "at least two" in ag.handle("check my choice order", {}, "en", Assumptions(), "o1", None)["reply"]


def test_compare_numbers_equal_card():
    c1, c2 = get_college("nit-calicut"), get_college("mnit-jaipur")
    out = ag.handle("compare NIT Calicut vs MNIT Jaipur", {}, "en", Assumptions(), "o1", None)
    for c in (c1, c2):
        assert f"₹{c.fees.totalFourYearCostINR:,}" in out["reply"] and f"{c.placement.actuallyPlaced:,} of {c.placement.eligibleStudents:,}" in out["reply"]


# ---------- Stage 4: why line, family brief, glossary ----------
def test_why_line_numbers_equal_card():
    from backend.app.services.recommend import recommend
    r = recommend("Computer Science", 25, "All", Assumptions(), {}, percentile=96)
    assert r["matches"]
    for x in r["matches"]:
        w = x["why"]
        assert f"{x['median_base_lpa']} LPA" in w["en"] and f"{x['payback']['payback_months']} months" in w["en"]
        assert f"{x['median_base_lpa']} LPA" in w["hi"]
        under = 25 * 100_000 - x["four_year_cost_inr"]
        assert (f"₹{under:,} under your budget" in w["en"]) == (under >= 0)


def test_brief_identical_answers_none_and_gap_names_real_college_and_emi():
    from backend.app.services import brief
    a = Assumptions()
    same = {k: 0 for k in ("brand_prestige", "branch_passion", "location_safety", "budget_strictness")}
    assert brief.build(same, ["nit-calicut"], a) == []
    pts = brief.build({**same, "budget_strictness": 3}, ["nit-calicut", "dtu-delhi"], a)
    c = get_college("nit-calicut")
    plan = funding_plan(c.fees.totalFourYearCostINR, 0, 0, a)
    assert len(pts) == 1 and "NIT Calicut" in pts[0]["en"] and f"₹{plan['loan']['emi_inr']:,}" in pts[0]["en"] and f"₹{plan['loan']['emi_inr']:,}" in pts[0]["hi"]
    two = brief.build({**same, "brand_prestige": 2}, ["nit-calicut", "dtu-delhi"], a)
    assert "NIT Calicut" in two[0]["en"] and "DTU Delhi" in two[0]["en"]


def test_alignment_endpoint_returns_brief(env):
    r = env.post("/api/alignment", json={"student": {"brand_prestige": 5, "branch_passion": 3, "location_safety": 3, "budget_strictness": 1},
                                         "parent": {"brand_prestige": 1, "branch_passion": 3, "location_safety": 3, "budget_strictness": 5},
                                         "college_ids": ["nit-calicut", "dtu-delhi"]}).json()
    assert {p["dimension"] for p in r["brief"]} == {"brand_prestige", "budget_strictness"} and len(r["brief"]) == 2
    assert env.post("/api/alignment", json={"student": {}, "parent": {}}).status_code == 422


@pytest.mark.parametrize("msg,tid", [("what does median salary mean", "median-salary"), ("होम स्टेट कोटा क्या है", "home-state-quota"),
                                     ("what does EMI mean", "emi"), ("freeze float meaning", "freeze-float-slide")])
def test_glossary_routes_and_answers_with_curated_text(msg, tid):
    from backend.app.services import glossary
    assert ag.route_rules(msg, {"percentile": 94}) == "explain_term"
    out = ag.handle(msg, {}, "en", Assumptions(), "o1", None)
    e = next(x for x in glossary.entries() if x["id"] == tid)
    assert out["data"]["id"] == tid and e["definition"]["hi" if out["language"] == "hi" else "en"] in out["reply"] and ("स्रोत" if out["language"] == "hi" else "Source:") in out["reply"]


def test_glossary_refuses_unrelated_and_model_only_picks_among_candidates():
    from backend.app.services import glossary
    assert ag.route_rules("what does the weather mean", {}) == "help"
    assert glossary.lookup("tell me a joke") is None
    cands = [e["id"] for e, _ in glossary.rank("closing rank cutoff quota")]
    assert glossary.lookup("closing rank cutoff quota", FakeLLM({"id": "escrow"}))["id"] == cands[0]  # not a candidate: ignored
    if len(cands) > 1:
        assert glossary.lookup("closing rank cutoff quota", FakeLLM({"id": cands[1]}))["id"] == cands[1]


def test_glossary_entries_have_both_languages_and_a_source():
    from backend.app.services import glossary
    es = glossary.entries()
    assert len(es) >= 20 and len({e["id"] for e in es}) == len(es)
    for e in es:
        assert e["definition"]["en"] and e["definition"]["hi"] and e["term"]["hi"] and e["source"]["label"]
        if e["source"]["url"]:
            assert e["source"]["url"].startswith("https://")
