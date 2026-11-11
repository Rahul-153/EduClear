"""Export one year / round of the JoSAA archive to a small SQLite file the app ships with (PLAN_VIEWS_AND_DATA.md, B1).

Reads data/evidence/josaa.sqlite (git-ignored, built by scrape_josaa_full.py) and writes data/cutoffs_2025.sqlite
(committed). Rows are copied as published; nothing is computed or filled. Preparatory-course ranks and rows without a
closing rank are kept out of the app's matching, not deleted: the `is_prep` flag stays on the row.
The only change to the text is decoding HTML entities in names (the archive page prints "&amp;"); no number is touched.
Usage: python scripts/export_cutoffs.py [--year 2025] [--round 6]
"""
import argparse
import csv
import html
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "evidence" / "josaa.sqlite"
MANIFEST = ROOT / "data" / "josaa_manifest.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--round", type=int, default=6)
    a = ap.parse_args()
    out = ROOT / "data" / f"cutoffs_{a.year}.sqlite"
    src = sqlite3.connect(SRC)
    clean = lambda r: tuple(html.unescape(v) if k in (1, 2, 3, 4, 5) else v for k, v in enumerate(r))  # text columns only
    rows = src.execute(
        """SELECT inst_type, institute, program, quota, seat_type, gender, opening, closing, is_prep
           FROM cutoffs WHERE year=? AND round=?""", (a.year, a.round)).fetchall()
    rows = [clean(r) for r in rows]
    pages = [r for r in csv.DictReader(MANIFEST.open()) if int(r["year"]) == a.year and int(r["round"]) == a.round]
    expected = sum(int(r["rows"]) for r in pages) - len(pages)  # every saved page ends with one empty footer row that the importer skips
    assert len(rows) == expected, f"exported {len(rows)} rows but the manifest implies {expected}"
    out.unlink(missing_ok=True)
    dst = sqlite3.connect(out)
    dst.execute("""CREATE TABLE cutoffs(inst_type TEXT, institute TEXT, program TEXT, quota TEXT, seat_type TEXT, gender TEXT,
                   opening REAL, closing REAL, is_prep INT)""")
    dst.execute("CREATE TABLE meta(key TEXT, value TEXT)")
    dst.executemany("INSERT INTO cutoffs VALUES (?,?,?,?,?,?,?,?,?)", rows)
    dst.executemany("INSERT INTO meta VALUES (?,?)", [("year", str(a.year)), ("round", str(a.round)), ("rows", str(len(rows))),
                    ("source", "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx")])
    dst.commit()
    dst.execute("VACUUM")
    dst.close()
    print(f"{out.relative_to(ROOT)}: {len(rows)} rows (matches manifest), {out.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
