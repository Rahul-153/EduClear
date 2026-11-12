"""Cutoff-only options (PLAN_VIEWS_AND_DATA.md B2): rank matching on the shipped JoSAA 2025 table, no invented figures."""
import pytest
from fastapi.testclient import TestClient

from backend.app.data import cutoff_rows
from backend.app.engines.assumptions import Assumptions
from backend.app.main import app
from backend.app.services import cutoff_options as co
from backend.app.services.recommend import recommend

client = TestClient(app)
A = Assumptions()

# These tests need the JoSAA table and partial records now archived in data/_archive_verified (D-53). They run again once those are restored.
pytestmark = pytest.mark.skipif(not cutoff_rows(), reason="needs data/_archive_verified restored")


def items(r):
    return r["cutoff_only"]["items"]


def test_audited_names_exist_in_the_table():
    names = {r["institute"] for r in cutoff_rows()}
    assert set(co.AUDITED_JOSAA_NAMES.values()) <= names


def test_audited_deck_is_unchanged_and_audited_institutes_are_not_repeated():
    r = recommend("Computer Science", 18, "All", A, percentile=99.75)
    assert r["deck"]["safe_anchor"]["id"] == "nit-calicut" and r["deck"]["safe_anchor"]["data_level"] == "audited"
    assert not {x["institute"] for x in items(r)} & set(co.AUDITED_JOSAA_NAMES.values())


def test_cutoff_only_rows_carry_a_rank_and_no_money_or_placement_fields():
    r = recommend("Computer Science", 18, "All", A, percentile=99.75)
    assert items(r)
    for x in items(r):
        assert x["data_level"] in ("cutoffs_only", "partly_verified") and x["source_url"].startswith("https://josaa.")
        assert not {"four_year_cost_inr", "median_base_lpa", "payback", "placed", "headline_ctc_lpa"} & set(x)  # never at the top level
        assert ("placement" in x) == (x["data_level"] == "partly_verified")


def test_every_row_traces_to_a_published_row_and_tier_follows_the_rank():
    r = recommend("Computer Science", 18, "All", A, percentile=97)
    rows = cutoff_rows()
    for x in items(r):
        assert any(w["institute"] == x["institute"] and w["program"] == x["program"] and w["quota"] == x["quota"]
                   and w["seat_type"] == x["seat_type"] and w["closing"] == x["closing_rank"] for w in rows)
        assert x["user_rank"] <= A.reach_margin * x["closing_rank"]
        assert (x["tier"] == "Safe") == (x["user_rank"] <= A.safe_margin * x["closing_rank"])


def test_lower_percentile_still_gets_options_when_the_audited_deck_is_empty():
    r = recommend("Computer Science", 18, "All", A, percentile=94.2)
    assert all(v is None for v in r["deck"].values()) and len(items(r)) > 0


def test_iits_need_the_students_own_advanced_rank():
    without = recommend("Computer Science", 18, "All", A, percentile=99.9)
    assert "IIT" not in {x["kind"] for x in items(without)} and without["cutoff_only"]["iits_need_rank"]
    with_rank = recommend("Computer Science", 18, "All", A, percentile=99.9, jee_advanced_rank=4000)
    assert "IIT" in {x["kind"] for x in items(with_rank)} and not with_rank["cutoff_only"]["iits_need_rank"]


def test_category_seats_need_a_category_rank():
    none_given = recommend("Mechanical", 18, "All", A, percentile=94.2, opts=dict(seat_type="SC"))
    assert items(none_given) == []
    given = recommend("Mechanical", 18, "All", A, percentile=94.2, opts=dict(seat_type="SC", category_rank=9000))
    assert items(given) and all(x["seat_type"] == "SC" for x in items(given))


def test_female_students_see_at_least_the_gender_neutral_options():
    base = {x["institute"] for x in items(recommend("Computer Science", 18, "All", A, percentile=96))}
    fem = {x["institute"] for x in items(recommend("Computer Science", 18, "All", A, percentile=96, opts=dict(gender="Female")))}
    assert base <= fem


def test_other_branch_shows_cutoffs_only_with_a_message():
    r = recommend("Mechanical", 18, "All", A, percentile=96)
    assert r["supported"] and r["matches"] == [] and "Computer Science only" in r["message"] and items(r)


def test_unknown_stream_is_still_unsupported_and_api_validates_new_fields():
    assert client.post("/api/recommend", json={"stream": "MBA"}).json()["supported"] is False
    ok = client.post("/api/recommend", json={"percentile": 94.2, "seat_type": "EWS", "category_rank": 5000, "gender": "Female"})
    assert ok.status_code == 200 and "cutoff_only" in ok.json()
    assert client.post("/api/recommend", json={"seat_type": "GENERAL"}).status_code == 422


# ---- partly verified records (B4) ----
import json  # noqa: E402

from backend.app.data import PARTIAL_DIR, partial_colleges  # noqa: E402
from scripts.partial_model import PartialCollege, gate_errors  # noqa: E402


def test_every_partial_record_passes_the_gates_and_joins_the_table():
    names = {r["institute"] for r in cutoff_rows()}
    recs = list(partial_colleges().values())
    assert recs
    for r in recs:
        assert r.josaaName in names and not gate_errors(r)
        assert r.verifiedFields == ["placement"] and "totalCost" in r.notVerified


def test_gates_catch_inconsistent_placement():
    rec = next(iter(partial_colleges().values())).model_dump()
    rec["placement"]["placed"] = rec["placement"]["eligible"] + 1
    assert any("placed must be" in e for e in gate_errors(PartialCollege.model_validate(rec)))
    rec = next(iter(partial_colleges().values())).model_dump()
    rec["placement"]["eligible"] += 1
    assert any("D-09" in e for e in gate_errors(PartialCollege.model_validate(rec)))


def test_partly_verified_iit_row_carries_placement_but_no_cost():
    r = recommend("Computer Science", 18, "All", A, percentile=99.9, jee_advanced_rank=3000)
    partly = [x for x in items(r) if x["data_level"] == "partly_verified"]
    assert partly
    for x in partly:
        rec = partial_colleges()[x["institute"]]
        assert x["placement"]["placed"] == rec.placement.placed and x["placement"]["eligible"] == rec.placement.eligible
        assert x["placement"]["median_base_lpa"] == round(rec.placement.medianSalaryInr / 100_000, 2)
        assert "four_year_cost_inr" not in x and "payback" not in x


def test_partial_files_match_their_model_on_disk():
    for f in PARTIAL_DIR.glob("*.json"):
        assert PartialCollege.model_validate(json.loads(f.read_text())).id == f.stem
