"""Backtest of the round history (PLAN_ROUND_COPILOT.md, T-16.04). A measurement, not a pass mark.

Question: when a student was just outside a seat's closing rank after round r of the test year, how often did the seat
reach that rank by the last round, grouped by what the previous five years showed? Two readings of the past are measured:
"relative" (did the closing rank move by at least the share the student is short by) and "absolute" (did the past
closing rank reach the student's rank itself). The app uses the relative one whenever it knows this round's closing rank.
A case = one seat x one round (all but the last) x one gap (the student's rank is 2%, 5% or 10% beyond that round's
closing rank). Cases with fewer than 3 past years of data are counted apart.
Usage: python scripts/backtest_rounds.py [--year 2025]
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.data import round_history  # noqa: E402
from backend.app.engines import rounds as eng  # noqa: E402

GAPS = (1.02, 1.05, 1.10)
BUCKETS = ("no past year", "fewer than half", "half or more", "every past year")


def bucket(reached: int, n: int) -> str:
    return BUCKETS[0] if reached == 0 else BUCKETS[3] if reached == n else BUCKETS[2] if reached * 2 >= n else BUCKETS[1]


def run(year: int = 2025) -> dict:
    h = round_history()
    total, use_years = h["rounds"][year], eng.history_years(h["rounds"], year)
    out = {"year": year, "history_years": use_years, "too_little_history": 0,
           "by_gap": {basis: {g: {b: [0, 0] for b in BUCKETS} for g in GAPS} for basis in ("relative", "absolute")}}  # [cases, reached by the last round]
    for seat in h["seats"].values():
        now = seat["years"].get(year)
        if now is None:
            continue
        for rnd in range(1, total):
            later = [c for c in now[rnd:total] if c is not None]
            if now[rnd - 1] is None or not later:
                continue
            for g in GAPS:
                rank = math.ceil(now[rnd - 1] * g)
                if rank <= now[rnd - 1]:
                    continue
                for basis, closing_now in (("relative", now[rnd - 1]), ("absolute", None)):
                    m = eng.movement(seat["years"], rnd, rank, use_years, closing_now)
                    if m["years_with_data"] < 3:
                        out["too_little_history"] += basis == "relative"
                        continue
                    cell = out["by_gap"][basis][g][bucket(m["years_reached"], m["years_with_data"])]
                    cell[0] += 1
                    cell[1] += rank <= max(later)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2025)
    r = run(ap.parse_args().year)
    print(f"Test year {r['year']}, history {r['history_years']}; cases skipped for fewer than 3 past years: {r['too_little_history']}")
    for basis, gaps in r["by_gap"].items():
        for g, cells in gaps.items():
            print(f"\n{basis}: student's rank {round((g - 1) * 100)}% beyond the closing rank of the round")
            print("| Past years that say yes | Cases | Reached it in the test year | Share |\n|---|---|---|---|")
            for b in BUCKETS:
                n, k = cells[b]
                print(f"| {b} | {n:,} | {k:,} | {k / n:.0%} |" if n else f"| {b} | 0 | 0 | n/a |")
