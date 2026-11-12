"""The app runs on the supplied dataset (D-53). These tests pin two things: every number in a record is the number in the
supplied CSV (nothing corrected or filled), and the app never calls this data audited."""
import csv

from backend.app.config import ROOT
from backend.app.data import colleges
from backend.app.engines.assumptions import Assumptions
from backend.app.services.recommend import recommend

SUPPLIED = ROOT / "data" / "supplied"
FILES = ("iits", "nits", "iiits", "gftis", "state_private")


def supplied_rows():
    out = {}
    for f in FILES:
        for r in csv.DictReader((SUPPLIED / f"{f}.csv").open(encoding="utf-8-sig")):
            out[r["id"]] = r
    return out


def test_one_record_per_supplied_engineering_institute():
    assert set(colleges()) == set(supplied_rows())


def test_every_number_matches_the_supplied_csv():
    rows = supplied_rows()
    for cid, c in colleges().items():
        r = rows[cid]
        assert (c.fees.tuitionAnnual, c.fees.mandatoryInstituteFeesAnnual, c.fees.hostelAndMessAnnual, c.fees.estimatedLivingAnnual, c.fees.totalFourYearCostINR) == \
            tuple(int(r[k]) for k in ("tuition_annual", "mandatory_fees_annual", "hostel_mess_annual", "estimated_living_annual", "total_degree_cost_inr")), cid
        p = c.placement
        assert (p.medianBaseSalary, p.eligibleStudents, p.actuallyPlaced, p.higherStudiesOrFounders, p.disclosedPlacementRate) == \
            (float(r["median_base_salary_lpa"]), int(r["eligible_students"]), int(r["actually_placed"]), int(r["higher_studies"]), float(r["disclosed_placement_rate"])), cid
        assert p.headlineCTC == (float(r["headline_ctc_lpa"]) if r["headline_ctc_lpa"] else None), cid
        assert (c.nirfRank, c.name, c.shortName, c.location.city, c.location.state) == (int(r["nirf_rank"]), r["name"], r["short_name"], r["city"], r["state"]), cid


def test_withheld_headline_packages_stay_empty_and_are_not_invented():
    missing = [c.id for c in colleges().values() if c.placement.headlineCTC is None]
    assert len(missing) == 3 and all(i.startswith("iit-") for i in missing)


def test_nothing_is_labelled_audited():
    assert all(c.sources.verificationStatus == "Supplied dataset, not audited" for c in colleges().values())
    r = recommend("Computer Science", 100, "All", Assumptions(), percentile=99.95)
    assert r["matches"] and {m["data_level"] for m in r["matches"]} == {"supplied"}
    assert all(not c.sources.provenance and not c.sources.snapshots for c in colleges().values())


def test_supplied_csvs_are_unchanged_since_they_were_copied_from_the_zip():
    import hashlib
    recorded = {name.strip(): digest for digest, name in (ln.split(None, 1) for ln in (SUPPLIED / "SHA256SUMS").read_text().splitlines())}
    assert len(recorded) == 22
    for name, digest in recorded.items():
        assert hashlib.sha256((SUPPLIED / name.strip()).read_bytes()).hexdigest() == digest, name
