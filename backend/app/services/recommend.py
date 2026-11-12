"""Smart Sentence recommendation: budget/region filter + fit tier + payback (FR-01, FR-03)."""

from ..data import colleges, cutoff_rows
from ..engines.assumptions import Assumptions
from ..engines.fit import fit
from ..engines.roi import payback
from .cutoff_options import BRANCH_GROUPS, options

SUPPORTED_STREAMS = ["Computer Science"]  # dataset covers CSE only (D-29)


def card(c, a: Assumptions, f: dict) -> dict:
    p = c.placement
    return {
        "id": c.id, "data_level": "audited" if c.sources.verificationStatus == "Audited & Verified" else "supplied", "name": c.name, "short_name": c.shortName, "city_state": f"{c.location.city}, {c.location.state}",
        "region": c.location.region, "nirf_rank": c.nirfRank, "fit": f,
        "four_year_cost_inr": c.fees.totalFourYearCostINR,
        "headline_ctc_lpa": p.headlineCTC, "median_base_lpa": p.medianBaseSalary,
        "placed": p.actuallyPlaced, "eligible": p.eligibleStudents, "placement_rate": p.disclosedPlacementRate,
        "payback": payback(c.fees.totalFourYearCostINR, p.medianBaseSalary, a),
        "source_url": c.sources.nirfDisclosureUrl,
        "accreditation": c.accreditation, "commercial_relationship": c.commercialRelationship,
    }


def recommend(stream: str, budget_lakhs: float, region: str, a: Assumptions, opts: dict | None = None, **user) -> dict:
    """`opts` (seat_type, gender, category_rank) only feeds the cutoff-only list; audited cards keep the OPEN, CSE basis (D-29)."""
    has_table = bool(cutoff_rows())  # the JoSAA cutoff table is optional; without it only the college records are used
    if stream not in BRANCH_GROUPS or (stream not in SUPPORTED_STREAMS and not has_table):
        return {"supported": False, "message": f"Data currently covers: {', '.join(SUPPORTED_STREAMS)}", "deck": {}, "matches": []}
    if stream not in SUPPORTED_STREAMS:  # other branches: official JoSAA closing ranks only, every institute in the table (D-59)
        extra = {"cutoff_only": options(stream, a, percentile=user.get("percentile"), jee_advanced_rank=user.get("jee_advanced_rank"),
                                        include_audited=True, **(opts or {}))}
        return {"supported": True, "message": f"Cost and placement are available for {', '.join(SUPPORTED_STREAMS)} only. Showing cutoff-only options for {stream}.",
                "deck": {"safe_anchor": None, "sweet_spot": None, "dream_reach": None}, "matches": [], "needs_more_input": [], **extra}
    pool = [c for c in colleges().values()
            if c.fees.totalFourYearCostINR <= budget_lakhs * 100_000 and (region == "All" or c.location.region == region)]
    cards = [card(c, a, fit(c, a, **user)) for c in pool]
    ranked = sorted(cards, key=lambda x: x["nirf_rank"])
    deck = {}
    for slot, tier in (("safe_anchor", "Safe"), ("sweet_spot", "Target"), ("dream_reach", "Reach")):
        deck[slot] = next((x for x in ranked if x["fit"]["tier"] == tier), None)
    unrated = [x for x in ranked if x["fit"]["tier"] is None]
    return {"supported": True, "deck": deck, "matches": ranked, "needs_more_input": [
        {"id": x["id"], "reason": x["fit"]["reason"]} for x in unrated]}
