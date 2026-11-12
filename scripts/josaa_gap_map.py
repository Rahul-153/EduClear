"""Phase 2 coverage gap map (DATA_PLAN_V2.md): for each JEE Main percentile, how many JoSAA programmes and
institutes have a final-round closing rank that a student at that percentile could reach, using only OPEN,
Gender-Neutral seats of NITs, IIITs and GFTIs (JEE Main CRL ranks; IIT ranks are JEE Advanced and are excluded).
Percentile to rank uses the engine's own rule (backend/app/engines/fit.percentile_to_rank).
Output: data/josaa_gap_map.md plus a ranked list of institutes by how many gap cells they would fill
(institutes that have no verified college record yet).
Usage: python scripts/josaa_gap_map.py [--year 2025] [--round 6]
"""
import argparse
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "evidence" / "josaa.sqlite"
PERCENTILES = [99.9, 99.75, 99.5, 99, 98, 97, 96, 95, 94.2, 92, 90, 85]
CANDIDATES = 1_475_103  # same constant as backend/app/engines/assumptions.py
VERIFIED = {  # official JoSAA names of the institutes that already have a verified record (DTU uses JAC Delhi, not JoSAA)
    "Malaviya National Institute of Technology Jaipur", "National Institute of Technology Calicut",
    "National Institute of Technology, Kurukshetra", "National Institute of Technology, Silchar",
    "National Institute of Technology Patna", "National Institute of Technology Raipur",
}


def rank(p):
    return max(1, round((100 - p) / 100 * CANDIDATES))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--round", type=int, default=6)
    a = ap.parse_args()
    db = sqlite3.connect(DB)
    rows = db.execute("""SELECT institute, program, quota, closing FROM cutoffs WHERE year=? AND round=? AND inst_type IN ('NIT','3IT','CFI')
                         AND seat_type='OPEN' AND gender='Gender-Neutral' AND closing IS NOT NULL AND is_prep=0""", (a.year, a.round)).fetchall()
    best = defaultdict(int)  # (institute, program) -> max closing rank over quotas
    for inst, prog, quota, closing in rows:
        best[(inst, prog)] = max(best[(inst, prog)], closing)
    out = [f"# JoSAA gap map ({a.year} round {a.round}, OPEN Gender-Neutral, NIT/IIIT/GFTI)", "",
           "A programme counts as reachable at a percentile when its most generous quota's closing rank is at or above the student's approximate rank. "
           "Percentile to rank: (100 - percentile)/100 x 1,475,103. Only OPEN seats are counted; category ranks need a category-rank mapping and are not in this table.", "",
           "| Percentile | Approx. rank | Programmes reachable | Institutes reachable | Institutes with a verified record that are reachable |", "|---|---|---|---|---|"]
    gain = defaultdict(int)
    for p in PERCENTILES:
        r = rank(p)
        reach = [(i, g) for (i, g), c in best.items() if c >= r]
        insts = {i for i, _ in reach}
        ver = insts & VERIFIED
        out.append(f"| {p} | {r:,} | {len(reach)} | {len(insts)} | {len(ver)} |")
        if len(ver) < 3:
            for i in insts:
                gain[i] += 1
    out += ["", "## Institutes ranked by gap percentiles they would fill (percentiles where fewer than 3 verified colleges are reachable)", "",
            "| Institute | Percentiles in the table where it is the only kind of option |", "|---|---|"]
    for i, n in sorted(gain.items(), key=lambda x: -x[1])[:40]:
        out.append(f"| {i} | {n} |")
    (ROOT / "data" / "josaa_gap_map.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[:20]))


if __name__ == "__main__":
    main()
