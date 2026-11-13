"""Loads the verified college dataset (data/colleges/*.json) once."""
import csv
import sqlite3
from functools import lru_cache
from typing import Dict, List

from scripts.college_model import College
from scripts.partial_model import PartialCollege

from .config import settings


@lru_cache(maxsize=1)
def colleges() -> Dict[str, College]:
    out = {}
    for p in sorted(settings.data_dir.glob("*.json")):
        c = College.model_validate_json(p.read_text())
        out[c.id] = c
    return out


CUTOFFS_DB = settings.data_dir.parent / "cutoffs_2025.sqlite"  # JoSAA 2025 final round, built by scripts/export_cutoffs.py


@lru_cache(maxsize=1)
def cutoff_rows() -> List[dict]:
    """The slim JoSAA table as published (about 12,000 rows). Empty list if the file is absent, so the app still runs."""
    if not CUTOFFS_DB.exists():
        return []
    db = sqlite3.connect(f"file:{CUTOFFS_DB}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in db.execute("SELECT * FROM cutoffs")]
    finally:
        db.close()


PARTIAL_DIR = settings.data_dir.parent / "partial"  # partly verified records (D-49), built by scripts/build_partial_records.py


@lru_cache(maxsize=1)
def partial_colleges() -> Dict[str, PartialCollege]:
    """Partly verified records keyed by the official JoSAA institute name, so they join the cutoff table."""
    out = {}
    for p in sorted(PARTIAL_DIR.glob("*.json")):
        r = PartialCollege.model_validate_json(p.read_text())
        out[r.josaaName] = r
    return out


BRANCH_CSV = settings.data_dir.parent / "supplied" / "branch_placements.csv"  # branch-level placement, supplied dataset (D-57), not audited


@lru_cache(maxsize=1)
def branch_placements() -> Dict[tuple, dict]:
    """(college id, branch code such as CSE, ECE, EE, ME, CE) -> that branch's placement row, numbers as supplied."""
    if not BRANCH_CSV.exists():
        return {}
    out = {}
    with BRANCH_CSV.open(newline="") as f:
        for r in csv.DictReader(f):
            out[(r["institute_id"], r["branch_code"])] = {
                "year": r["academic_year"], "eligible": int(r["eligible_students"]), "placed": int(r["placed_students"]),
                "rate": float(r["placement_rate_percent"]), "median": float(r["median_salary_lpa"]),
                "highest": float(r["highest_salary_lpa"]), "source_url": r["document_source_url"]}
    return out


def get_college(cid: str) -> College:
    try:
        return colleges()[cid]
    except KeyError:
        raise KeyError(f"unknown college '{cid}'")


ROUNDS_DB = settings.data_dir.parent / "round_history.sqlite"  # JoSAA closing rank per round, built by scripts/export_round_history.py


@lru_cache(maxsize=1)
def round_history() -> dict:
    """{"rounds": {year: rounds in the archive}, "seats": {(institute, program, quota, seat type, gender): {"inst_type", "years": {year: [r1..r6]}}}}.
    Closing ranks as published; None where the archive has no row. Empty if the file is absent, so the app still runs."""
    out: dict = {"rounds": {}, "seats": {}}
    if not ROUNDS_DB.exists():
        return out
    db = sqlite3.connect(f"file:{ROUNDS_DB}?mode=ro", uri=True)
    try:
        meta = dict(db.execute("SELECT key, value FROM meta"))
        out["rounds"] = {int(y): int(n) for y, n in (p.split(":") for p in meta["rounds"].split(";"))}
        for year, inst_type, *key, r1, r2, r3, r4, r5, r6 in db.execute("SELECT * FROM closing"):
            seat = out["seats"].setdefault(tuple(key), {"inst_type": inst_type, "years": {}})
            seat["years"][year] = [r1, r2, r3, r4, r5, r6]
    finally:
        db.close()
    return out
