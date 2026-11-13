"""Round-by-round counselling answer (T-16.05): looks seats up in the shipped JoSAA round history and calls engines/rounds.py.

Two ways in. Replay: the cycle year is in the archive, so the seat held after each round is read from that year's
published closing ranks. Own round: the family says which choice was allotted (or none). In both, the history shown for
a higher choice comes only from years before the cycle, so a replay never sees its own answer.
"""
import re
from functools import lru_cache
from typing import List, Optional

from ..data import round_history
from ..engines import rounds as eng
from ..engines.assumptions import Assumptions
from ..engines.fit import percentile_to_rank
from . import admissions, cutoff_options, intake

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


# ---- Copilot tool (T-16.08): "I got NIT Patna in round 2 and want NIT Calicut, should I float?" ----------------------
_SHORT = (("indian institute of information technology", "iiit"), ("national institute of technology", "nit"),
          ("indian institute of technology", "iit"))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[,()]", " ", s.lower())).strip()


@lru_cache(maxsize=1)
def _institute_names() -> dict:
    """Ways to write an institute -> its JoSAA name: the full name and the NIT / IIT / IIIT short form. A form shared by two institutes is dropped."""
    out, clash = {}, set()
    for inst in {k[0] for k in round_history()["seats"]}:
        full = _norm(inst)
        forms = {full}
        for long, short in _SHORT:
            if long in full:
                forms.add(_norm(full.replace(long, short)))
        for f in forms:
            if f in out and out[f] != inst:
                clash.add(f)
            out[f] = inst
    return {k: v for k, v in out.items() if k not in clash}


def find_institutes(text: str) -> List[tuple]:
    """(position, JoSAA institute name) in the order written. Longest name first; a matched span is blanked."""
    low, found = _norm(text), []
    for k, inst in sorted(_institute_names().items(), key=lambda kv: -len(kv[0])):
        m = re.search(rf"(?<!\w){re.escape(k)}(?!\w)", low)
        if m:
            found.append((m.start(), inst))
            low = low[:m.start()] + " " * len(k) + low[m.end():]
    return sorted(set(found))


def _seat_for(institute: str, stream: str, seat_type: str, gender: str) -> Optional[dict]:
    """The institute's programme in this branch group: Other State quota where it exists, else All India; the plainest programme name."""
    pattern = re.compile(cutoff_options.BRANCH_GROUPS[stream], re.I)
    rows = [k for k in round_history()["seats"] if k[0] == institute and k[3] == seat_type and k[4] == gender and pattern.search(k[1])]
    for quota in ("OS", "AI"):
        pick = sorted((k for k in rows if k[2] == quota), key=lambda k: (len(k[1]), k[1]))
        if pick:
            return {"institute": institute, "program": pick[0][1], "quota": quota}
    return None


def _label(c: dict) -> str:
    return f"{c['institute']}, {re.sub(r' *[(]4 Years.*$', '', c['program'])} ({c['quota']})"


