"""The four counselling programs (UX spec section 3) and bookable slots. Times are IST wall-clock."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import List, Optional


@dataclass(frozen=True)
class Program:
    id: str
    title: str
    kind: str  # "1:1" | "cohort"
    minutes: int
    price_inr: int
    escrow: bool  # False = direct payment (cohort seat)
    capacity: int
    summary: str


PROGRAMS = {p.id: p for p in [
    Program("branch-vs-college", "Branch vs College Dilemma", "1:1", 45, 2499, True, 1,
            "Resolve core trade-offs: curriculum depth, branch-change rules and 5-year outcomes by department."),
    Program("josaa-audit", "JoSAA Choice-Filling Review", "1:1", 60, 2999, True, 1,
            "Audit of your 100+ preference list for order-inversion flaws and a round-by-round retention strategy."),
    Program("year1-roadmap", "Year 1 to First Job Roadmap", "cohort", 90, 999, False, 25,
            "Cohort masterclass (max 25): semester milestones, portfolio, internships and specialisation blueprint."),
    Program("family-consensus", "Parent-Student Consensus Session", "1:1", 60, 3499, True, 1,
            "Neutral review of your alignment matrix, loan-vs-cash-flow stress test and an agreed top-5 list."),
]}

COUNSELLOR = "Demo counsellor (sandbox profile)"  # no real person or credentials are claimed (D-33)


def slots(program: Program, today: Optional[date] = None) -> List[datetime]:
    today = today or date.today()
    out: List[datetime] = []
    d = today + timedelta(days=1)
    if program.kind == "cohort":
        while len(out) < 4:
            if d.weekday() == 5:  # Saturday 18:00
                out.append(datetime.combine(d, time(18, 0)))
            d += timedelta(days=1)
    else:
        while len(out) < 14:
            if d.weekday() < 5:  # weekdays 10:00 and 16:00
                out += [datetime.combine(d, time(10, 0)), datetime.combine(d, time(16, 0))]
            d += timedelta(days=1)
    return out
