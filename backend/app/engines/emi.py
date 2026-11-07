"""Loan EMI and per-semester funding gap."""
from .assumptions import Assumptions


def emi(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0:
        return 0.0
    r, n = annual_rate / 12, years * 12
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def funding_plan(total_cost: int, family_savings: int, annual_contribution: int, a: Assumptions, semesters: int = 8) -> dict:
    cost_sem = total_cost / semesters
    funds_sem = family_savings / semesters + annual_contribution / 2
    deficits = [max(0, round(cost_sem - funds_sem)) for _ in range(semesters)]
    principal = sum(deficits)
    m = emi(principal, a.loan_rate, a.loan_years)
    return {
        "cost_per_semester_inr": round(cost_sem),
        "funds_per_semester_inr": round(funds_sem),
        "deficit_per_semester_inr": deficits,
        "total_deficit_inr": principal,
        "affordable_without_loan": principal == 0,
        "loan": {"principal_inr": principal, "annual_rate": a.loan_rate, "years": a.loan_years,
                 "emi_inr": round(m), "total_repaid_inr": round(m * a.loan_years * 12)},
    }
