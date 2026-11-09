
import pytest

from backend.app.data import colleges
from backend.app.engines import alignment as align
from backend.app.engines.assumptions import Assumptions
from backend.app.engines.emi import emi, funding_plan
from backend.app.engines.fit import fit, parse_cutoff, percentile_to_rank
from backend.app.engines.roi import in_hand_monthly, payback, trajectory
from backend.app.engines.tax import annual_tax

A = Assumptions()


def test_tax_hand_computed():
    # taxable 14,75,000: 20,000 + 40,000 + 15% of 2,75,000 = 1,01,250; +4% cess
    assert annual_tax(1_550_000) == pytest.approx(105_300)
    assert annual_tax(1_075_000) == 0  # 87A rebate (taxable 10L)
    # taxable 12,15,000: raw 62,250 but marginal relief caps at 15,000; +4% cess
    assert annual_tax(1_290_000) == pytest.approx(15_600)


def test_payback_hand_computed():
    assert in_hand_monthly(1_550_000) == pytest.approx(120_391.67, abs=0.01)
    p = payback(1_060_000, 15.5, A)
    assert p["payback_months"] == pytest.approx(22.0, abs=0.05)  # 1,060,000 / (120,391.67 x 0.40)
    assert p["payback_months_gross_pay"] == pytest.approx(8.2, abs=0.05)  # the prototype's gross-pay figure


def test_trajectory_starts_at_audited_median():
    t = trajectory(15.5, A)
    assert t["illustrative"] and t["points"][0]["salary_lpa"] == 15.5 and len(t["points"]) == 11


def test_emi_matches_amortisation():
    P, r, n = 1_000_000, 0.095 / 12, 120
    m = emi(P, 0.095, 10)
    bal = P
    for _ in range(n):
        bal = bal * (1 + r) - m
    assert abs(bal) < 1e-4
    assert emi(0, 0.095, 10) == 0


def test_funding_plan_hand_computed():
    f = funding_plan(1_060_000, 800_000, 0, A)
    assert f["cost_per_semester_inr"] == 132_500 and f["funds_per_semester_inr"] == 100_000
    assert f["deficit_per_semester_inr"] == [32_500] * 8 and f["total_deficit_inr"] == 260_000
    assert funding_plan(1_060_000, 2_000_000, 0, A)["affordable_without_loan"] is True


def test_alignment():
    same = dict(brand_prestige=3, branch_passion=4, location_safety=2, budget_strictness=5)
    assert align.score(same, same)["alignment_score"] == 100
    low, high = {k: 1 for k in same}, {k: 5 for k in same}
    r = align.score(low, high)
    assert r["alignment_score"] == 0 and len(r["discussion_guide"]) == 4
    with pytest.raises(ValueError):
        align.score({"brand_prestige": 9}, same)


def test_percentile_to_rank():
    assert percentile_to_rank(99.1, A) == round(0.9 / 100 * 1_475_103)


def test_all_verified_colleges_have_parsable_cutoffs():
    kinds = {cid: parse_cutoff(c)["kind"] for cid, c in colleges().items()}
    assert kinds == {"bits-pilani": "bitsat", "dtu-delhi": "jee_main", "iit-bhu": "jee_advanced", "iit-guwahati": "jee_advanced",
                     "iit-hyderabad": "jee_advanced", "mnit-jaipur": "jee_main", "nit-calicut": "jee_main"}
    assert parse_cutoff(colleges()["mnit-jaipur"]) == {"kind": "jee_main", "os": 5601, "hs": 6013}
    assert parse_cutoff(colleges()["dtu-delhi"]) == {"kind": "jee_main", "os": 7060, "hs": 14806}
    assert parse_cutoff(colleges()["iit-bhu"])["closing"] == 1489


def test_fit_tiers():
    c = colleges()["nit-calicut"]  # OS closing 5222, HS 8428
    assert fit(c, A, percentile=99.75)["tier"] == "Safe"  # AIR 3,688 <= 0.8 x 5,222 = 4,177
    assert fit(c, A, percentile=99.7)["tier"] == "Target"  # AIR 4,425 is above the safe margin
    assert fit(c, A, percentile=99.65)["tier"] == "Target"  # AIR ~5,163
    assert fit(c, A, percentile=94.2)["tier"] == "Out of reach"
    assert fit(c, A, percentile=99.6, home_state="Kerala")["quota"] == "Home State"
    assert fit(c, A)["tier"] is None
    assert fit(colleges()["iit-bhu"], A, jee_advanced_rank=1300)["tier"] == "Target"  # 1300 > 0.8 x 1489 = 1191
