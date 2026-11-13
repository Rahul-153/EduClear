"""Sourced admissions timeline and refund policy (data/admissions/*.json)."""
import json
from datetime import date
from functools import lru_cache
from typing import Optional

from ..config import ROOT

DIR = ROOT / "data" / "admissions"


@lru_cache(maxsize=1)
def timeline_data() -> dict:
    return json.loads((DIR / "timeline.json").read_text())


@lru_cache(maxsize=1)
def refund_policy() -> dict:
    return json.loads((DIR / "refund_policy.json").read_text())


@lru_cache(maxsize=1)
def josaa_rules() -> dict:
    """Freeze / float / slide and withdrawal clauses, quoted from the saved JoSAA Business Rules (T-16.02)."""
    return json.loads((DIR / "josaa_rules.json").read_text())


def timeline(today: Optional[date] = None) -> dict:
    today = today or date.today()
    out = []
    for e in timeline_data()["events"]:
        start = date.fromisoformat(e["start"])
        end = date.fromisoformat(e["end"]) if e.get("end") else start
        status = "upcoming" if today < start else "ongoing" if today <= end else "past"
        out.append({**e, "status": status, "days_until_start": (start - today).days, "days_until_end": (end - today).days})
    d = timeline_data()
    return {"cycle": d["cycle"], "retrieved_at": d["retrievedAt"], "seat_acceptance_fee": d["seatAcceptanceFee"],
            "events": out, "unverified": d.get("unverified", []),
            "disclaimer": f"Dates shown are from the latest published cycle (JoSAA {d['cycle']}); the next cycle is not yet published."}
