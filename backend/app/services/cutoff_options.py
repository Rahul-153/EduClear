"""Cutoff-only options: JoSAA institutes that have no audited record, matched on the official 2025 final-round closing ranks.

These rows carry a closing rank and nothing else. Cost, placement and payback are never estimated for them (D-49).
Rank basis: NIT, IIIT and GFTI closing ranks are JEE Main ranks, so the student's percentile is converted with the same
engine rule as the audited fit (D-10). IIT closing ranks are JEE Advanced ranks and need the student's own rank.
Institutes with a partly verified record (D-49) also carry their NIRF placement row; cost is still absent.
Home-state seats are not applied here (the table has no institute state): Other State and All India seats are used.
"""
import re

from ..data import cutoff_rows, partial_colleges
from ..engines.assumptions import Assumptions
from ..engines.fit import _tier, percentile_to_rank  # same tier margins as the audited cards

SOURCE = "JoSAA 2025 round 6 (official opening and closing rank archive)"
SOURCE_URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"

# Programme-name keywords per branch. Only 4-year degrees count; dual degree, MBA and integrated courses are left out.
BRANCH_GROUPS = {
    "Computer Science": r"computer science",
    "Electronics & Communication": r"electronics (and|&) communication",
    "Electrical": r"electrical engineering",
    "Mechanical": r"mechanical engineering",
    "Civil": r"civil engineering",
}
_EXCLUDE = re.compile(r"dual degree|mba|integrated|master|m\.tech", re.I)
SEAT_TYPES = ("OPEN", "EWS", "OBC-NCL", "SC", "ST")
FEMALE_ONLY = "Female-only (including Supernumerary)"
LABEL = {"IIT": "IIT", "NIT": "NIT", "3IT": "IIIT", "CFI": "GFTI"}
ORDER = {"Safe": 0, "Target": 1, "Reach": 2, "Out of reach": 3}

# Official JoSAA names of the institutes that already have an audited record (DTU and BITS are not in JoSAA).
AUDITED_JOSAA_NAMES = {
    "iit-hyderabad": "Indian Institute of Technology Hyderabad", "iit-bhu": "Indian Institute of Technology (BHU) Varanasi",
    "iit-guwahati": "Indian Institute of Technology Guwahati", "mnit-jaipur": "Malaviya National Institute of Technology Jaipur",
    "nit-calicut": "National Institute of Technology Calicut", "nit-kurukshetra": "National Institute of Technology, Kurukshetra",
    "nit-silchar": "National Institute of Technology, Silchar", "nit-patna": "National Institute of Technology Patna",
    "nit-raipur": "National Institute of Technology Raipur",
}


def _published(v: float):
    return int(v) if v == int(v) else v  # ranks are shown as published, never rounded


def options(stream: str, a: Assumptions, *, percentile=None, jee_advanced_rank=None, seat_type="OPEN",
            gender="Any", category_rank=None, include_audited=False, keep_out_of_reach=False) -> dict:
    pattern = re.compile(BRANCH_GROUPS[stream], re.I)
    genders = {"Gender-Neutral"} | ({FEMALE_ONLY} if gender == "Female" else set())
    skip = set() if include_audited else set(AUDITED_JOSAA_NAMES.values())  # those institutes already show as cards, for Computer Science only
    best: dict = {}  # institute -> (closing, row, user rank): the most generous programme and quota for this student
    for r in cutoff_rows():
        if r["is_prep"] or r["closing"] is None or r["seat_type"] != seat_type or r["gender"] not in genders or r["institute"] in skip:
            continue
        prog = r["program"]
        if "(4 Years" not in prog or _EXCLUDE.search(prog) or not pattern.search(prog):
            continue
        if r["inst_type"] == "IIT":  # Advanced ranks; category seats would need an Advanced category rank, which is not asked
            if r["quota"] != "AI" or seat_type != "OPEN" or jee_advanced_rank is None:
                continue
            rank = jee_advanced_rank
        else:
            if r["quota"] not in ("AI", "OS"):
                continue
            rank = (percentile_to_rank(percentile, a) if percentile is not None else None) if seat_type == "OPEN" else category_rank
            if rank is None:
                continue
        cur = best.get(r["institute"])
        if cur is None or r["closing"] > cur[0]:
            best[r["institute"]] = (r["closing"], r, rank)
    partial = partial_colleges()
    out = []
    for inst, (closing, r, rank) in best.items():
        tier = _tier(rank, closing, a)
        if tier == "Out of reach" and not keep_out_of_reach:
            continue
        out.append({"institute": inst, "kind": LABEL[r["inst_type"]], "program": r["program"], "quota": r["quota"],
                    "seat_type": seat_type, "gender": r["gender"], "closing_rank": _published(closing), "user_rank": rank,
                    "tier": tier, "data_level": "cutoffs_only", "source": SOURCE, "source_url": SOURCE_URL})
        if inst in partial:
            p = partial[inst]
            out[-1].update(data_level="partly_verified", nirf_rank=p.nirfRank, placement={
                "batch": p.placement.batch, "placed": p.placement.placed, "eligible": p.placement.eligible,
                "placement_rate": p.placement.placementRatePct, "median_base_lpa": round(p.placement.medianSalaryInr / 100_000, 2),
                "source_url": p.source.url})
    out.sort(key=lambda x: (ORDER[x["tier"]], x["closing_rank"]))
    return {"items": out, "iits_need_rank": jee_advanced_rank is None}
