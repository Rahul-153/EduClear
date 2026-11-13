"""Export round-by-round JoSAA closing ranks to a small SQLite file the app ships with (PLAN_ROUND_COPILOT.md, T-16.01).

Reads data/evidence/josaa.sqlite (git-ignored) and writes data/round_history.sqlite (committed): one row per
(year, institute, programme, quota, seat type, gender) with the published closing rank of each round. Rows are copied as
published; nothing is computed or filled, and a round the archive does not have stays NULL. Kept out: preparatory-course
ranks, PwD seat types, and programmes outside the five 4-year branch groups the app matches (services/cutoff_options.py).
The only change to the text is decoding HTML entities in names, as in export_cutoffs.py.
Usage: python scripts/export_round_history.py [--from-year 2020] [--to-year 2025]
"""
import argparse
import csv
import html
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "evidence" / "josaa.sqlite"
OUT = ROOT / "data" / "round_history.sqlite"
MANIFEST = ROOT / "data" / "josaa_manifest.csv"
# Same programme rule as backend/app/services/cutoff_options.py (kept in step by tests/test_rounds.py).
BRANCHES = re.compile(r"computer science|electronics (and|&) communication|electrical engineering|mechanical engineering|civil engineering", re.I)
EXCLUDE = re.compile(r"dual degree|mba|integrated|master|m\.tech", re.I)
SEAT_TYPES = ("OPEN", "EWS", "OBC-NCL", "SC", "ST")
MAX_ROUNDS = 6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-year", type=int, default=2020)
    ap.add_argument("--to-year", type=int, default=2025)
    a = ap.parse_args()
    src = sqlite3.connect(SRC)
    # 1. The archive must hold every row the manifest says was downloaded, for each year and round used.
    pages: dict = {}
    for r in csv.DictReader(MANIFEST.open()):
        k = (int(r["year"]), int(r["round"]))
        n, p = pages.get(k, (0, 0))
        pages[k] = (n + int(r["rows"]), p + 1)
    rounds = {}
    for (year, rnd), n in sorted({(y, r): c for y, r, c in src.execute(
            "SELECT year, round, COUNT(*) FROM cutoffs WHERE year BETWEEN ? AND ? GROUP BY 1, 2", (a.from_year, a.to_year))}.items()):
        total, n_pages = pages[(year, rnd)]
        assert n == total - n_pages, f"{year} round {rnd}: archive has {n} rows, manifest implies {total - n_pages}"  # one empty footer row per page
        rounds.setdefault(year, []).append(rnd)
    # 2. Pivot the kept rows: one row per seat and year, one column per round.
    seats: dict = {}
    for year, rnd, inst_type, inst, prog, quota, seat, gender, closing in src.execute(
            """SELECT year, round, inst_type, institute, program, quota, seat_type, gender, closing FROM cutoffs
               WHERE year BETWEEN ? AND ? AND is_prep = 0 AND closing IS NOT NULL""", (a.from_year, a.to_year)):
        inst, prog = html.unescape(inst), html.unescape(prog)
        if seat not in SEAT_TYPES or "(4 Years" not in prog or EXCLUDE.search(prog) or not BRANCHES.search(prog):
            continue
        row = seats.setdefault((year, inst_type, inst, prog, quota, seat, gender), [None] * MAX_ROUNDS)
        assert row[rnd - 1] is None, f"duplicate row: {year} round {rnd} {inst} {prog} {quota} {seat} {gender}"
        row[rnd - 1] = closing
    OUT.unlink(missing_ok=True)
    dst = sqlite3.connect(OUT)
    dst.execute("""CREATE TABLE closing(year INT, inst_type TEXT, institute TEXT, program TEXT, quota TEXT, seat_type TEXT,
                   gender TEXT, r1 REAL, r2 REAL, r3 REAL, r4 REAL, r5 REAL, r6 REAL)""")
    dst.execute("CREATE TABLE meta(key TEXT, value TEXT)")
    dst.executemany("INSERT INTO closing VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", [k + tuple(v) for k, v in sorted(seats.items())])
    dst.executemany("INSERT INTO meta VALUES (?,?)", [
        ("rows", str(len(seats))),
        ("rounds", ";".join(f"{y}:{max(r)}" for y, r in sorted(rounds.items()))),  # rounds present in the archive per year
        ("source", "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx")])
    dst.commit()
    dst.execute("VACUUM")
    dst.close()
    print(f"{OUT.relative_to(ROOT)}: {len(seats)} rows, rounds per year {dict((y, max(r)) for y, r in sorted(rounds.items()))}, "
          f"{OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
