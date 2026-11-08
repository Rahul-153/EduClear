"""Campus tech kit (FR-08, data manual section 3 step 5). Live prices from Channel3; labelled sample listings if unavailable."""
from typing import Dict, List

import httpx

from ..config import settings

CHANNEL3_URL = "https://api.trychannel3.com/v1/search"  # per DATA_INGESTION_MANUAL section 2
REQUIREMENTS: Dict[str, List[dict]] = {
    "Computer Science": [
        {"id": "laptop", "label": "GPU laptop (16 GB RAM, RTX 3050/4060-class)", "query": "laptop RTX 4060 16GB RAM", "min_usd": 500},
        {"id": "peripherals", "label": "Peripherals (wireless mouse and headset)", "query": "wireless mouse headset", "min_usd": 10},
    ],
}
# Offline fallback: generic, clearly labelled illustrative listings (not live prices, not real products).
SAMPLE = {"laptop": ("Sample listing: GPU laptop, 16 GB RAM, RTX 4060-class", 85_000),
          "peripherals": ("Sample listing: wireless mouse and headset", 3_500)}
_cache: Dict[str, dict] = {}


def _offers(it: dict) -> List[dict]:
    """Channel3 v1 nests prices: product.offers[].price.{price,currency} with an availability flag and the retailer URL."""
    out = []
    for o in it.get("offers") or []:
        pr = o.get("price") or {}
        if pr.get("price") is None or o.get("availability") not in (None, "InStock"):
            continue
        out.append({"title": it.get("title"), "price": float(pr["price"]), "currency": (pr.get("currency") or "USD").upper(), "url": o.get("url")})
    return out


def _parse(j: object) -> List[dict]:
    items = j if isinstance(j, list) else next((j[k] for k in ("products", "items", "results", "data") if isinstance(j, dict) and isinstance(j.get(k), list)), [])
    out = []
    for it in items:
        if it.get("offers"):
            out.extend(_offers(it))
            continue
        price = it.get("price")
        cur = None
        if isinstance(price, dict):
            cur, price = price.get("currency"), price.get("price", price.get("amount"))
        if price is None or not it.get("title", it.get("name")):
            continue
        out.append({"title": it.get("title", it.get("name")), "price": float(price), "currency": (cur or "USD").upper(),
                    "url": it.get("url") or it.get("link")})
    return out


def _to_inr(price: float, cur: str) -> int:
    return round(price) if cur == "INR" else round(price / settings.inr_to_usd_rate)  # fixed documented rate, D-08


def _live(query: str, min_usd: float = 0) -> dict:
    r = httpx.post(CHANNEL3_URL, headers={"x-api-key": settings.channel3_api_key}, json={"query": query, "limit": 30}, timeout=20)
    r.raise_for_status()
    # a cheap accessory must not stand in for the item (a laptop sleeve is not a laptop), so apply a per-item floor
    cands = [c for c in _parse(r.json()) if (c["price"] if c["currency"] == "USD" else c["price"] * settings.inr_to_usd_rate) >= min_usd]
    if not cands:
        raise ValueError("no priced results above the item's price floor")
    best = min(cands, key=lambda c: c["price"])
    return {"title": best["title"], "price_inr": _to_inr(best["price"], best["currency"]), "url": best["url"],
            "currency_note": None if best["currency"] == "INR" else f"Listed in {best['currency']}, converted at the fixed demo rate"}


def kit(stream: str = "Computer Science") -> dict:
    reqs = REQUIREMENTS.get(stream)
    if not reqs:
        return {"supported": False, "message": "Kit definitions currently cover Computer Science."}
    items, sources, reasons = [], set(), set()
    for r in reqs:
        try:
            if not settings.channel3_api_key:
                raise LookupError("no key")
            got, src = _live(r["query"], r.get("min_usd", 0)), "channel3-live"
            _cache[r["id"]] = got
        except Exception as e:  # noqa: BLE001 - any failure falls back so the demo never breaks (NFR-04)
            if settings.channel3_api_key:
                reasons.add(f"{type(e).__name__}: {str(e)[:120]}")  # never includes the key
            if r["id"] in _cache:
                got, src = _cache[r["id"]], "channel3-cached"
            else:
                title, price = SAMPLE[r["id"]]
                got, src = {"title": title, "price_inr": price, "url": None, "currency_note": None}, "sample"
        sources.add(src)
        items.append({"id": r["id"], "requirement": r["label"], **got, "source": src})
    total = sum(i["price_inr"] for i in items)
    return {"supported": True, "items": items, "total_inr": total, "sample_data": "sample" in sources,
            "sources": sorted(sources), "fallback_reason": sorted(reasons) or None, "pay_in_4_inr": round(total / 4),
            "note": "Sample listings are illustrative and not live prices." if "sample" in sources else "Live Channel3 listings."}
