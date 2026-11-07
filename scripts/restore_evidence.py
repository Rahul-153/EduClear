"""Re-download the evidence snapshots listed in data/colleges/*.json from their recorded official URLs into data/sources/<id>/
and compare each file's SHA-256 with the recorded one. Never overwrites a record; reports MATCH / DIFFERS / FAILED.
Dynamic pages (the JoSAA result page) are regenerated with scripts/scrape_josaa.py and normally differ byte-for-byte."""
import hashlib
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
cache = {}


def fetch(url):
    if url not in cache:
        r = requests.get(url, headers=UA, timeout=120)
        r.raise_for_status()
        cache[url] = r.content
    return cache[url]


def main(only=None):
    rows = []
    for f in sorted((ROOT / "data" / "colleges").glob("*.json")):
        c = json.loads(f.read_text())
        if only and c["id"] not in only:
            continue
        s = c["sources"]
        for name, want in s["snapshots"].items():
            urls = [p["url"] for p in s["provenance"].values() if p.get("snapshot") == name and p["url"].startswith("http")]
            if name == "nirf-2025-dcs.pdf":
                urls = [s["nirfDisclosureUrl"]]
            if name == "nirf-2025-engineering-ranking.html":
                urls = ["https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html"]
            if name.startswith("josaa-"):
                rows.append((c["id"], name, "SKIPPED", "regenerate with scripts/scrape_josaa.py")); continue
            if not urls:
                rows.append((c["id"], name, "FAILED", "no recorded URL")); continue
            dest = ROOT / "data" / "sources" / c["id"] / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                data = fetch(urls[0])
            except Exception as e:  # noqa: BLE001
                rows.append((c["id"], name, "FAILED", f"{type(e).__name__} {urls[0]}")); print(rows[-1], flush=True); continue
            dest.write_bytes(data)
            ok = hashlib.sha256(data).hexdigest() == want
            rows.append((c["id"], name, "MATCH" if ok else "DIFFERS", urls[0])); print(rows[-1][:3], flush=True)
    from collections import Counter
    print(Counter(r[2] for r in rows))
    (ROOT / "data" / "restore_report.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
