import pytest
from fastapi.testclient import TestClient

from backend.app.config import ROOT
from backend.app.main import app

client = TestClient(app)


def test_health_and_list():
    assert client.get("/api/health").json() == {"status": "ok", "colleges": 11}
    rows = client.get("/api/colleges").json()
    assert [r["nirf_rank"] for r in rows] == sorted(r["nirf_rank"] for r in rows)
    assert all(r["source_url"].startswith("http") for r in rows)


def test_college_and_sources():
    c = client.get("/api/colleges/nit-calicut").json()
    assert c["fees"]["totalFourYearCostINR"] == 1_163_500
    s = client.get("/api/colleges/nit-calicut/sources").json()
    assert s["verification"] == "Audited & Verified" and "placement.batchSize" in s["provenance"]
    assert client.get("/api/colleges/nope").status_code == 404


def test_recommend_deck_and_filters():
    r = client.post("/api/recommend", json={"percentile": 99.75, "budget_lakhs": 12, "region": "All"}).json()
    assert r["supported"] and all(m["four_year_cost_inr"] <= 1_200_000 for m in r["matches"])
    assert r["deck"]["safe_anchor"]["id"] == "nit-calicut"
    south = client.post("/api/recommend", json={"percentile": 99.75, "budget_lakhs": 40, "region": "South"}).json()
    assert {m["region"] for m in south["matches"]} == {"South"}
    unsupported = client.post("/api/recommend", json={"stream": "MBA"}).json()
    assert unsupported["supported"] is False


def test_roi_finance_alignment():
    roi = client.post("/api/roi", json={"college_id": "mnit-jaipur"}).json()
    assert roi["payback"]["payback_months"] > roi["payback"]["payback_months_gross_pay"]
    fin = client.post("/api/finance/plan", json={"college_id": "mnit-jaipur", "family_savings": 500_000}).json()
    assert fin["total_deficit_inr"] == 1_110_348 - 500_000 or abs(fin["total_deficit_inr"] - (1_110_348 - 500_000)) <= 8
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