def copilot(msg: str, profile: dict, a: Assumptions, hi: bool) -> dict:
    t = _norm(msg.translate(intake.DEV))
    stream = profile.get("stream") if profile.get("stream") in cutoff_options.BRANCH_GROUPS else "Computer Science"
    seat_type = profile.get("seat_type") if profile.get("seat_type") in cutoff_options.SEAT_TYPES else "OPEN"
    gender = GENDERS[0]  # chat answers use Gender-Neutral seats; female-only seats are on the Apply page
    found = find_institutes(msg)
    rnd = re.search(r"(?:round|राउंड)\s*(\d)", t)
    if not found or not rnd:
        return {"data": {}, "reply": "लिखें कि किस राउंड में कौन-सी सीट मिली और ऊपर की कौन-सी पसंद चाहिए, जैसे: 'राउंड 2 में NIT Patna मिला, NIT Calicut चाहिए'।" if hi else
                "Tell me the round, the seat you were allotted and the higher choice you are waiting for, e.g. 'I got NIT Patna in round 2 and want NIT Calicut'."}
    # The allotted seat: the institute after "got / allotted / holding", or before "मिला / मिली"; otherwise the first one written.
    en, hin = re.search(r"\b(got|allotted|allocated|holding|have)\b", t), re.search(r"मिल", t)
    held_inst = (next((i for p, i in found if en and p > en.start()), None) or next((i for p, i in reversed(found) if hin and p < hin.start()), None)
                 or found[0][1])
    higher = [i for _, i in found if i != held_inst]
    seats = {i: _seat_for(i, stream, seat_type, gender) for i in [held_inst] + higher}
    missing = [i for i, s in seats.items() if s is None]
    if missing:
        return {"data": {}, "reply": (f"{missing[0]} में {stream} की {seat_type} सीट हमारे JoSAA रिकॉर्ड में नहीं है।" if hi else
                f"{missing[0]} has no {seat_type} seat for {stream} in our JoSAA record.")}
    year_m = re.search(r"\b(20\d\d)\b", t)
    cyc = cycles()
    year = int(year_m.group(1)) if year_m and int(year_m.group(1)) in cyc["rounds"] else cyc["own_round"]["year"]
    said = re.search(r"(?:rank|रैंक)\D{0,12}(\d[\d ,]*\d|\d)", t)
    rank = int(re.sub(r"\D", "", said.group(1))) if said else None
    approx = False
    if rank is None:
        if seat_type == "OPEN" and profile.get("percentile") is not None:
            rank, approx = percentile_to_rank(float(profile["percentile"]), a), True
        elif seat_type != "OPEN" and profile.get("category_rank"):
            rank = int(profile["category_rank"])
    adv = int(profile["jee_advanced_rank"]) if profile.get("jee_advanced_rank") else None
    choices = [seats[i] for i in higher] + [seats[held_inst]]
    try:
        r = advise(year=year, rnd=int(rnd.group(1)), choices=choices, seat_type=seat_type, gender=gender, main_rank=rank,
                   advanced_rank=adv, allotted=len(higher))
    except ValueError as e:
        return {"data": {}, "reply": str(e)}
    act, m = r["option"]["action"], r["money"]
    head = (f"राउंड {r['round']}/{r['total_rounds']}, आपके पास: {_label(choices[-1])}." if hi else
            f"Round {r['round']} of {r['total_rounds']}, seat held: {_label(choices[-1])}.")
    opt = {"freeze_only": ("सूची में इससे ऊपर कोई पसंद नहीं बताई गई: केवल फ़्रीज़ का विकल्प है।", "No higher choice was named: freeze is the only option."),
           "last_round": ("अंतिम राउंड में फ़्लोट और स्लाइड नहीं मिलते।", "Float and slide are not offered in the last round."),
           "slide": ("स्लाइड ऊपर की पसंद खुली रखता है (एक ही संस्थान)। ऊपर की पसंद खुलते ही यह सीट अपने-आप बदल जाती है; फ़्रीज़ बाद में बदला नहीं जा सकता।",
                     "Slide keeps the higher choice open (same institute). If it opens it replaces this seat automatically; freeze cannot be changed later."),
           "float": ("फ़्लोट ऊपर की हर पसंद खुली रखता है। ऊपर की पसंद खुलते ही यह सीट अपने-आप बदल जाती है; फ़्रीज़ बाद में बदला नहीं जा सकता।",
                     "Float keeps every higher choice open. If one opens it replaces this seat automatically; freeze cannot be changed later.")}[act][0 if hi else 1]
    lines = [head, opt]
    yrs = f"{r['history_years'][0]}-{r['history_years'][-1]}"
    for c in r["choices"][:-1] if act in ("float", "slide") else []:
        h = c.get("history")
        if not h:
            lines.append(f"{_label(c)}: " + ("रैंक चाहिए (IIT के लिए JEE Advanced रैंक)।" if hi else "needs your rank (a JEE Advanced rank for IITs)."))
        elif h["basis"] == "relative_move":
            lines.append((f"{_label(c)}: इस राउंड की क्लोज़िंग रैंक {h['closing_now']:,}, आप {h['short_by_pct']}% पीछे; {yrs} के {h['years_with_data']} में से {h['years_reached']} वर्षों में रैंक इतनी खिसकी।" if hi else
                          f"{_label(c)}: closing rank this round {h['closing_now']:,}, you are short by {h['short_by_pct']}%; it moved that much after this round in {h['years_reached']} of {h['years_with_data']} past years ({yrs})."))
        else:
            lines.append((f"{_label(c)}: {yrs} के {h['years_with_data']} में से {h['years_reached']} वर्षों में क्लोज़िंग रैंक आपकी रैंक {c['rank_used']:,} तक पहुँची। Apply पेज पर इस राउंड की क्लोज़िंग रैंक डालें, तुलना बेहतर होगी।" if hi else
                          f"{_label(c)}: in {h['years_reached']} of {h['years_with_data']} past years ({yrs}) the closing rank reached your rank {c['rank_used']:,}. Add this round's closing rank on the Apply page for a closer reading."))
    if approx:
        lines.append(f"रैंक {rank:,} आपके पर्सेंटाइल से निकाली गई है; अपनी असली रैंक लिखें।" if hi else f"Rank {rank:,} is worked out from your percentile; tell me your actual rank for a better answer.")
    lines.append((f"सीट स्वीकृति शुल्क ₹{m['seat_acceptance_fee_inr']:,}; सीट छोड़ने पर ₹{m['refund_on_withdrawal_inr']:,} वापस (₹{m['withdrawal_charge_inr']:,} कटौती)। वर्षों की गिनती पूर्वानुमान नहीं है।" if hi else
                  f"Seat acceptance fee ₹{m['seat_acceptance_fee_inr']:,}; ₹{m['refund_on_withdrawal_inr']:,} comes back if you withdraw (₹{m['withdrawal_charge_inr']:,} charge). A count of past years is not a forecast."))
    return {"data": r, "reply": "\n".join(lines)}
