from backend.app.engines.assumptions import Assumptions
from backend.app.engines.choice import analyse

A = Assumptions()


def test_inversion_detected_and_order_suggested():
    # Calicut OS closing 5222, MNIT OS closing 5601. Percentile 99.75 -> AIR 3,688 qualifies for both.
    r = analyse(["mnit-jaipur", "nit-calicut"], A, percentile=99.75)
    assert len(r["alerts"]) == 1 and r["alerts"][0]["severity"] == "high"
    assert r["alerts"][0]["easier_option"] == "MNIT Jaipur" and r["alerts"][0]["harder_option"] == "NIT Calicut"
    assert r["suggested_order"] == ["nit-calicut", "mnit-jaipur"]


def test_correct_order_has_no_alerts():
    assert analyse(["nit-calicut", "mnit-jaipur"], A, percentile=99.75)["alerts"] == []


def test_far_out_of_reach_harder_option_is_not_flagged():
    # AIR ~85,000 cannot plausibly get Calicut (5222 x 1.5 = 7,833): no inversion alert
    assert analyse(["mnit-jaipur", "nit-calicut"], A, percentile=94.2)["alerts"] == []


def test_mixed_bases_checked_separately():
    r = analyse(["nit-calicut", "iit-bhu", "bits-pilani"], A, percentile=99.75, jee_advanced_rank=1300)
    assert r["alerts"] == []
    assert any("different" in n or "Not comparable" in n for n in r["notes"])
    assert r["suggested_order"][-1] == "bits-pilani"


def test_iit_advanced_inversion():
    # BHU closing 1489 (easier) above Hyderabad closing 673 for AIR 600 -> high
    r = analyse(["iit-bhu", "iit-hyderabad"], A, jee_advanced_rank=600)
    assert r["alerts"][0]["severity"] == "high" and r["suggested_order"] == ["iit-hyderabad", "iit-bhu"]


def test_endpoint_accepts_every_college_the_app_can_list():
    from fastapi.testclient import TestClient
    from backend.app.data import colleges
    from backend.app.main import app
    ids = list(colleges())
    r = TestClient(app).post("/api/choice-order", json={"college_ids": ids, "percentile": 99.75})
    assert r.status_code == 200 and len(r.json()["items"]) == len(ids)  # the simulator sends the whole matching list (was 422 above 50)
