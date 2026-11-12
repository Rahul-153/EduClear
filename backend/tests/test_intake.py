"""Golden set (T-15.09, FR-01): 10 English + 10 Hindi sentences, pass mark 90%; guard tests (T-15.07); timeout and rate limit (T-15.08)."""
import time

import httpx
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.data import get_college
from backend.app.engines.assumptions import Assumptions
from backend.app.engines.emi import funding_plan
from backend.app.llm import client as llm_client
from backend.app.llm.client import HostedLLM, OllamaLLM
from backend.app.main import app
from backend.app.services import agent as ag
from backend.app.services import intake
from backend.app.llm.client import get_llm

# (text, expected non-null fields)
EN = [
    ("I got 93 percentile in JEE Main, budget 18 lakhs", {"percentile": 93, "budget_lakhs": 18}),
    ("99.5 percentile, budget 0.3 crore, from Kerala", {"percentile": 99.5, "budget_lakhs": 30, "home_state": "Kerala"}),
    ("my percentile is 96.4 and we want south india", {"percentile": 96.4, "region": "South"}),
    ("94.2 percentile, 25 lakh budget, CSE", {"percentile": 94.2, "budget_lakhs": 25, "stream": "Computer Science"}),
    ("mechanical engineering, 20 lakhs total, north", {"budget_lakhs": 20, "stream": "Mechanical", "region": "North"}),
    ("JEE advanced rank 1200, budget 1 crore", {"jee_advanced_rank": 1200, "budget_lakhs": 100}),
    ("bitsat 310, 99 percentile, west india", {"bitsat_score": 310, "percentile": 99, "region": "West"}),
    ("civil, from Tamil Nadu, 12 lakh budget", {"stream": "Civil", "home_state": "Tamil Nadu", "budget_lakhs": 12}),
    ("ECE please, 97 percentile", {"stream": "Electronics & Communication", "percentile": 97}),
    ("West Bengal student with 91 percentile and 15 lakhs", {"home_state": "West Bengal", "percentile": 91, "budget_lakhs": 15}),
]
HI = [
    ("मेरे JEE Main में 99.5 पर्सेंटाइल हैं, बजट १८ लाख है", {"percentile": 99.5, "budget_lakhs": 18}),
    ("९३ पर्सेंटाइल, दक्षिण भारत में कंप्यूटर साइंस चाहिए", {"percentile": 93, "region": "South", "stream": "Computer Science"}),
    ("बजट 25 लाख, राजस्थान से हूँ", {"budget_lakhs": 25, "home_state": "Rajasthan"}),
    ("मैकेनिकल चाहिए, बजट १५ लाख", {"stream": "Mechanical", "budget_lakhs": 15}),
    ("बजट 1 करोड़, 98 पर्सेंटाइल", {"budget_lakhs": 100, "percentile": 98}),
    ("सिविल, उत्तर भारत, 10 लाख", {"stream": "Civil", "region": "North", "budget_lakhs": 10}),
    ("mera 94 percentile hai, budget 10 lakh", {"percentile": 94, "budget_lakhs": 10}),
    ("मेरा बिटसैट 320 है और 97 पर्सेंटाइल", {"bitsat_score": 320, "percentile": 97}),
    ("केरल से, इलेक्ट्रिकल, ९० पर्सेंटाइल", {"home_state": "Kerala", "stream": "Electrical", "percentile": 90}),
    ("एडवांस्ड रैंक 850, बजट 30 लाख", {"jee_advanced_rank": 850, "budget_lakhs": 30}),
]


def test_golden_intake_pass_mark_90_percent():
    bad = []
    for text, want in EN + HI:
        got = intake.parse(text)["profile"]
        if any(got.get(k) != v for k, v in want.items()):
            bad.append((text, want, {k: got.get(k) for k in want}))
    assert len(bad) <= 2, bad  # 20 sentences, 90% pass mark


