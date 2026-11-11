"""Loads the verified college dataset (data/colleges/*.json) once."""
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


def get_college(cid: str) -> College:
    try:
        return colleges()[cid]
    except KeyError:
        raise KeyError(f"unknown college '{cid}'")
