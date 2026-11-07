import copy
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_data as vd  # noqa: E402
from college_model import College  # noqa: E402

PROV_KEYS = vd.REQUIRED_PROVENANCE


@pytest.fixture()
def good(tmp_path, monkeypatch):
    monkeypatch.setattr(vd, "ROOT", tmp_path)
    snap_dir = tmp_path / "data" / "sources" / "test-college"
    snap_dir.mkdir(parents=True)
    (snap_dir / "nirf.txt").write_text("x")
    digest = hashlib.sha256(b"x").hexdigest()
    prov = {k: {"url": "https://example.org/a", "locator": "Table 3.A", "snapshot": "nirf.txt"} for k in PROV_KEYS}
    return {
        "id": "test-college", "name": "Test", "shortName": "T", "stream": "Engineering", "type": "Public",
        "location": {"city": "A", "state": "B", "tier": "Tier 2", "region": "South"},
        "nirfRank": 9, "accreditation": "NBA", "flagshipPrograms": ["B.Tech CSE"],
        "cutoffs": {"primaryExam": "JEE Main", "category": "General", "minPercentileOrRank": "AIR 1", "safeCutoffScore": 99.1},
        "fees": {"tuitionAnnual": 125000, "mandatoryInstituteFeesAnnual": 38000, "hostelAndMessAnnual": 72000,
                 "estimatedLivingAnnual": 30000, "totalFourYearCostINR": 1060000},
        "placement": {"headlineCTC": 52.8, "medianBaseSalary": 15.5, "batchSize": 1100, "eligibleStudents": 1020,
                      "actuallyPlaced": 926, "higherStudiesOrFounders": 80, "disclosedPlacementRate": 90.78,
                      "placementAuditNote": "n"},
        "sources": {"nirfDisclosureUrl": "https://example.org/nirf", "feeCircularDate": "July 2024",
                    "verificationStatus": "Audited & Verified", "nirfYear": 2025, "retrievedAt": "2026-11-06",
                    "headlineCtcUrl": "https://example.org/h", "feeCircularUrl": "https://example.org/f",
                    "cutoffUrl": "https://example.org/c", "snapshots": {"nirf.txt": digest}, "provenance": prov},
        "commercialRelationship": "None (100% Student-Funded & Independent)",
    }


def check(d):
    return vd.run_integrity_check(College.model_validate(d))


def test_good_record_passes(good):
    ok, errs = check(good)
    assert ok, errs


@pytest.mark.parametrize("mutate,code", [
    (lambda d: d["placement"].update(actuallyPlaced=2000), "G1"),
    (lambda d: d["placement"].update(eligibleStudents=1200), "G1"),
    (lambda d: d["placement"].update(disclosedPlacementRate=80.0), "G2"),
    (lambda d: d["placement"].update(headlineCTC=10.0), "G3"),
    (lambda d: d["fees"].update(totalFourYearCostINR=1000000), "G4"),
    (lambda d: d["sources"].update(nirfDisclosureUrl="nirf"), "G5"),
    (lambda d: d.update(commercialRelationship="Affiliate"), "G6"),
    (lambda d: d["sources"]["provenance"].pop("nirfRank"), "provenance"),
    (lambda d: d["sources"]["snapshots"].update({"nirf.txt": "0" * 64}), "sha256"),
    (lambda d: d["sources"].update(verificationStatus="Pending"), "verificationStatus"),
])
def test_each_gate_fails(good, mutate, code):
    d = copy.deepcopy(good)
    mutate(d)
    ok, errs = check(d)
    assert not ok
    assert any(code in e for e in errs), errs


def test_iim_two_year_multiplier(good):
    d = copy.deepcopy(good)
    d["id"], d["stream"] = "iim-a", "Management"
    d["fees"]["totalFourYearCostINR"] = 265000 * 2
    ok, errs = check(d)
    assert not any("G4" in e for e in errs)
