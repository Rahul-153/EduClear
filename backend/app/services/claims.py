"""Brochure claim checker (T-15.06). Rules read the claim, Python compares it with the college record, templates write the verdict.
The model (optional) may only fill a claim the rules missed, and only a number that literally appears in the text (D-07)."""
import re
from typing import List, Optional

from ..data import colleges
from ..llm.client import LLM
from . import intake

NUM = r"(\d+(?:\.\d+)?)"
UNIT = r"(lpa|lakhs?|lacs?|लाख|crores?|cr|करोड़)"
PKG_WORDS = r"package|ctc|salary|lpa|highest|average|median|avg|top offer|पैकेज"
SYSTEM = ('Extract claims from a college brochure line. Reply JSON: {"claimed_rate_pct": number|null, "claimed_package_lpa": number|null, '
          '"package_kind": "highest"|"average"|null}. Use only numbers written in the text.')
SCHEMA = {"type": "object", "properties": {"claimed_rate_pct": {"type": ["number", "null"]}, "claimed_package_lpa": {"type": ["number", "null"]},
                                           "package_kind": {"type": ["string", "null"], "enum": ["highest", "average", None]}}}
TOL_LPA, TOL_PCT = 0.5, 0.5  # rounding slack only


def _kind(window: str) -> Optional[str]:
    if re.search(r"highest|top|maximum|max\b|best", window):
        return "highest"
    if re.search(r"average|avg|median|mean", window):
        return "average"
    return None


def extract(text: str) -> dict:
    t = text.translate(intake.DEV).lower()
    out = {"claimed_rate_pct": None, "claimed_package_lpa": None, "package_kind": None, "source": "rules"}
    for m in re.finditer(rf"{NUM}\s*%", t):
        if re.search(r"placement|placed|प्लेसमेंट", t[max(0, m.start() - 40): m.end() + 40]):
            out["claimed_rate_pct"] = float(m.group(1))
            break
    for m in re.finditer(rf"{NUM}\s*{UNIT}", t):
        win = t[max(0, m.start() - 40): m.end() + 40]
        if m.group(2) in ("lpa",) or re.search(PKG_WORDS, win):
            n = float(m.group(1)) * (100 if m.group(2).startswith(("cr", "कर")) else 1)
            out["claimed_package_lpa"], out["package_kind"] = n, _kind(win)
            break
    return out


def _in_text(value, text: str) -> bool:
    nums = {float(x) for x in re.findall(r"\d+(?:\.\d+)?", text.translate(intake.DEV))}
    return isinstance(value, (int, float)) and not isinstance(value, bool) and (float(value) in nums or float(value) / 100 in nums)


def _fill_with_model(text: str, claim: dict, llm: Optional[LLM]) -> dict:
    if not llm or (claim["claimed_rate_pct"] is not None or claim["claimed_package_lpa"] is not None):
        return claim
    got = llm.json(SYSTEM, text, SCHEMA) or {}
    rate, pkg = got.get("claimed_rate_pct"), got.get("claimed_package_lpa")
    claim = dict(claim, source="llm")
    if _in_text(rate, text) and 0 < rate <= 100:
        claim["claimed_rate_pct"] = float(rate)
    if _in_text(pkg, text) and pkg > 0:
        claim["claimed_package_lpa"] = float(pkg)
        claim["package_kind"] = got.get("package_kind") if got.get("package_kind") in ("highest", "average") else None
    return claim


def _f(x: float) -> str:
    return f"{x:g}"


def check(text: str, college_ids: List[str], llm: Optional[LLM] = None, lang: str = "en") -> dict:
    hi = lang == "hi"
    cs = colleges()
    if len(college_ids) != 1:
        n = [cs[i].shortName for i in college_ids[:3]]
        msg = (f"कौन सा: {' या '.join(n)}?" if hi else f"Which one: {' or '.join(n)}?") if n else \
              ("कृपया कॉलेज का नाम लिखें।" if hi else "Which college is this about? Please include its name.")
        return {"college_id": None, "needs_college": True, "claims": {}, "lines": [msg]}
    c = cs[college_ids[0]]
    claim = _fill_with_model(text, extract(text), llm)
    p = c.placement
    lines, verdicts = [], []
    audited = c.sources.verificationStatus == "Audited & Verified"
    if claim["claimed_package_lpa"] is not None:
        v, kind = claim["claimed_package_lpa"], claim["package_kind"]
        rec = {"highest": [("headline", p.headlineCTC)], "average": [("median", p.medianBaseSalary)]}.get(kind) or \
              [("median", p.medianBaseSalary), ("headline", p.headlineCTC)]
        have = [(k, x) for k, x in rec if x]
        if not have:
            lines.append(f"ब्रोशर: {_f(v)} LPA। रिकॉर्ड: हमारे डेटा में नहीं।" if hi else f"Brochure: {_f(v)} LPA. Record: not in our data.")
        else:
            rec_txt = ", ".join(f"{k} {_f(x)} LPA" for k, x in have)
            lines.append((f"ब्रोशर: {_f(v)} LPA। रिकॉर्ड: {rec_txt}।") if hi else f"Brochure: {_f(v)} LPA. Record: {rec_txt}.")
            # a claim is consistent if it does not exceed the matching record figure (one figure when the kind is stated)
            ok = any(v <= x + TOL_LPA for _, x in have)
            verdicts.append({"claim": "package", "claimed": v, "status": "consistent" if ok else "above_record"})
    if claim["claimed_rate_pct"] is not None:
        v = claim["claimed_rate_pct"]
        if not p.eligibleStudents:
            lines.append(f"ब्रोशर: {_f(v)}% प्लेस्ड। रिकॉर्ड: हमारे डेटा में नहीं।" if hi else f"Brochure: {_f(v)}% placed. Record: not in our data.")
        else:
            r = p.actuallyPlaced / p.eligibleStudents * 100
            lines.append((f"ब्रोशर: {_f(v)}% प्लेस्ड। रिकॉर्ड: {p.eligibleStudents:,} में से {p.actuallyPlaced:,} ({r:.0f}%)।") if hi else
                         f"Brochure: {_f(v)}% placed. Record: {p.actuallyPlaced:,} of {p.eligibleStudents:,} eligible ({r:.0f}%).")
            verdicts.append({"claim": "placement_rate", "claimed": v, "status": "consistent" if v <= r + TOL_PCT else "above_record"})
    if not lines:
        lines.append("इस पाठ में प्लेसमेंट दर या पैकेज का दावा नहीं मिला।" if hi else "I found no placement-rate or package claim in that text.")
    return {"college_id": c.id, "college": c.shortName, "needs_college": False, "claims": claim, "verdicts": verdicts, "lines": lines,
            "label": "Fully audited" if audited else "Supplied, not audited", "source_url": c.sources.nirfDisclosureUrl}
