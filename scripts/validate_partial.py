"""Validate data/partial/*.json (partly verified records, D-49). Exit code 1 if any record fails.

Checks: model shape, placement gates (partial_model.gate_errors), file name equals id, JoSAA name exists in the shipped
cutoff table and is unique, and the saved NIRF PDF still hashes to the recorded SHA-256 (skipped with a notice when the
git-ignored evidence folder is absent, as in validate_data.py).
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from partial_model import PartialCollege, gate_errors  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    names = {r[0] for r in sqlite3.connect(ROOT / "data" / "cutoffs_2025.sqlite").execute("SELECT DISTINCT institute FROM cutoffs")}
    audited = {p.stem for p in (ROOT / "data" / "colleges").glob("*.json")}
    files = sorted((ROOT / "data" / "partial").glob("*.json"))
    seen, bad, skipped = set(), 0, 0
    for f in files:
        errs = []
        try:
            r = PartialCollege.model_validate_json(f.read_text())
        except Exception as e:  # noqa: BLE001 - report any shape error for this file and continue
            print(f"FAIL {f.name}: {e}")
            bad += 1
            continue
        errs += gate_errors(r)
        if f.stem != r.id:
            errs.append("file name must equal id")
        if r.id in audited:
            errs.append("id also has an audited record")
        if r.josaaName not in names:
            errs.append("JoSAA name not in the cutoff table")
        if r.josaaName in seen:
            errs.append("duplicate JoSAA name")
        seen.add(r.josaaName)
        snap = ROOT / "data" / "sources" / r.id / r.source.snapshot
        if snap.exists():
            if hashlib.sha256(snap.read_bytes()).hexdigest() != r.source.sha256:
                errs.append("snapshot hash differs from the record")
        else:
            skipped += 1
        print(("FAIL " if errs else "ok   ") + f.name + (": " + "; ".join(errs) if errs else ""))
        bad += bool(errs)
    if skipped:
        print(f"notice: {skipped} snapshot(s) not on disk (evidence folder is git-ignored); hash re-check skipped for them")
    print(f"{len(files) - bad}/{len(files)} partial records valid")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
