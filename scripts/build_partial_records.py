"""Build partly verified records for the IITs researched in the IIT round (PLAN_VIEWS_AND_DATA.md B4, D-49).

For each data/sources/iit-*/ folder without an audited record:
  1. read the staged NIRF row (prestage.json, written by iit_prestage.py);
  2. re-read the same row independently from the saved NIRF PDF text (pdftotext -layout);
  3. check the PDF's SHA-256 against the hash recorded in research.json / sha256.txt;
  4. run the integrity gates in partial_model.gate_errors.
Only a record that passes all four is written to data/partial/<id>.json. Anything else is reported with the reason and left out.
Usage: python scripts/build_partial_records.py [iit-indore ...]
"""
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from partial_model import PartialCollege, gate_errors  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "data" / "sources", ROOT / "data" / "partial"
CUTOFFS = ROOT / "data" / "cutoffs_2025.sqlite"
BATCH = "2023-24"
YEAR = re.compile(r"\d{4}-\d{2}")


def pdf_row(pdf: Path) -> dict | None:
    """The UG [4 Years] row graduating 2023-24, read from the PDF text layer: graduated, placed, median, higher studies."""
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    block, inside = [], False
    for line in text.splitlines():
        if "UG [4 Year" in line and "Placement" in line:
            inside = True
            continue
        if inside and re.search(r"UG \[5 Year|PG \[|Ph\.D", line):
            break
        if inside:
            block.append(line)
    rows = [ln for ln in block if re.match(r"\s*2020-21\s", ln) and f" {BATCH} " in ln + " "]
    if len(rows) != 1:
        return None
    nums = [int(n) for n in re.findall(r"(?<![\d-])\d+(?![\d-])", YEAR.sub(" ", rows[0]))]
    if len(nums) < 4 or nums[-2] < 100_000:
        return None
    return {"graduated": nums[-4], "placed": nums[-3], "medianSalary": nums[-2], "higherStudies": nums[-1]}


def recorded_sha(folder: Path, research: dict, snapshot: str) -> str | None:
    np_ = research.get("nirfPlacement") or (research.get("fields") or {}).get("nirfPlacement") or {}
    for s in np_.get("sources", []):
        if s.get("snapshot") == snapshot and s.get("sha256"):
            return s["sha256"]
    f = folder / "sha256.txt"
    if f.exists():
        for ln in f.read_text().splitlines():
            h, _, name = ln.partition("  ")
            if name.strip() == snapshot:
                return h
    return None


def build(iid: str, josaa_names: set) -> tuple[PartialCollege | None, str]:
    folder = SRC / iid
    pre = json.loads((folder / "prestage.json").read_text())
    research = json.loads((folder / "research.json").read_text())
    if pre["josaaName"] not in josaa_names:
        return None, f"JoSAA name '{pre['josaaName']}' not in the cutoff table"
    # Staged rows can include the UG [5 Years] block after the 4-year rows, so the first 2023-24 row is compared with the
    # block-aware PDF reading below; if the first one is not the UG4 row the two differ and the record is skipped.
    staged = [r for r in pre["nirfPlacementUG4"] if r["graduatingYear"] == BATCH]
    if not staged:
        return None, "no staged row for 2023-24"
    np_ = research.get("nirfPlacement") or (research.get("fields") or {}).get("nirfPlacement") or {}
    srcs = np_.get("sources", [])
    snapshot = srcs[0]["snapshot"] if srcs and srcs[0].get("snapshot") else "nirf-2025-dcs.pdf"
    pdf = folder / snapshot
    if not pdf.exists():
        return None, f"snapshot {snapshot} not saved"
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    want = recorded_sha(folder, research, snapshot)
    if want and want != sha:
        return None, "snapshot hash differs from the recorded hash"
    read = pdf_row(pdf)
    if read is None:
        return None, "PDF row could not be read"
    s = staged[0]
    if read != {k: s[k] for k in read}:
        return None, f"PDF row {read} differs from staged row"
    eligible = read["graduated"] - read["higherStudies"]
    url = srcs[0]["url"] if srcs and srcs[0].get("url", "").startswith("http") else (
        f"https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/{pre['nirfCode']}.pdf" if pre.get("nirfCode") else None)
    if url is None:
        return None, "no source URL"
    short = re.sub(r"^Indian Institute of Technology", "IIT", pre["josaaName"])
    rec = PartialCollege.model_validate({
        "id": iid, "josaaName": pre["josaaName"], "name": pre["josaaName"], "shortName": short, "type": "IIT",
        "nirfRank": pre.get("nirfRank"),
        "placement": {"batch": BATCH, "graduated": read["graduated"], "higherStudies": read["higherStudies"], "eligible": eligible,
                      "placed": read["placed"], "placementRatePct": round(read["placed"] / eligible * 100, 2) if eligible > 0 else 0,
                      "medianSalaryInr": read["medianSalary"]},
        "verifiedFields": ["placement"], "notVerified": ["fees", "totalCost", "headlineCTC", "accreditation"],
        "source": {"url": url, "nirfYear": 2025, "retrievedAt": date.fromtimestamp(pdf.stat().st_mtime).isoformat(), "snapshot": snapshot,
                   "sha256": sha, "locator": "Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24"},
    })
    errs = gate_errors(rec)
    return (None, "; ".join(errs)) if errs else (rec, "ok")


def main() -> None:
    audited = {p.stem for p in (ROOT / "data" / "colleges").glob("*.json")}
    db = sqlite3.connect(CUTOFFS)
    names = {r[0] for r in db.execute("SELECT DISTINCT institute FROM cutoffs")}
    ids = sys.argv[1:] or sorted(p.name for p in SRC.glob("iit-*") if (p / "prestage.json").exists())
    OUT.mkdir(exist_ok=True)
    built = 0
    for iid in ids:
        if iid in audited:
            continue
        rec, why = build(iid, names)
        if rec:
            (OUT / f"{iid}.json").write_text(rec.model_dump_json(indent=2) + "\n")
            built += 1
            p = rec.placement
            print(f"OK    {iid}: graduated {p.graduated}, higher {p.higherStudies}, placed {p.placed}/{p.eligible} ({p.placementRatePct}%), median {p.medianSalaryInr}")
        else:
            (OUT / f"{iid}.json").unlink(missing_ok=True)
            print(f"SKIP  {iid}: {why}")
    print(f"{built} partial records written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
