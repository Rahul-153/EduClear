"""Smart Sentence recommendation: budget/region filter + fit tier + payback (FR-01, FR-03)."""

from ..data import colleges
from ..engines.assumptions import Assumptions
from ..engines.fit import fit
from ..engines.roi import payback

SUPPORTED_STREAMS = ["Computer Science"]  # dataset covers CSE only (D-29)


def card(c, a: Assumptions, f: dict) -> dict:
    p = c.placement
    return {
        "id": c.id, "name": c.name, "short_name": c.shortName, "city_state": f"{c.location.city}, {c.location.state}",
        "region": c.location.region, "nirf_rank": c.nirfRank, "fit": f,
        "four_year_cost_inr": c.fees.totalFourYearCostINR,
        "headline_ctc_lpa": p.headlineCTC, "median_base_lpa": p.medianBaseSalary,
        "placed": p.actuallyPlaced, "eligible": p.eligibleStudents, "placement_rate": p.disclosedPlacementRate,
        "payback": payback(c.fees.totalFourYearCostINR, p.medianBaseSalary, a),
        "source_url": c.sources.nirfDisclosureUrl,
        "accreditation": c.accreditation, "commercial_relationship": c.commercialRelationship,
    }


def recommend(stream: str, budget_lakhs: float, region: str, a: Assumptions, **user) -> dict:
    if stream not in SUPPORTED_STREAMS:
        return {"supported": False, "message": f"Verified data currently covers: {', '.join(SUPPORTED_STREAMS)}", "deck": {}, "matches": []}
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