# ---------- T-15.07 guard ----------
def test_guard_rejects_unsupported_region_stream_and_budget():
    t = "i have 1.5 crore and like the mountains"
    for field, value in (("budget_lakhs", 250), ("region", "South"), ("stream", "Civil")):
        assert not intake._supported(field, value, t, t), field
    assert intake._supported("budget_lakhs", 150, t, t)
    h = "बजट 1.5 करोड़ है"
    assert intake._supported("budget_lakhs", 150, h.lower(), h.lower())
    assert not intake._supported("budget_lakhs", 200, h.lower(), h.lower())
    assert intake._supported("region", "North", "north india", "north india") and not intake._supported("region", "East", "west bengal", "west bengal")


# ---------- T-15.08 timeout and rate limit ----------
def test_chat_model_uses_short_timeout_and_stalled_model_yields_rules_answer(monkeypatch):
    seen = []

    def stall(url, json=None, headers=None, timeout=None):
        seen.append(timeout)
        raise httpx.ReadTimeout("stalled")

    monkeypatch.setattr(httpx, "post", stall)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "llm_api_key", "sk-or-test")
    monkeypatch.setattr(settings, "llm_local_fallback", False)
    monkeypatch.setattr(llm_client, "_paused_until", {})  # an earlier test may have paused this model name
    llm = get_llm()
    assert isinstance(llm, HostedLLM) and llm.timeout == settings.llm_chat_timeout_s == 8
    t = time.time()
    out = ag.handle("hmm tell me something", {}, "en", Assumptions(), "o1", llm)
    assert time.time() - t < 10 and out["tool"] == "help" and seen and set(seen) == {8}
    assert llm_client.build_llm().timeout == 90  # scripts keep the long default
    assert OllamaLLM("http://x", "m", 5).timeout == 5 and OllamaLLM("http://x", "m").timeout == 90


def test_rate_limit_returns_429_after_the_limit(monkeypatch):
    monkeypatch.setattr(settings, "agent_per_minute", 3)
    app.dependency_overrides[get_llm] = lambda: None
    try:
        c = TestClient(app)
        codes = [c.post("/api/intake", json={"text": "93 percentile"}).status_code for _ in range(4)]
        assert codes == [200, 200, 200, 429]
        assert c.post("/api/claims/check", json={"text": "IIT Delhi 100% placement"}).status_code == 429  # one shared counter per IP
    finally:
        app.dependency_overrides.clear()


# ---------- T-15.09 scripted Copilot conversations: numbers equal the engines (FR-11) ----------
def test_scripted_conversations_numbers_equal_engines():
    a = Assumptions()
    c = get_college("nit-calicut")
    plan = funding_plan(c.fees.totalFourYearCostINR, 500_000, 0, a)
    first = ag.handle("Tell me about NIT Calicut", {}, "en", a, "o", None)
    assert f"₹{c.fees.totalFourYearCostINR:,}" in first["reply"] and f"{c.placement.medianBaseSalary}" in first["reply"]
    second = ag.handle("can I afford it with 5 lakh savings", first["profile"], "en", a, "o", None)
    assert f"₹{plan['total_deficit_inr']:,}" in second["reply"] and f"₹{plan['loan']['emi_inr']:,}" in second["reply"]
    third = ag.handle("what would the EMI be", second["profile"], "en", a, "o", None)
    assert third["tool"] == "emi_compare" and "NIT Calicut" in third["reply"]  # memory: no college named, last_college used
    hi = ag.handle("NIT Calicut के बारे में बताओ", {}, "en", a, "o", None)
    assert hi["language"] == "hi" and f"₹{c.fees.totalFourYearCostINR:,}" in hi["reply"]
    cmp_ = ag.handle("compare NIT Calicut vs DTU", {}, "en", a, "o", None)
    assert f"₹{get_college('dtu-delhi').fees.totalFourYearCostINR:,}" in cmp_["reply"]
