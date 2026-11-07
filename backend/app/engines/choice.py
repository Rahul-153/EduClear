"""Choice-filling rehearsal: detect order inversions in a preference list (FR-06).

Seats are allotted in the order of the student's list, so an easier option (larger closing rank) placed above a harder
one the student could also get means the harder option is never reached. Only options compared on the same rank basis
(JEE Main AIR, or JEE Advanced AIR) are checked against each other.
"""
from typing import List, Optional

from ..data import get_college
from .assumptions import Assumptions
from .fit import fit, parse_cutoff, percentile_to_rank


def _basis(c, a: Assumptions, percentile, home_state, adv_rank):
    cut = parse_cutoff(c)
    if cut["kind"] == "jee_main" and percentile is not None:
        in_home = bool(home_state) and home_state.strip().lower() == c.location.state.lower()
        return "jee_main", (cut["hs"] if in_home else cut["os"]), percentile_to_rank(percentile, a)
    if cut["kind"] == "jee_advanced" and adv_rank is not None:
        return "jee_advanced", cut["closing"], adv_rank
    return None, None, None


def analyse(college_ids: List[str], a: Assumptions, *, percentile: Optional[float] = None,
            home_state: Optional[str] = None, jee_advanced_rank: Optional[int] = None) -> dict:
    items = []
    for pos, cid in enumerate(college_ids, 1):
        c = get_college(cid)
        basis, closing, user_rank = _basis(c, a, percentile, home_state, jee_advanced_rank)
        items.append({"position": pos, "id": cid, "name": c.shortName, "basis": basis, "closing_rank": closing,
                      "user_rank": user_rank, "fit": fit(c, a, percentile=percentile, home_state=home_state,
                                                         jee_advanced_rank=jee_advanced_rank)["tier"]})
    alerts = []
    for i, hi in enumerate(items):
        for lo in items[i + 1:]:
            if hi["basis"] and hi["basis"] == lo["basis"] and hi["closing_rank"] > lo["closing_rank"]:
                u = hi["user_rank"]
                if u <= lo["closing_rank"]:
                    sev = "high"
                elif u <= lo["closing_rank"] * a.reach_margin:
                    sev = "medium"
                else:
                    continue
                alerts.append({
                    "severity": sev, "easier_option": hi["name"], "harder_option": lo["name"],
                    "message": (f"{hi['name']} (closing rank {hi['closing_rank']:,}) is listed above {lo['name']} "
                                f"(closing rank {lo['closing_rank']:,}). If your rank qualifies for both you will be "
                                f"allotted {hi['name']} and never reach {lo['name']}.")})
    comparable = sorted([x for x in items if x["basis"]], key=lambda x: (x["basis"], x["closing_rank"]))
    rest = [x for x in items if not x["basis"]]
    notes = []
    if rest:
        notes.append("Not comparable by rank (missing input or different admission process): " + ", ".join(x["name"] for x in rest))
    if len({x["basis"] for x in items if x["basis"]}) > 1:
        notes.append("Options on different rank bases (JEE Main vs JEE Advanced) are checked only within their own group.")
    return {"items": items, "alerts": alerts, "suggested_order": [x["id"] for x in comparable] + [x["id"] for x in rest], "notes": notes}
