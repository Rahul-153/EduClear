"""Parent-student alignment score and discussion guide (FR-02). Deterministic, equal weights."""
from typing import Dict, List

DIMENSIONS = {
    "brand_prestige": "Brand prestige",
    "branch_passion": "Branch passion",
    "location_safety": "Location and safety",
    "budget_strictness": "Budget strictness",
}
PROMPTS = {
    "brand_prestige": "Compare what the brand adds in audited median pay against the cost difference.",
    "branch_passion": "Check whether the preferred branch is open at the colleges both sides like, and its audited outcomes.",
    "location_safety": "Agree on regions and campus conditions that feel safe; shortlist colleges inside them.",
    "budget_strictness": "Fix a hard 4-year budget together and test it against the loan EMI plan.",
}


def score(student: Dict[str, int], parent: Dict[str, int]) -> dict:
    for who in (student, parent):
        if set(who) != set(DIMENSIONS) or any(not 1 <= v <= 5 for v in who.values()):
            raise ValueError("ratings must cover all four dimensions with values 1-5")
    gaps = {k: abs(student[k] - parent[k]) for k in DIMENSIONS}
    pct = round(100 * (1 - sum(gaps.values()) / (4 * len(DIMENSIONS))))
    guide: List[dict] = []
    for k, g in sorted(gaps.items(), key=lambda kv: -kv[1]):
        if g >= 2:
            higher = "student" if student[k] > parent[k] else "parent"
            guide.append({"dimension": DIMENSIONS[k], "gap": g, "higher_priority": higher, "prompt": PROMPTS[k]})
    return {"alignment_score": pct, "gaps": gaps, "discussion_guide": guide,
            "verdict": "Well aligned" if pct >= 80 else "Some trade-offs to discuss" if pct >= 55 else "Significant gaps; consider a family session"}
