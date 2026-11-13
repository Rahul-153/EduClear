"""Round-by-round counselling engine (PLAN_ROUND_COPILOT.md, T-16.03).

Everything here is history and rule, never a forecast: closing ranks are the published JoSAA figures, the option follows
from the student's own list and the quoted Business Rules, and the money figures are the fee and the withdrawal charge.
Pure functions: the caller passes the data in (as engines/refund.py does).
"""
from typing import Dict, List, Optional

HISTORY_YEARS = 5  # D-66: the latest five years before the cycle being looked at


def published(v: Optional[float]):
    return None if v is None else int(v) if v == int(v) else v  # ranks are shown as published, never rounded


def history_years(rounds_by_year: Dict[int, int], cycle: int) -> List[int]:
    return sorted(y for y in rounds_by_year if y < cycle)[-HISTORY_YEARS:]


def _pct(num: float, den: float) -> float:
    return round((num / den - 1) * 100, 1)  # display only; comparisons below use the published ranks themselves


def movement(years: Dict[int, list], rnd: int, rank: float, use_years: List[int], closing_now: Optional[float] = None) -> dict:
    """Per past year: the closing rank at this round and the highest closing rank from this round to the last published
    round. With this cycle's closing rank for the round (`closing_now`) the test is relative: did the closing rank move
    by at least the share the student is short by now? Without it, the test is whether the past closing rank reached the
    student's rank itself; the backtest (scripts/backtest_rounds.py) shows that reading is much weaker.
    A year without this seat or this round is listed as missing."""
    relative = closing_now is not None
    rows, reached, with_data = [], 0, 0
    for y in use_years:
        r = years.get(y)
        if r is None or r[rnd - 1] is None:
            rows.append({"year": y, "available": False})
            continue
        at, peak = r[rnd - 1], max(c for c in r[rnd - 1:] if c is not None)
        hit = peak * closing_now >= rank * at if relative else rank <= peak
        with_data += 1
        reached += hit
        rows.append({"year": y, "available": True, "closing_at_round": published(at), "highest_closing_from_round": published(peak),
                     "moved_pct": _pct(peak, at), "reached": hit})
    return {"basis": "relative_move" if relative else "absolute_rank", "years": rows, "years_reached": reached, "years_with_data": with_data,
            "closing_now": published(closing_now), "short_by_pct": _pct(rank, closing_now) if relative else None}


def held_choice(closings: List[Optional[list]], ranks: List[Optional[float]], rnd: int) -> Optional[int]:
    """Replay: the best-placed choice whose published closing rank had reached the student's rank in any round so far.
    Assumes the student kept floating: a seat once held is kept until a higher choice replaces it."""
    for i, (r, rank) in enumerate(zip(closings, ranks)):
        if r is None or rank is None:
            continue
        if any(c is not None and rank <= c for c in r[:rnd]):
            return i
    return None


def option(held: Optional[int], institutes: List[str], rnd: int, total_rounds: int) -> dict:
    """Which of freeze / float / slide the rules leave open, from the student's own list. `institutes` is the list in order."""
    if held is None:
        return {"action": "no_seat", "rule_ids": []}
    if held == 0:
        return {"action": "freeze_only", "rule_ids": ["first_choice_freeze_only", "freeze"]}
    if rnd >= total_rounds:
        return {"action": "last_round", "rule_ids": ["no_float_slide_in_last_round", "freeze"]}
    same = all(inst == institutes[held] for inst in institutes[:held])
    caveats = ["upgrade_replaces_seat", "rejecting_upgrade_ends_participation", "freeze_is_final", "can_step_down_option"]
    # Slide covers higher choices in the same institute only; float covers every higher choice.
    return {"action": "slide" if same else "float", "rule_ids": ["slide" if same else "float", "must_accept_to_continue"] + caveats}


def money_at_risk(held_inst_type: Optional[str], seat_type: str, rnd: int, total_rounds: int, fee: dict, withdrawal_charge_inr: int) -> dict:
    """Seat acceptance fee for this category and what comes back on a valid withdrawal. `fee` is timeline.json's seatAcceptanceFee."""
    if held_inst_type is None:
        return {"seat_acceptance_fee_inr": 0, "status": "no_seat"}
    paid = fee["reservedInr"] if seat_type in ("SC", "ST") else fee["generalInr"]
    last = total_rounds - 1 if held_inst_type == "IIT" else total_rounds  # Clause 63: IITs until the second-last round, NIT+ until the final round
    return {"seat_acceptance_fee_inr": paid, "status": "seat_held", "withdrawal_charge_inr": withdrawal_charge_inr,
            "refund_on_withdrawal_inr": paid - withdrawal_charge_inr, "withdrawal_open_this_round": 2 <= rnd <= last,
            "withdrawal_first_round": 2, "withdrawal_last_round": last,
            "rule_ids": ["fee_paid_once", "withdrawal_refund", "withdrawal_window_iit"]  # this clause also states the start (2nd round)
            + ([] if held_inst_type == "IIT" else ["withdrawal_window_nit_plus"]) + ["withdrawal_excludes"]}


def order_alerts(items: List[dict], reach_margin: float) -> List[dict]:
    """Same rule as engines/choice.py, on seats: an easier seat (larger closing rank) listed above a harder one the
    student could also get means the harder one is never reached. `items` in list order, each with `basis`, `closing`
    (a past final-round closing rank) and `rank`; entries without a closing rank or a rank are skipped."""
    out = []
    for i, hi in enumerate(items):
        for j in range(i + 1, len(items)):
            lo = items[j]
            if None in (hi["closing"], lo["closing"], hi["rank"]) or hi["basis"] != lo["basis"] or hi["closing"] <= lo["closing"]:
                continue
            if hi["rank"] <= lo["closing"]:
                sev = "high"
            elif hi["rank"] <= lo["closing"] * reach_margin:
                sev = "medium"
            else:
                continue
            out.append({"severity": sev, "above": i, "below": j, "above_closing": published(hi["closing"]), "below_closing": published(lo["closing"])})
    return out

