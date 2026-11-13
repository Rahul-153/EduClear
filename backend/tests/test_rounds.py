"""Round-by-round counselling (PLAN_ROUND_COPILOT.md): history and rules only, numbers equal to the published ranks."""
import re

import pytest
from fastapi.testclient import TestClient

from backend.app.config import ROOT
from backend.app.data import round_history
from backend.app.engines import rounds as eng
from backend.app.main import app
from backend.app.services import admissions, cutoff_options
from backend.app.services import rounds as svc
from scripts import backtest_rounds, export_round_history

client = TestClient(app)
GN = "Gender-Neutral"
CALICUT = {"institute": "National Institute of Technology Calicut", "program": "Computer Science and Engineering (4 Years, Bachelor of Technology)", "quota": "OS"}
PATNA = {"institute": "National Institute of Technology Patna", "program": "Computer Science and Engineering (4 Years, Bachelor of Technology)", "quota": "OS"}
FEE = {"generalInr": 30000, "reservedInr": 15000}


# ---- engine, hand-computed -------------------------------------------------------------------------------------------
YEARS = {2021: [100, 104, 104, 104, 104, 110], 2022: [200, 200, 200, 200, 200, 200], 2023: [None, 50, 60, None, None, None],
         2024: [300, 330, 320, 310, 305, None]}


def test_movement_relative_to_this_rounds_closing_rank():
    # Student at 105 with this round's closing at 100 is short by 5%. Moves from round 1: 2021 +10%, 2022 0%, 2024 +10%; 2023 has no round 1.
    m = eng.movement(YEARS, 1, 105, [2020, 2021, 2022, 2023, 2024], closing_now=100)
    assert (m["basis"], m["short_by_pct"], m["years_reached"], m["years_with_data"]) == ("relative_move", 5.0, 2, 3)
    assert [y["available"] for y in m["years"]] == [False, True, True, False, True]
    assert m["years"][1] == {"year": 2021, "available": True, "closing_at_round": 100, "highest_closing_from_round": 110, "moved_pct": 10.0, "reached": True}
    assert m["years"][4]["highest_closing_from_round"] == 330  # the peak, not the last round: a seat taken in round 2 is kept


def test_movement_uses_only_rounds_from_this_one_on():
    m = eng.movement(YEARS, 3, 105, [2024], closing_now=100)  # from round 3 the 2024 peak is 320 on 320: no move
    assert m["years"][0]["moved_pct"] == 0.0 and m["years_reached"] == 0


def test_movement_without_this_rounds_closing_rank_compares_the_rank_itself():
    m = eng.movement(YEARS, 1, 105, [2021, 2022], closing_now=None)
    assert (m["basis"], m["short_by_pct"]) == ("absolute_rank", None)
    assert [y["reached"] for y in m["years"]] == [True, True]  # 110 and 200 are both beyond 105


def test_held_choice_keeps_a_seat_once_reached_and_skips_choices_without_a_rank():
    a, b = [10, 10, 12, 9, 9, 9], [50, 50, 50, 50, 50, 50]
    assert eng.held_choice([a, b], [11, 11], 2) == 1
    assert eng.held_choice([a, b], [11, 11], 3) == 0
    assert eng.held_choice([a, b], [11, 11], 5) == 0  # closing fell back to 9, the seat is kept
    assert eng.held_choice([a, b], [None, 60], 6) is None


def test_option_follows_the_list_and_the_round():
    x, y = "Institute X", "Institute Y"
    assert eng.option(None, [x, y], 1, 5)["action"] == "no_seat"
    assert eng.option(0, [x, y], 1, 5)["action"] == "freeze_only"
    assert eng.option(1, [x, x], 1, 5)["action"] == "slide"
    assert eng.option(2, [x, y, x], 1, 5)["action"] == "float"
    assert eng.option(1, [x, y], 5, 5)["action"] == "last_round"
    assert "freeze_is_final" in eng.option(1, [x, y], 2, 5)["rule_ids"]


