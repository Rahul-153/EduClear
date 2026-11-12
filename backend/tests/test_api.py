import pytest
from fastapi.testclient import TestClient

from backend.app.config import ROOT
from backend.app.main import app

client = TestClient(app)


def test_health_and_list():
    rows = client.get("/api/colleges").json()
    assert rows and client.get("/api/health").json() == {"status": "ok", "colleges": len(rows)}
    assert [r["nirf_rank"] for r in rows] == sorted(r["nirf_rank"] for r in rows)
    assert all(r["source_url"].startswith("http") for r in rows)


def test_college_and_sources():
    c = client.get("/api/colleges/nit-calicut").json()
    f = c["fees"]
    assert f["totalFourYearCostINR"] == 4 * (f["tuitionAnnual"] + f["mandatoryInstituteFeesAnnual"] + f["hostelAndMessAnnual"] + f["estimatedLivingAnnual"])
    s = client.get("/api/colleges/nit-calicut/sources").json()
    assert s["verification"] == "Supplied dataset, not audited" and s["provenance"] == {}  # no source documents exist for it
    assert client.get("/api/colleges/nope").status_code == 404


def test_recommend_deck_and_filters():
    r = client.post("/api/recommend", json={"percentile": 99.95, "budget_lakhs": 12, "region": "All"}).json()
    assert r["supported"] and r["matches"] and all(m["four_year_cost_inr"] <= 1_200_000 for m in r["matches"])
    assert r["deck"]["safe_anchor"]["fit"]["tier"] == "Safe" and all(m["data_level"] == "supplied" for m in r["matches"])
    assert "cutoff_only" not in r  # Computer Science uses the supplied records only; the JoSAA table serves the other branches (D-59)


def test_other_branches_show_cutoff_only_options_from_the_josaa_table():
    for stream, word in (("Mechanical", "Mechanical"), ("Civil", "Civil"), ("Electrical", "Electrical"), ("Electronics & Communication", "Electronics")):
        r = client.post("/api/recommend", json={"stream": stream, "percentile": 97, "budget_lakhs": 12, "region": "All"}).json()
        rows = r["cutoff_only"]["items"]
        assert r["supported"] and rows and all(word in x["program"] for x in rows), stream  # branch cards, if any, are covered by the next test
    top = client.post("/api/recommend", json={"stream": "Civil", "percentile": 99.9, "budget_lakhs": 12, "region": "All"}).json()["cutoff_only"]["items"]
    assert any(x["institute"] == "National Institute of Technology Calicut" for x in top)  # no institute is left out for these branches
    assert client.post("/api/recommend", json={"stream": "Astrology", "percentile": 97, "budget_lakhs": 12, "region": "All"}).json()["supported"] is False
    south = client.post("/api/recommend", json={"percentile": 99.75, "budget_lakhs": 40, "region": "South"}).json()
    assert {m["region"] for m in south["matches"]} == {"South"}
    unsupported = client.post("/api/recommend", json={"stream": "MBA"}).json()
    assert unsupported["supported"] is False


def test_roi_finance_alignment():
    roi = client.post("/api/roi", json={"college_id": "mnit-jaipur"}).json()
    assert roi["payback"]["payback_months"] > roi["payback"]["payback_months_gross_pay"]
    cost = client.get("/api/colleges/mnit-jaipur").json()["fees"]["totalFourYearCostINR"]
    fin = client.post("/api/finance/plan", json={"college_id": "mnit-jaipur", "family_savings": 500_000}).json()
    assert abs(fin["total_deficit_inr"] - (cost - 500_000)) <= 8
    ok = dict(brand_prestige=3, branch_passion=3, location_safety=3, budget_strictness=3)
    assert client.post("/api/alignment", json={"student": ok, "parent": ok}).json()["alignment_score"] == 100
    assert client.post("/api/alignment", json={"student": {"x": 1}, "parent": ok}).status_code == 422


def test_cards_carry_accreditation_and_zero_commission():
    r = client.get("/api/colleges").json()
    assert all(x["commercial_relationship"].startswith("None") and x["accreditation"] for x in r)


@pytest.mark.skipif(not (ROOT / "frontend" / "dist").exists(), reason="frontend not built")
def test_index_is_revalidated_and_hashed_assets_are_cached():
    c = TestClient(app)
    assert c.get("/").headers["cache-control"] == "no-cache"
    asset = next((ROOT / "frontend" / "dist" / "assets").glob("index-*.css")).name
    assert "immutable" in c.get(f"/assets/{asset}").headers["cache-control"]


def test_branch_placement_drives_cards_for_other_branches():
    r = client.post("/api/recommend", json={"stream": "Mechanical", "percentile": 99, "budget_lakhs": 40, "region": "All", "jee_advanced_rank": 500}).json()
    by = {m["id"]: m for m in r["matches"]}
    assert {"iit-bombay", "nit-trichy", "dtu-delhi", "bits-pilani"} <= set(by)
    b = by["iit-bombay"]  # branch_placements.csv: IIT Bombay ME 148 placed of 170, median 18.5 LPA
    assert (b["placed"], b["eligible"], b["median_base_lpa"], b["branch_scope"]) == (148, 170, 18.5, True)
    assert b["payback"]["median_base_lpa"] == 18.5 and b["fit"]["tier"] is not None  # tier from the official JoSAA ME row
    assert by["dtu-delhi"]["fit"]["tier"] is None and by["dtu-delhi"]["fit"]["reason"]  # not in JoSAA: no rank, said so
    shown = {x["institute"] for x in r["cutoff_only"]["items"]}
    assert "Indian Institute of Technology Bombay" not in shown and "National Institute of Technology, Tiruchirappalli" not in shown
    assert shown  # every other institute stays cutoff-only
    low = client.post("/api/recommend", json={"stream": "Mechanical", "percentile": 99, "budget_lakhs": 12, "region": "All"}).json()
    assert "iit-bombay" not in {m["id"] for m in low["matches"]} and "nit-trichy" in {m["id"] for m in low["matches"]}  # the budget filter applies
    assert "Mechanical" in r["message"]


def test_computer_science_uses_the_branch_row_when_there_is_one():
    r = client.post("/api/recommend", json={"percentile": 99.95, "budget_lakhs": 40, "region": "All"}).json()
    by = {m["id"]: m for m in r["matches"]}
    assert (by["nit-trichy"]["placed"], by["nit-trichy"]["eligible"], by["nit-trichy"]["median_base_lpa"]) == (118, 120, 24.5)  # CSE row

