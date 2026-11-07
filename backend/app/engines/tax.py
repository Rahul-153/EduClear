"""India new-regime income tax, FY2025-26 slabs (assumption D-28: verify before launch)."""
STANDARD_DEDUCTION = 75_000
SLABS = [(400_000, 0.00), (800_000, 0.05), (1_200_000, 0.10), (1_600_000, 0.15),
         (2_000_000, 0.20), (2_400_000, 0.25), (float("inf"), 0.30)]
REBATE_LIMIT = 1_200_000
CESS = 0.04


def annual_tax(gross: float) -> float:
    taxable = max(0.0, gross - STANDARD_DEDUCTION)
    tax, lower = 0.0, 0.0
    for upper, rate in SLABS:
        if taxable > lower:
            tax += (min(taxable, upper) - lower) * rate
        lower = upper
    if taxable <= REBATE_LIMIT:
        tax = 0.0
    else:
        tax = min(tax, taxable - REBATE_LIMIT)  # marginal relief
    return tax * (1 + CESS)