def test_money_at_risk():
    m = eng.money_at_risk("NIT", "OPEN", 2, 5, FEE, 7000)
    assert (m["seat_acceptance_fee_inr"], m["refund_on_withdrawal_inr"], m["withdrawal_open_this_round"], m["withdrawal_last_round"]) == (30000, 23000, True, 5)
    assert eng.money_at_risk("NIT", "OPEN", 1, 5, FEE, 7000)["withdrawal_open_this_round"] is False  # opens in round 2
    iit = eng.money_at_risk("IIT", "SC", 5, 5, FEE, 7000)
    assert (iit["seat_acceptance_fee_inr"], iit["refund_on_withdrawal_inr"], iit["withdrawal_open_this_round"], iit["withdrawal_last_round"]) == (15000, 8000, False, 4)
    assert eng.money_at_risk(None, "OPEN", 3, 5, FEE, 7000) == {"seat_acceptance_fee_inr": 0, "status": "no_seat"}


# ---- sourced files ---------------------------------------------------------------------------------------------------
def test_rule_ids_used_by_the_engine_exist_and_fee_matches_the_timeline():
    ids = {r["id"] for r in admissions.josaa_rules()["rules"]}
    used = set(eng.money_at_risk("NIT", "OPEN", 2, 5, FEE, 7000)["rule_ids"]) | set(eng.money_at_risk("IIT", "OPEN", 2, 5, FEE, 7000)["rule_ids"])
    for held, insts, rnd in ((0, ["a"], 1), (1, ["a", "a"], 1), (1, ["a", "b"], 1), (1, ["a", "b"], 5)):
        used |= set(eng.option(held, insts, rnd, 5)["rule_ids"])
    assert used <= ids
    assert "Rs. 7000" in admissions.timeline_data()["seatAcceptanceFee"]["rule_text"] and admissions.josaa_rules()["withdrawalChargeInr"] == 7000


def test_every_quoted_rule_is_in_the_saved_document():
    txt = ROOT / "data" / "sources" / "_admissions" / "josaa2026_business_rules.txt"
    if not txt.exists():
        pytest.skip("evidence snapshots are not in git")
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    doc = norm(re.sub(r"\n\s*\d{1,3}\s*\n", "\n", txt.read_text()))  # page-number lines removed
    for r in admissions.josaa_rules()["rules"]:
        assert norm(r["quote"]) in doc, r["id"]


def test_export_keeps_the_same_programmes_as_the_cutoff_matching():
    assert export_round_history.BRANCHES.pattern == "|".join(cutoff_options.BRANCH_GROUPS.values())
    assert export_round_history.EXCLUDE.pattern == cutoff_options._EXCLUDE.pattern
    assert export_round_history.SEAT_TYPES == cutoff_options.SEAT_TYPES


# ---- shipped round history -------------------------------------------------------------------------------------------
pytestmark_data = pytest.mark.skipif(not round_history()["seats"], reason="needs data/round_history.sqlite")


@pytestmark_data
def test_shipped_rows_equal_the_published_ranks():
    h = round_history()
    assert h["rounds"] == {2020: 6, 2021: 6, 2022: 6, 2023: 6, 2024: 5, 2025: 6}
    seat = h["seats"][(CALICUT["institute"], CALICUT["program"], "OS", "OPEN", GN)]
    assert seat["years"][2025] == [4678, 4846, 4886, 4957, 4966, 5222]  # read from the JoSAA 2025 archive pages
    assert seat["years"][2024] == [4088, 4147, 4147, 4185, 4482, None]  # the archive has five rounds for 2024


