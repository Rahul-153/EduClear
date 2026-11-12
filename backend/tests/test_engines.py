
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


def test_cutoffs_in_the_supplied_data_parse_into_known_kinds():
    kinds = {cid: parse_cutoff(c)["kind"] for cid, c in colleges().items()}
    assert set(kinds.values()) <= {"jee_main", "jee_advanced", "bitsat", "unknown"}
    assert sum(k != "unknown" for k in kinds.values()) > 50  # most colleges have a comparable cutoff
    assert parse_cutoff(colleges()["nit-trichy"]) == {"kind": "jee_main", "os": 1500, "hs": 3900}  # supplied CSE round 6 rows
    assert parse_cutoff(colleges()["iit-bombay"]) == {"kind": "jee_advanced", "closing": 68}
    assert parse_cutoff(colleges()["bits-pilani"]) == {"kind": "bitsat", "cutoff_score": 331, "max": 390}


def test_single_all_india_closing_rank_applies_to_every_home_state():
    c = next(c for c in colleges().values() if "All India closing AIR" in c.cutoffs.minPercentileOrRank)
    cut = parse_cutoff(c)
    assert cut["os"] == cut["hs"]
    assert fit(c, A, percentile=99.0)["closing_rank_used"] == fit(c, A, percentile=99.0, home_state=c.location.state)["closing_rank_used"]


def test_fit_tiers():
    c = colleges()["nit-trichy"]  # supplied: OS closing 1500, HS 3900
    assert fit(c, A, percentile=99.95)["tier"] == "Safe"  # AIR 738 <= 0.8 x 1,500 = 1,200
    assert fit(c, A, percentile=99.9)["tier"] == "Target"  # AIR 1,475 is above the safe margin, within the closing rank
    assert fit(c, A, percentile=99.85)["tier"] == "Reach"  # AIR 2,213 <= 1.5 x 1,500
    assert fit(c, A, percentile=99.5)["tier"] == "Out of reach"
    home = fit(c, A, percentile=99.9, home_state="Tamil Nadu")
    assert home["quota"] == "Home State" and home["tier"] == "Safe"  # 1,475 <= 0.8 x 3,900
    assert fit(c, A)["tier"] is None
    iit = colleges()["iit-bombay"]  # supplied closing AIR 68
    assert [fit(iit, A, jee_advanced_rank=r)["tier"] for r in (50, 60, 70, 200)] == ["Safe", "Target", "Reach", "Out of reach"]
    assert fit(iit, A)["tier"] is None


def test_colleges_without_a_comparable_cutoff_are_not_rated():
    c = next(c for c in colleges().values() if parse_cutoff(c)["kind"] == "unknown")
    assert fit(c, A, percentile=99.9, jee_advanced_rank=1, bitsat_score=390)["tier"] is None
