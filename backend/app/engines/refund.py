"""UGC fee-refund calculation (FR-09). Tiers come from data/admissions/refund_policy.json (sourced, not hard-coded)."""
from datetime import date, timedelta
from typing import List, Optional


def usable_tiers(policy: dict) -> List[dict]:
    return [t for t in policy["tiers"] if t.get("refund_percent") is not None and t.get("anchor") == "closure_of_admission"]


def tier_for(policy: dict, closure: date, notice: date) -> dict:
    d = (notice - closure).days  # negative = before the last date of admission
    for t in usable_tiers(policy):
        lo, hi = t.get("from_days"), t.get("to_days")
        if (lo is None or d >= lo) and (hi is None or d <= hi):
            return t
    raise ValueError("no refund tier covers this date")


def refund(policy: dict, amount_inr: int, closure: date, notice: date) -> dict:
    t = tier_for(policy, closure, notice)
    gross = round(amount_inr * t["refund_percent"] / 100)
    cap = policy.get("processing_fee_deduction_max_inr") or 0
    fee = min(round(amount_inr * 0.05), cap) if t["id"] == "t1" else 0  # 5% capped; first tier only (UGC Cl. 4.1.4)
    return {"tier_id": t["id"], "refund_percent": t["refund_percent"], "window": t["window"], "gross_refund_inr": gross,
            "max_processing_fee_inr": fee, "minimum_net_refund_inr": gross - fee,
            "days_relative_to_closure": (notice - closure).days}


def milestones(policy: dict, closure: date, today: Optional[date] = None) -> List[dict]:
    """Dates at which the refundable share drops, with days remaining from today."""
    today = today or date.today()
    out = []
    for t in usable_tiers(policy):
        hi = t.get("to_days")
        if hi is None:
            continue
        last_day = closure + timedelta(days=hi)
        out.append({"tier_id": t["id"], "refund_percent": t["refund_percent"], "last_day": last_day.isoformat(),
                    "days_left": (last_day - today).days})
    return out