@pytestmark_data
def test_replay_2025_walks_from_patna_to_calicut():
    kw = dict(year=2025, choices=[CALICUT, PATNA], seat_type="OPEN", gender=GN, main_rank=5000, advanced_rank=None)
    r1 = svc.advise(rnd=1, **kw)
    assert (r1["mode"], r1["held"], r1["option"]["action"], r1["history_years"]) == ("replay", 1, "float", [2020, 2021, 2022, 2023, 2024])
    hist = r1["choices"][0]["history"]
    # 5000 on a round-1 closing of 4678 is short by 6.9%. Moves after round 1: 2020 3682/2869, 2021 3436/2717, 2022 4521/3843, 2023 5256/4455, 2024 4482/4088.
    assert (hist["closing_now"], hist["short_by_pct"]) == (4678, 6.9)
    assert [y["moved_pct"] for y in hist["years"]] == [28.3, 26.5, 17.6, 18.0, 9.6]
    assert (hist["years_reached"], hist["years_with_data"]) == (5, 5)
    assert "history" not in r1["choices"][1]  # no history for the seat held or anything below it
    assert r1["money"]["refund_on_withdrawal_inr"] == 23000 and {x["id"] for x in r1["rules"]} >= {"float", "withdrawal_refund"}
    assert svc.advise(rnd=5, **kw)["held"] == 1
    r6 = svc.advise(rnd=6, **kw)
    assert (r6["held"], r6["option"]["action"]) == (0, "freeze_only")


@pytestmark_data
def test_iit_choices_need_an_advanced_rank_and_never_use_the_main_rank():
    iit = {"institute": "Indian Institute of Technology Bombay", "program": "Computer Science and Engineering (4 Years, Bachelor of Technology)", "quota": "AI"}
    r = svc.advise(year=2025, rnd=1, choices=[iit, PATNA], seat_type="OPEN", gender=GN, main_rank=50, advanced_rank=None)
    assert r["needs_rank"] == ["jee_advanced"] and r["choices"][0]["history"] is None and r["held"] == 1


@pytestmark_data
def test_own_round_uses_the_latest_five_years_and_the_typed_closing_rank():
    body = {"year": 2027, "round": 2, "choices": [{**CALICUT, "closing_this_round": 5000}, PATNA], "main_rank": 5100, "allotted": 1}
    r = client.post("/api/rounds/advise", json=body).json()
    assert (r["mode"], r["total_rounds"], r["history_years"]) == ("own_round", 5, [2021, 2022, 2023, 2024, 2025])
    assert r["choices"][0]["history"]["basis"] == "relative_move" and r["choices"][0]["history"]["short_by_pct"] == 2.0
    del body["choices"][0]["closing_this_round"]
    assert client.post("/api/rounds/advise", json=body).json()["choices"][0]["history"]["basis"] == "absolute_rank"
    assert client.post("/api/rounds/advise", json={**body, "no_seat": True, "allotted": None}).json()["option"]["action"] == "no_seat"


@pytestmark_data
def test_api_rejects_bad_input_and_lists_seats():
    ok = {"year": 2025, "round": 1, "choices": [CALICUT], "main_rank": 5000}
    assert client.post("/api/rounds/advise", json={**ok, "choices": [{**CALICUT, "quota": "XX"}]}).status_code == 422
    assert client.post("/api/rounds/advise", json={**ok, "round": 7}).status_code == 422
    assert client.post("/api/rounds/advise", json={**ok, "year": 2027}).status_code == 422  # own round: must say what was allotted
    seats = client.get("/api/rounds/seats", params={"year": 2025}).json()["items"]
    assert {"inst_type": "NIT", **CALICUT} in seats and all("(4 Years" in s["program"] for s in seats)
    assert client.get("/api/rounds/cycles").json()["replay_years"][0] == 2025


@pytestmark_data
def test_backtest_runs_and_counts_cases():
    r = backtest_rounds.run(2025)
    cells = r["by_gap"]["relative"][1.05]
    assert r["history_years"] == [2020, 2021, 2022, 2023, 2024] and sum(n for n, _ in cells.values()) > 10_000
    assert all(k <= n for n, k in cells.values())
