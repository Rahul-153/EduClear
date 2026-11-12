from backend.app.data import get_college
from backend.app.engines.assumptions import Assumptions
from backend.app.services import agent as ag
from backend.app.services import claims

CID = "iit-delhi"


def _check(text, llm=None, ids=None):
    return claims.check(text, ids if ids is not None else ag._find_colleges(text), llm)


class Fake:
    name = "fake"

    def __init__(self, out):
        self.out = out

    def json(self, system, user, schema):
        return self.out


def test_rate_claim_uses_record_numbers():
    p = get_college(CID).placement
    r = _check("IIT Delhi advertises 100% placement")
    assert r["college_id"] == CID and f"{p.actuallyPlaced:,} of {p.eligibleStudents:,}" in r["lines"][0]
    assert r["verdicts"][0]["status"] == ("consistent" if p.actuallyPlaced == p.eligibleStudents else "above_record")


def test_package_claim_compares_with_headline_and_median():
    p = get_college("bits-pilani").placement  # has a headline figure
    r = _check("BITS Pilani brochure: highest package 450 LPA")
    assert r["verdicts"][0]["status"] == "above_record" and "450 LPA" in r["lines"][0] and f"headline {p.headlineCTC:g} LPA" in r["lines"][0]
    avg = _check("BITS Pilani average package of 900 LPA")
    assert f"median {p.medianBaseSalary:g} LPA" in avg["lines"][0] and avg["verdicts"][0]["status"] == "above_record"
    assert _check("BITS Pilani highest package 10 LPA")["verdicts"][0]["status"] == "consistent"


def test_missing_record_figure_is_not_estimated():
    assert get_college(CID).placement.headlineCTC is None  # IIT Delhi withholds it
    r = _check("IIT Delhi brochure: highest package 45 LPA")
    assert "not in our data" in r["lines"][0] and r["verdicts"] == []


def test_crore_is_converted_to_lpa():
    assert claims.extract("highest package 1.2 crore")["claimed_package_lpa"] == 120


def test_unknown_or_ambiguous_college_asks():
    r = _check("100% placement guaranteed", ids=[])
    assert r["needs_college"] and "Which college" in r["lines"][0]
    r2 = claims.check("100% placement", ["iit-hyderabad", "iiit-hyderabad"])
    assert r2["needs_college"] and "Which one" in r2["lines"][0]


def test_model_invented_number_is_dropped_but_literal_one_kept():
    txt = "IIT Delhi has amazing outcomes, ninety seven percent placed"
    assert _check(txt, Fake({"claimed_rate_pct": 97, "claimed_package_lpa": None}))["claims"]["claimed_rate_pct"] is None  # 97 not written as digits
    txt2 = "IIT Delhi: nearly everyone placed, 97 of every 100"
    assert _check(txt2, Fake({"claimed_rate_pct": 97, "claimed_package_lpa": 60}))["claims"]["claimed_package_lpa"] is None
    assert _check(txt2, Fake({"claimed_rate_pct": 97}))["claims"]["claimed_rate_pct"] == 97


def test_no_model_and_no_claim():
    assert "no placement-rate or package claim" in _check("IIT Delhi is a great campus")["lines"][0]


def test_copilot_tool_and_label():
    out = ag.handle("IIT Delhi brochure says 100% placement", {}, "en", Assumptions(), "o1", None)
    assert out["tool"] == "check_claim" and "of" in out["reply"] and out["data"]["label"] in ("Supplied, not audited", "Fully audited")
