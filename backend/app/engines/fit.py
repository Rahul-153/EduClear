"""Fit tier (Safe / Target / Reach) from verified closing ranks (D-10, D-21).

Cutoff numbers are parsed from the verified record text, not stored separately; parsing is tested.
Colleges whose entrance exam cannot be compared with the user's input return tier=None with a reason.
"""
import re
from typing import Optional

from scripts.college_model import College

from .assumptions import Assumptions


def percentile_to_rank(percentile: float, a: Assumptions) -> int:
    return max(1, round((100 - percentile) / 100 * a.jee_main_candidates))


def parse_cutoff(c: College) -> dict:
    t = c.cutoffs.minPercentileOrRank
    exam = c.cutoffs.primaryExam
    if exam == "JEE Advanced":
        m = re.search(r"closing AIR (\d+)", t)
        return {"kind": "jee_advanced", "closing": int(m.group(1))} if m else {"kind": "unknown"}
    if exam.startswith("JEE Main"):  # also "JEE Main (JoSAA)", "JEE Main / UGEE", "JEE Main (JAC Delhi)"
        os_, hs = re.search(r"Other State closing AIR (\d+)", t), re.search(r"Home State closing AIR (\d+)", t)
        if os_ and hs:
            return {"kind": "jee_main", "os": int(os_.group(1)), "hs": int(hs.group(1))}
        ai = re.search(r"All India closing AIR (\d+)", t)  # all-India seats: one rank for every candidate
        if ai:
            return {"kind": "jee_main", "os": int(ai.group(1)), "hs": int(ai.group(1))}
        o, d = re.search(r"Outside Delhi Region GNGNO (\d+)", t), re.search(r"Delhi Region GNGND (\d+)", t)
        return {"kind": "jee_main", "os": int(o.group(1)), "hs": int(d.group(1))} if o and d else {"kind": "unknown"}
    if exam == "BITSAT":
        m = re.search(r"B\.E\. Computer Science: (\d+)", t)
        return {"kind": "bitsat", "cutoff_score": int(m.group(1)), "max": 390} if m else {"kind": "unknown"}
    return {"kind": "unknown"}


def _tier(user_rank: float, closing: int, a: Assumptions) -> str:
    if user_rank <= a.safe_margin * closing:
        return "Safe"
    if user_rank <= closing:
        return "Target"
    if user_rank <= a.reach_margin * closing:
        return "Reach"
    return "Out of reach"


def fit(c: College, a: Assumptions, *, percentile: Optional[float] = None, home_state: Optional[str] = None,
        jee_advanced_rank: Optional[int] = None, bitsat_score: Optional[int] = None) -> dict:
    cut = parse_cutoff(c)
    out = {"tier": None, "reason": None, "basis": cut}
    if cut["kind"] == "jee_main":
        if percentile is None:
            out["reason"] = "Enter a JEE Main percentile"
            return out
        rank = percentile_to_rank(percentile, a)
        in_home = bool(home_state) and home_state.strip().lower() == c.location.state.lower()
        closing = cut["hs"] if in_home else cut["os"]
        out.update(tier=_tier(rank, closing, a), approx_user_rank=rank, closing_rank_used=closing,
                   quota="Home State" if in_home else "Other State")
    elif cut["kind"] == "jee_advanced":
        if jee_advanced_rank is None:
            out["reason"] = "Needs a JEE Advanced rank (IIT cutoffs are Advanced ranks)"
            return out
        out.update(tier=_tier(jee_advanced_rank, cut["closing"], a), closing_rank_used=cut["closing"], quota="All India")
    elif cut["kind"] == "bitsat":
        if bitsat_score is None:
            out["reason"] = "Needs a BITSAT score"
            return out
        gap = cut["cutoff_score"] - bitsat_score
        out.update(tier="Safe" if gap <= -20 else "Target" if gap <= 0 else "Reach" if gap <= 20 else "Out of reach",
                   cutoff_score=cut["cutoff_score"])
    else:
        out["reason"] = "Cutoff not comparable"
    return out
