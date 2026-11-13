"""Round-by-round counselling answer (T-16.05): looks seats up in the shipped JoSAA round history and calls engines/rounds.py.

Two ways in. Replay: the cycle year is in the archive, so the seat held after each round is read from that year's
published closing ranks. Own round: the family says which choice was allotted (or none). In both, the history shown for
a higher choice comes only from years before the cycle, so a replay never sees its own answer.
"""
from typing import List, Optional

from ..data import round_history
from ..engines import rounds as eng
from . import admissions

GENDERS = ("Gender-Neutral", "Female-only (including Supernumerary)")
SOURCE = "JoSAA opening and closing rank archive, every round"


def cycles() -> dict:
    h = round_history()
    # "Own round" is the cycle of the published schedule and rules (the next one is not out yet).
    return {"replay_years": sorted(h["rounds"], reverse=True), "rounds": h["rounds"],
            "own_round": {"year": int(admissions.timeline_data()["cycle"]), "total_rounds": _live_total_rounds()}}


def seats(year: int, seat_type: str, gender: str) -> List[dict]:
    out = [{"institute": k[0], "program": k[1], "quota": k[2], "inst_type": v["inst_type"]}
           for k, v in round_history()["seats"].items() if k[3] == seat_type and k[4] == gender and year in v["years"]]
    return sorted(out, key=lambda x: (x["institute"], x["program"], x["quota"]))


def _live_total_rounds() -> int:
    return sum(1 for e in admissions.timeline_data()["events"] if e["kind"] == "allotment" and e["id"].startswith("josaa-"))


def advise(*, year: int, rnd: int, choices: List[dict], seat_type: str, gender: str, main_rank: Optional[int],
           advanced_rank: Optional[int], allotted: Optional[int] = None, no_seat: bool = False) -> dict:
    h = round_history()
    replay = year in h["rounds"]
    total = h["rounds"][year] if replay else _live_total_rounds()
    if not 1 <= rnd <= total:
        raise ValueError(f"round must be between 1 and {total}")
    rows = []
    for c in choices:
        seat = h["seats"].get((c["institute"], c["program"], c["quota"], seat_type, gender))
        if seat is None:
            raise ValueError(f"unknown seat: {c['institute']} / {c['program']} / {c['quota']}")
        rows.append(seat)
    ranks = [advanced_rank if s["inst_type"] == "IIT" else main_rank for s in rows]  # IIT closing ranks are JEE Advanced ranks
    if replay and allotted is None and not no_seat:
        held, held_from = eng.held_choice([s["years"].get(year) for s in rows], ranks, rnd), "replay"
    else:
        held, held_from = (None if no_seat else allotted), "entered"
        if held is not None and not 0 <= held < len(choices):
            raise ValueError("allotted must be a position in the list")
        if held is None and not no_seat:
            raise ValueError("say which choice was allotted, or that no seat was allotted")
    use_years = eng.history_years(h["rounds"], year)
    items = []
    for i, (c, s, rank) in enumerate(zip(choices, rows, ranks)):
        item = {"position": i + 1, "institute": c["institute"], "program": c["program"], "quota": c["quota"], "inst_type": s["inst_type"], "rank_used": rank, "held": i == held,
                "above_held": held is None or i < held, "same_institute_as_held": held is not None and c["institute"] == choices[held]["institute"]}
        # The closing rank published after this round: read from the archive in a replay, typed in by the family otherwise.
        now = (s["years"].get(year) or [None] * 6)[rnd - 1] if replay else c.get("closing_this_round")
        item["closing_this_round"] = eng.published(now)
        if item["above_held"]:
            item["history"] = eng.movement(s["years"], rnd, rank, use_years, now) if rank is not None else None
        items.append(item)
    opt = eng.option(held, [c["institute"] for c in choices], rnd, total)
    money = eng.money_at_risk(rows[held]["inst_type"] if held is not None else None, seat_type, rnd, total,
                              admissions.timeline_data()["seatAcceptanceFee"], admissions.josaa_rules()["withdrawalChargeInr"])
    doc = admissions.josaa_rules()
    used = set(opt["rule_ids"]) | set(money.get("rule_ids", []))
    return {"year": year, "round": rnd, "total_rounds": total, "mode": "replay" if replay else "own_round", "held_from": held_from,
            "held": held, "option": opt, "choices": items, "money": money, "history_years": use_years,
            "rules": [r for r in doc["rules"] if r["id"] in used],
            "rules_source": {"document": doc["document"], "url": doc["url"], "cycle": doc["cycle"]},
            "source": SOURCE, "source_url": "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx",
            "needs_rank": sorted({"jee_advanced" if s["inst_type"] == "IIT" else "jee_main" for s, r in zip(rows, ranks) if r is None})}
