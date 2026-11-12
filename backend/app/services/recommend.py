"""Smart Sentence recommendation: budget/region filter + fit tier + payback (FR-01, FR-03)."""

import re

from ..data import branch_placements, colleges, cutoff_rows
from ..engines.assumptions import Assumptions
from ..engines.fit import fit
from ..engines.roi import payback
from .cutoff_options import BRANCH_GROUPS, options

SUPPORTED_STREAMS = ["Computer Science"]  # institute-wide cost and placement cover CSE only (D-29)
BRANCH_CODE = {"Computer Science": "CSE", "Electronics & Communication": "ECE", "Electrical": "EE", "Mechanical": "ME", "Civil": "CE"}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def card(c, a: Assumptions, f: dict, bp: dict | None = None) -> dict:
    """`bp` is the chosen branch's own placement row (branch_placements.csv); when present it replaces the institute-wide figures."""
    p = c.placement
    out = {
        "id": c.id, "data_level": "audited" if c.sources.verificationStatus == "Audited & Verified" else "supplied", "name": c.name, "short_name": c.shortName, "city_state": f"{c.location.city}, {c.location.state}",
        "region": c.location.region, "nirf_rank": c.nirfRank, "fit": f,
        "four_year_cost_inr": c.fees.totalFourYearCostINR,
        "headline_ctc_lpa": p.headlineCTC, "median_base_lpa": p.medianBaseSalary,
        "placed": p.actuallyPlaced, "eligible": p.eligibleStudents, "placement_rate": p.disclosedPlacementRate,
        "payback": payback(c.fees.totalFourYearCostINR, p.medianBaseSalary, a),
        "source_url": c.sources.nirfDisclosureUrl,
        "accreditation": c.accreditation, "commercial_relationship": c.commercialRelationship,
    }
    if bp:
        out.update(branch_scope=True, headline_ctc_lpa=bp["highest"], median_base_lpa=bp["median"], placed=bp["placed"], eligible=bp["eligible"],
                   placement_rate=bp["rate"], payback=payback(c.fees.totalFourYearCostINR, bp["median"], a), source_url=bp["source_url"])
    return out


def _deck(cards: list) -> tuple[list, dict]:
    ranked = sorted(cards, key=lambda x: x["nirf_rank"])
    deck = {slot: next((x for x in ranked if x["fit"]["tier"] == tier), None)
            for slot, tier in (("safe_anchor", "Safe"), ("sweet_spot", "Target"), ("dream_reach", "Reach"))}
    return ranked, deck


def _branch_fit(c, item: dict | None) -> dict:
    if item:
        return {"tier": item["tier"], "reason": None, "closing_rank_used": item["closing_rank"], "quota": item["quota"], "approx_user_rank": item["user_rank"]}
    if c.cutoffs.primaryExam == "JEE Advanced":
        return {"tier": None, "reason": "Needs a JEE Advanced rank (IIT cutoffs are Advanced ranks)"}
    return {"tier": None, "reason": "No official cutoff row for this branch"}


def recommend(stream: str, budget_lakhs: float, region: str, a: Assumptions, opts: dict | None = None, **user) -> dict:
    """`opts` (seat_type, gender, category_rank) only feeds the cutoff-only list; audited cards keep the OPEN, CSE basis (D-29)."""
    has_table = bool(cutoff_rows())  # the JoSAA cutoff table is optional; without it only the college records are used
    if stream not in BRANCH_GROUPS or (stream not in SUPPORTED_STREAMS and not has_table):
        return {"supported": False, "message": f"Data currently covers: {', '.join(SUPPORTED_STREAMS)}", "deck": {}, "matches": []}
    code, bps = BRANCH_CODE[stream], branch_placements()
    if stream not in SUPPORTED_STREAMS:
        # Other branches (D-59, D-60): institutes with a branch placement row become cards (cost from the record, that branch's own
        # placement and payback, tier from the official JoSAA row when there is one); every other institute stays cutoff-only.
        items = options(stream, a, percentile=user.get("percentile"), jee_advanced_rank=user.get("jee_advanced_rank"),
                        include_audited=True, keep_out_of_reach=True, **(opts or {}))
        by_name = {_norm(i["institute"]): i for i in items["items"]}
        pool = [c for c in colleges().values() if (c.id, code) in bps and c.fees.totalFourYearCostINR <= budget_lakhs * 100_000
                and (region == "All" or c.location.region == region)]
        cards = [card(c, a, _branch_fit(c, by_name.get(_norm(c.name))), bps[(c.id, code)]) for c in pool]
        ranked, deck = _deck(cards)
        shown = {_norm(c.name) for c in colleges().values() if (c.id, code) in bps}  # a branch card, or filtered out by budget or region
        rest = [i for i in items["items"] if i["tier"] != "Out of reach" and _norm(i["institute"]) not in shown]
        msg = (f"{stream} placement is shown per branch for {len(shown)} institutes (supplied, not audited); all other institutes show closing ranks only."
               if shown else f"Cost and placement are available for {', '.join(SUPPORTED_STREAMS)} only. Showing cutoff-only options for {stream}.")
        return {"supported": True, "message": msg, "deck": deck, "matches": ranked, "cutoff_only": {**items, "items": rest},
                "needs_more_input": [{"id": x["id"], "reason": x["fit"]["reason"]} for x in ranked if x["fit"]["tier"] is None]}
    pool = [c for c in colleges().values()
            if c.fees.totalFourYearCostINR <= budget_lakhs * 100_000 and (region == "All" or c.location.region == region)]
    cards = [card(c, a, fit(c, a, **user), bps.get((c.id, code))) for c in pool]
    ranked, deck = _deck(cards)
    unrated = [x for x in ranked if x["fit"]["tier"] is None]
    return {"supported": True, "deck": deck, "matches": ranked, "needs_more_input": [
        {"id": x["id"], "reason": x["fit"]["reason"]} for x in unrated]}
