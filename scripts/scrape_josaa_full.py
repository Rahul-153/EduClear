"""Pull the whole JoSAA opening/closing-rank archive (plan: DATA_PLAN_V2.md, phase 1).

For every year x round x institute type the official form is submitted once with Institute=ALL,
Branch=ALL, Seat type=ALL. Raw result pages are saved gzip-compressed under data/evidence/josaa/
(git-ignored) and the parsed rows go to data/evidence/josaa.sqlite. A manifest with row counts and
SHA-256 of each raw page is written to data/josaa_manifest.csv (small, committed). Resumable: pulls
already in the manifest are skipped. Nothing is estimated; pages that fail are logged, not skipped silently.

Usage: python scripts/scrape_josaa_full.py [--years 2025 2024 ...] [--rounds 1..6] [--types IIT NIT 3IT CFI]
"""
import argparse
import csv
import gzip
import hashlib
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scrape_josaa as J  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "data" / "evidence" / "josaa"
DB = ROOT / "data" / "evidence" / "josaa.sqlite"
MANIFEST = ROOT / "data" / "josaa_manifest.csv"
P = J.P
FIELDS = ["year", "round", "inst_type", "file", "rows", "sha256_raw", "header", "retrieved_at"]


def cells(row):
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]


def parse(html):
    rows = [cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)]
    header = next((r for r in rows if r and r[0] == "Institute"), None)
    if header is None:
        return None, []
    return header, [r for r in rows if len(r) == len(header) and r is not header and r[0] != "Institute"]


def to_int(v):
    """Rank as a number (int when whole). Handles the site's scientific notation (e.g. 1.04465e+006); '50P' keeps 50 and is flagged is_prep."""
    v = (v or "").strip()
    if re.fullmatch(r"\d+P?", v):
        return int(v.rstrip("P"))
    if re.fullmatch(r"\d+(\.\d+)?([eE]\+?\d+)?", v):  # decimals (e.g. 10.01) and scientific notation are real published values
        f = float(v)
        return int(f) if f == int(f) else f
    return None


def insert_rows(db, year, rnd, itype, header, rows):
    idx = {h: i for i, h in enumerate(header)}
    fixed = ("Institute", "Academic Program Name", "Quota", "Seat Type", "Gender", "Opening Rank", "Closing Rank")
    n = 0
    with db:
        for r in rows:
            if r[idx["Institute"]] in ("", "\xa0", "&nbsp;"):  # footer padding row
                continue
            o, c = r[idx["Opening Rank"]], r[idx["Closing Rank"]]
            extra = "|".join(f"{h}={r[i]}" for h, i in idx.items() if h not in fixed)
            db.execute("INSERT INTO cutoffs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                int(year), int(rnd), itype, r[idx["Institute"]], r[idx["Academic Program Name"]], r[idx["Quota"]],
                r[idx["Seat Type"]], r[idx["Gender"]] if "Gender" in idx else "", o, c, to_int(o), to_int(c),
                int(o.endswith("P") or c.endswith("P")), extra))
            n += 1
    return n


SCHEMA = """CREATE TABLE IF NOT EXISTS cutoffs(year INT, round INT, inst_type TEXT, institute TEXT, program TEXT,
            quota TEXT, seat_type TEXT, gender TEXT, opening_raw TEXT, closing_raw TEXT, opening REAL, closing REAL,
            is_prep INT, extra TEXT)"""


def rebuild():
    """Re-parse every saved raw page listed in the manifest into a fresh sqlite file (no network)."""
    DB.unlink(missing_ok=True)
    db = sqlite3.connect(DB)
    db.execute(SCHEMA)
    total = 0
    for r in csv.DictReader(MANIFEST.open()):
        header, rows = parse(gzip.decompress((ROOT / r["file"]).read_bytes()).decode())
        total += insert_rows(db, r["year"], r["round"], r["inst_type"], header, rows)
    print(f"rebuilt {DB.name}: {total} rows")


def pull(s, year, rnd, itype):
    html = s.get(J.URL, headers=J.UA, timeout=90).text
    vals = {P + "ddlYear": year}
    html = J.post(s, html, P + "ddlYear", vals)
    if rnd not in {v for v, _ in J.options(html, "ddlroundno")}:
        return "NOROUND"
    vals[P + "ddlroundno"] = rnd
    html = J.post(s, html, P + "ddlroundno", vals)
    if itype not in {v for v, _ in J.options(html, "ddlInstype")}:
        return None
    vals[P + "ddlInstype"] = itype
    html = J.post(s, html, P + "ddlInstype", vals)
    vals[P + "ddlInstitute"] = "ALL"
    html = J.post(s, html, P + "ddlInstitute", vals)
    vals[P + "ddlBranch"] = "ALL"
    html = J.post(s, html, P + "ddlBranch", vals)
    vals[P + "ddlSeatType"] = "ALL"
    vals[P + "btnSubmit"] = "Submit"
    return J.post(s, html, P + "btnSubmit", vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", default=[str(y) for y in range(2025, 2015, -1)])
    ap.add_argument("--rounds", nargs="*", default=["6", "1", "2", "3", "4", "5"])
    ap.add_argument("--types", nargs="*", default=["IIT", "NIT", "3IT", "CFI"])
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--rebuild", action="store_true", help="re-parse saved pages into a fresh database, no network")
    a = ap.parse_args()
    if a.rebuild:
        return rebuild()
    EVID.mkdir(parents=True, exist_ok=True)
    done = set()
    if MANIFEST.exists():
        done = {(r["year"], r["round"], r["inst_type"]) for r in csv.DictReader(MANIFEST.open())}
    new_manifest = not MANIFEST.exists()
    db = sqlite3.connect(DB)
    db.execute(SCHEMA)
    mf = MANIFEST.open("a", newline="")
    w = csv.DictWriter(mf, FIELDS)
    if new_manifest:
        w.writeheader()
    s = requests.Session()
    for rnd in a.rounds:
        for year in a.years:
            for itype in a.types:
                if (year, rnd, itype) in done:
                    continue
                try:
                    html = pull(s, year, rnd, itype)
                except Exception as e:  # noqa: BLE001
                    print(f"FAIL {year} r{rnd} {itype}: {type(e).__name__} {e}", flush=True)
                    continue
                if html == "NOROUND":
                    print(f"NOROUND {year} r{rnd} (round not in the archive for that year)", flush=True)
                    continue
                if html is None:
                    print(f"NOTYPE {year} r{rnd} {itype}", flush=True)
                    continue
                header, rows = parse(html)
                if header is None or not rows:
                    print(f"EMPTY {year} r{rnd} {itype} ({len(html)} bytes)", flush=True)
                    continue
                d = EVID / year
                d.mkdir(exist_ok=True)
                fn = d / f"round{rnd}_{itype}.html.gz"
                raw = html.encode()
                fn.write_bytes(gzip.compress(raw))
                n = insert_rows(db, year, rnd, itype, header, rows)
                w.writerow(dict(year=year, round=rnd, inst_type=itype, file=str(fn.relative_to(ROOT)), rows=n,
                                sha256_raw=hashlib.sha256(raw).hexdigest(), header="|".join(header),
                                retrieved_at=time.strftime("%Y-%m-%d")))
                mf.flush()
                print(f"OK {year} r{rnd} {itype}: {n} rows", flush=True)
                time.sleep(a.delay)


if __name__ == "__main__":
    main()
