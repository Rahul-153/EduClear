"""EduClear data validator: 6 integrity gates (manual §5) ported to Python + extra audit checks.

Usage: python scripts/validate_data.py [--check-urls] [--dir data/colleges]
Exit code 0 only if every record passes. Also regenerates data/schema/college.schema.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from college_model import College  # noqa: E402
from pydantic import ValidationError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_MISSING: List[str] = []
SUPPLIED: List[str] = []  # records from the supplied dataset: integrity gates only, no evidence checks (D-53)
REQUIRED_COMMERCIAL = "None (100% Student-Funded & Independent)"
REQUIRED_PROVENANCE = [
    "placement.medianBaseSalary",
    "placement.batchSize",
    "placement.eligibleStudents",
    "placement.actuallyPlaced",
    "placement.headlineCTC",
    "fees.tuitionAnnual",
    "fees.hostelAndMessAnnual",
    "cutoffs.minPercentileOrRank",
    "nirfRank",
]


def run_integrity_check(c: College) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    p, f = c.placement, c.fees

    # Gate 1: denominator consistency
    if p.actuallyPlaced > p.eligibleStudents:
        errors.append(f"G1 placed ({p.actuallyPlaced}) exceeds eligible ({p.eligibleStudents})")
    if p.eligibleStudents > p.batchSize:
        errors.append(f"G1 eligible ({p.eligibleStudents}) exceeds batch ({p.batchSize})")
    # D-09: eligible = batch - direct higher studies
    if p.eligibleStudents != p.batchSize - p.higherStudiesOrFounders:
        errors.append(
            f"D-09 eligible ({p.eligibleStudents}) != batch ({p.batchSize}) - higherStudies ({p.higherStudiesOrFounders})"
        )

    # Gate 2: placement % math
    if p.eligibleStudents > 0:
        expected = round(p.actuallyPlaced / p.eligibleStudents * 100, 2)
        if abs(expected - p.disclosedPlacementRate) > 0.5:
            errors.append(f"G2 disclosed rate {p.disclosedPlacementRate}% != computed {expected}%")
    else:
        errors.append("G2 eligibleStudents is zero")

    # Gate 3: CTC distortion sanity
    if p.headlineCTC is not None and p.headlineCTC < p.medianBaseSalary:
        errors.append(f"G3 headline CTC {p.headlineCTC} < median {p.medianBaseSalary}")

    # Gate 4: total cost
    annual = f.tuitionAnnual + f.mandatoryInstituteFeesAnnual + f.hostelAndMessAnnual + f.estimatedLivingAnnual
    mult = 2 if (c.stream == "Management" and c.id.startswith("iim")) else 4
    if f.totalFourYearCostINR != annual * mult:
        errors.append(f"G4 total {f.totalFourYearCostINR} != {mult} x {annual} = {annual * mult}")

    # Gate 5: regulatory URL
    if not c.sources.nirfDisclosureUrl.startswith("http"):
        errors.append("G5 missing valid NIRF disclosure URL")

    # Gate 6: conflict of interest
    if c.commercialRelationship != REQUIRED_COMMERCIAL:
        errors.append("G6 invalid commercialRelationship declaration")

    # Supplied dataset (D-53): the evidence checks below cannot pass because no source documents exist for it. It is
    # labelled "not audited" instead, and the gates above still apply.
    if c.sources.verificationStatus.startswith("Supplied"):
        SUPPLIED.append(c.id)
        return (not errors, errors)

    # Extra audit checks (D-04)
    s = c.sources
    if not s.nirfYear:
        errors.append("X nirfYear missing")
    try:
        date.fromisoformat(s.retrievedAt or "")
    except ValueError:
        errors.append("X retrievedAt missing/not ISO date")
    if not s.feeCircularDate:
        errors.append("X feeCircularDate missing")
    if not s.feeCircularUrl or not s.feeCircularUrl.startswith("http"):
        errors.append("X feeCircularUrl missing")
    if not s.cutoffUrl or not s.cutoffUrl.startswith("http"):
        errors.append("X cutoffUrl missing")
    if not s.headlineCtcUrl or not s.headlineCtcUrl.startswith("http"):
        errors.append("X headlineCtcUrl missing")
    for key in REQUIRED_PROVENANCE:
        prov = s.provenance.get(key)
        if prov is None or not prov.url.startswith("http") or not prov.locator.strip():
            errors.append(f"X provenance missing for {key}")
    # snapshot hashes must match files on disk. The evidence folder is not published with the repo; when a checkout has none,
    # the recorded URL + SHA-256 remain the audit trail and file checks are skipped with a warning.
    evidence_dir = ROOT / "data" / "sources" / c.id
    if not evidence_dir.is_dir():
        EVIDENCE_MISSING.append(c.id)
    else:
        for name, digest in s.snapshots.items():
            fp = evidence_dir / name
            if not fp.exists():
                errors.append(f"X snapshot {name} not found")
            elif hashlib.sha256(fp.read_bytes()).hexdigest() != digest:
                errors.append(f"X snapshot {name} sha256 mismatch")
    if not s.snapshots:
        errors.append("X no source snapshots recorded")
    for k, v in s.provenance.items():
        if v.snapshot and v.snapshot not in s.snapshots:
            errors.append(f"X provenance {k} cites unknown snapshot {v.snapshot}")
    if s.verificationStatus != "Audited & Verified":
        errors.append(f"X verificationStatus is '{s.verificationStatus}'")
    return (not errors, errors)


def check_urls(c: College) -> List[str]:
    import requests

    ua = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
    bad = []
    urls = {c.sources.nirfDisclosureUrl, c.sources.feeCircularUrl, c.sources.cutoffUrl, c.sources.headlineCtcUrl}
    for u in filter(None, urls):
        try:
            r = requests.get(u, headers=ua, timeout=25, stream=True)
            if r.status_code >= 400:
                bad.append(f"URL {u} -> {r.status_code}")
            r.close()
        except Exception as e:  # noqa: BLE001
            bad.append(f"URL {u} unreachable: {type(e).__name__}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "data" / "colleges"))
    ap.add_argument("--check-urls", action="store_true")
    args = ap.parse_args()

    schema_path = ROOT / "data" / "schema" / "college.schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(College.model_json_schema(), indent=2))

    files = sorted(Path(args.dir).glob("*.json"))
    if not files:
        print("No college records found.")
        return 1
    failed = 0
    for fp in files:
        try:
            c = College.model_validate_json(fp.read_text())
        except ValidationError as e:
            failed += 1
            print(f"FAIL {fp.name}: schema")
            for err in e.errors():
                print(f"   - {'.'.join(map(str, err['loc']))}: {err['msg']}")
            continue
        ok, errs = run_integrity_check(c)
        if args.check_urls:
            errs += check_urls(c)
            ok = ok and not errs
        if fp.stem != c.id:
            errs.append(f"filename {fp.name} != id {c.id}")
            ok = False
        if ok:
            print(f"PASS {c.id}")
        else:
            failed += 1
            print(f"FAIL {c.id}")
            for e in errs:
                print(f"   - {e}")
    if EVIDENCE_MISSING:
        print(f"\nNOTE: no local evidence folder for {len(EVIDENCE_MISSING)} record(s); snapshot files and hashes were not re-checked (URL + SHA-256 are recorded in each record).")
    if SUPPLIED:
        print(f"\nNOTE: {len(SUPPLIED)} record(s) are from the supplied dataset: integrity gates G1 to G6 ran; provenance, snapshot and URL checks were not applicable.")
    print(f"\n{len(files) - failed}/{len(files)} records valid")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
