"""Degree ROI: payback ('Time-to-Debt-Freedom') and illustrative trajectory (D-02, D-28)."""
from .assumptions import Assumptions
from .tax import annual_tax


def in_hand_monthly(gross_annual: float) -> float:
    return (gross_annual - annual_tax(gross_annual)) / 12


def payback(total_cost: int, median_lpa: float, a: Assumptions) -> dict:
    gross_annual = median_lpa * 100_000
    ih = in_hand_monthly(gross_annual)
    disposable = ih * a.savings_rate
    return {
        "total_cost_inr": total_cost,
        "median_base_lpa": median_lpa,
        "in_hand_monthly_inr": round(ih),
        "disposable_monthly_inr": round(disposable),
        "payback_months": round(total_cost / disposable, 1),
        "payback_months_gross_pay": round(total_cost / (gross_annual / 12), 1),
        "assumptions": {"savings_rate": a.savings_rate},
    }


def trajectory(median_lpa: float, a: Assumptions, years: int = 10) -> dict:
    pts = [{"year": y, "salary_lpa": round(median_lpa * (1 + a.salary_growth) ** y, 2)} for y in range(years + 1)]
    return {"illustrative": True, "note": "Year 0 is the audited NIRF median; later years apply the editable growth assumption and are not audited data.",
            "growth": a.salary_growth, "points": pts}
