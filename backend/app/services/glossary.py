"""Grounded glossary answers (T-15.12). The text shown is always a curated entry from data/glossary.json. Matching is a small in-memory
TF-IDF; the model (optional) may only pick among the top three entries, never write the answer. Below the score threshold: no answer."""
import json
import math
import re
from collections import Counter
from functools import lru_cache
from typing import List, Optional, Tuple

from ..config import ROOT
from ..llm.client import LLM
from . import intake

THRESHOLD = 0.12
TOKEN = re.compile(r"[a-z0-9]+|[ऀ-ॿ]+")
STOP = {"what", "does", "is", "the", "a", "an", "of", "mean", "means", "meaning", "define", "explain", "me", "to", "in", "for", "and", "my",
        "क्या", "है", "होता", "का", "की", "के", "में", "मतलब", "अर्थ", "बताओ", "बताइए"}


def _tokens(s: str) -> List[str]:
    return [w for w in TOKEN.findall(s.translate(intake.DEV).lower()) if w not in STOP]


@lru_cache(maxsize=1)
def entries() -> list:
    return json.loads((ROOT / "data" / "glossary.json").read_text())["entries"]


@lru_cache(maxsize=1)
def _index() -> Tuple[list, dict]:
    docs = [Counter(_tokens(" ".join([e["term"]["en"], e["term"]["hi"], e["keywords"]]))) for e in entries()]
    df = Counter(w for d in docs for w in d)
    n = len(docs)
    idf = {w: math.log((n + 1) / (c + 0.5)) for w, c in df.items()}
    return docs, idf


def rank(query: str, k: int = 3) -> List[Tuple[dict, float]]:
    docs, idf = _index()
    q = Counter(_tokens(query))
    if not q:
        return []
    qn = math.sqrt(sum((c * idf.get(w, 0)) ** 2 for w, c in q.items())) or 1
    scored = []
    for e, d in zip(entries(), docs):
        dn = math.sqrt(sum((c * idf[w]) ** 2 for w, c in d.items())) or 1
        dot = sum(c * idf.get(w, 0) * d.get(w, 0) * idf.get(w, 0) for w, c in q.items())
        scored.append((e, dot / (qn * dn)))
    return [x for x in sorted(scored, key=lambda x: -x[1])[:k] if x[1] >= THRESHOLD]


def best(query: str) -> Optional[dict]:
    r = rank(query, 1)
    return r[0][0] if r else None


def lookup(query: str, llm: Optional[LLM] = None) -> Optional[dict]:
    cands = [e for e, _ in rank(query)]
    if len(cands) > 1 and llm:
        ids = [e["id"] for e in cands]
        got = llm.json("Pick the glossary entry that best answers the question. Reply JSON {\"id\": \"<one of the ids>\"}.",
                       f"Question: {query}\nIds: {', '.join(ids)}", {"type": "object", "properties": {"id": {"type": "string", "enum": ids}}, "required": ["id"]})
        if got and got.get("id") in ids:
            return next(e for e in cands if e["id"] == got["id"])
    return cands[0] if cands else None
