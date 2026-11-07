"""Loads the verified college dataset (data/colleges/*.json) once."""
from functools import lru_cache
from typing import Dict

from scripts.college_model import College

from .config import settings


@lru_cache(maxsize=1)
def colleges() -> Dict[str, College]:
    out = {}
    for p in sorted(settings.data_dir.glob("*.json")):
        c = College.model_validate_json(p.read_text())
        out[c.id] = c
    return out


def get_college(cid: str) -> College:
    try:
        return colleges()[cid]
    except KeyError:
        raise KeyError(f"unknown college '{cid}'")
