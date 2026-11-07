"""Editable model assumptions (decision D-28). Never audited data; always surfaced to the user."""
from pydantic import BaseModel, Field


class Assumptions(BaseModel):
    jee_main_candidates: int = Field(1_475_103, description="Unique JEE Main 2025 candidates appeared (NTA notice 18 Apr 2025, secondhand)")
    savings_rate: float = Field(0.40, ge=0.05, le=0.9, description="Share of in-hand pay available to repay the degree cost")
    salary_growth: float = Field(0.10, ge=0.0, le=0.3, description="Yearly salary growth for the illustrative trajectory")
    loan_rate: float = Field(0.095, ge=0.01, le=0.3, description="Education-loan annual interest rate")
    loan_years: int = Field(10, ge=1, le=20, description="Education-loan repayment tenure in years")
    safe_margin: float = Field(0.80, description="Safe if your rank <= margin x closing rank")
    reach_margin: float = Field(1.50, description="Reach if your rank <= margin x closing rank")
