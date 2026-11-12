"""Convert the supplied dataset (data/supplied/*.csv, from rehackathonfileseom.zip) into app records in data/colleges/*.json.

The numbers are copied as supplied; nothing is corrected, rounded or filled. What this script adds, and why:
  * identity and location come from the category files (iits, nits, iiits, gftis, state_private, b_schools); region comes from
    colleges_master when the id is there, otherwise from the state, using the same state-to-region convention as that file;
  * the cutoff text the fit engine parses is built from the supplied cutoffs_master rows (CSE, 2025 Round 6, OPEN, Gender-Neutral);
  * `verificationStatus` is "Supplied dataset, not audited", not the zip's "Audited & Verified": the zip's evidence files do not
    stand up (see DATA_ZIP_REVIEW.md), so the app must not claim an audit that did not happen;
  * batchSize = eligible + higher studies, because the supplied files give no separate batch size (D-09 then holds by construction).
Only engineering institutes are written; the 10 B-schools stay in data/supplied for a later MBA step.
Usage: python scripts/build_supplied_records.py
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from college_model import College  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "data" / "supplied", ROOT / "data" / "colleges"
STATUS = "Supplied dataset, not audited"
COMMERCIAL = "None (100% Student-Funded & Independent)"
FILES = ("iits", "nits", "iiits", "gftis", "state_private")  # b_schools: later
STATE_REGION = {  # same convention as colleges_master.csv; used only for ids that file does not list
    "Andhra Pradesh": "South", "Arunachal Pradesh": "East", "Delhi NCR": "North", "Gujarat": "West", "Jammu & Kashmir": "North",
    "Jharkhand": "East", "Karnataka": "South", "Madhya Pradesh": "West", "Manipur": "East", "Mizoram": "East",
    "Tamil Nadu": "South", "Tripura": "East", "Uttarakhand": "North", "West Bengal": "East",
}


def rows(name):
    return list(csv.DictReader((SRC / f"{name}.csv").open(encoding="utf-8-sig")))


def cutoff_text(cat: dict, cuts: dict) -> str:
    """The text engines/fit.parse_cutoff reads, built from supplied numbers. If a cutoff is missing the text says so and fit returns 'not comparable'."""
    exam, text = cat["primary_exam"], cat["min_rank_or_score"]
    quotas = cuts.get(cat["id"], {})
    if exam == "JEE Advanced" and "AI" in quotas:
        return f"JoSAA 2025 Round 6 closing AIR {quotas['AI']} (CSE, OPEN, Gender-Neutral, All India); supplied range {text}"
    if exam.startswith("JEE Main"):
        if "OS" in quotas and "HS" in quotas:
            return f"JoSAA 2025 Round 6 CSE OPEN: Other State closing AIR {quotas['OS']}, Home State closing AIR {quotas['HS']}"
        if "AI" in quotas:  # all-India seats: the same rank applies whatever the student's home state
            return f"JoSAA 2025 Round 6 CSE OPEN: All India closing AIR {quotas['AI']}"
    if exam == "BITSAT":
        m = re.search(r"Score (\d+)", text)
        if m:
            return f"B.E. Computer Science: {m.group(1)} (as supplied: {text})"
    return f"{text} (not comparable with a JEE Main percentile)"


def main() -> None:
    master = {r["id"]: r for r in rows("colleges_master")}
    cuts, names = defaultdict(dict), defaultdict(set)
    for r in rows("cutoffs_master"):
        names[r["collegeId"]].add(r["programName"])
        if r["programCode"] == "CSE" and r["round"] == "Round 6" and r["year"] == "2025" and r["gender"] == "Gender-Neutral" and r["seatCategory"] == "OPEN":
            cuts[r["collegeId"]][r["quota"]] = int(float(r["closingRank"]))
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.json"):
        f.unlink()
    n = 0
    for kind in FILES:
        for r in rows(kind):
            i = r["id"]
            region = master[i]["region"] if i in master else STATE_REGION[r["state"]]
            hs, el = int(r["higher_studies"]), int(r["eligible_students"])
            rec = {
                "id": i, "name": r["name"], "shortName": r["short_name"], "stream": r["stream"], "type": r["type"],
                "location": {"city": r["city"], "state": r["state"], "tier": r["city_tier"], "region": region},
                "nirfRank": int(r["nirf_rank"]), "accreditation": r["accreditation"],
                "flagshipPrograms": sorted(names.get(i, [])),
                "cutoffs": {"primaryExam": r["primary_exam"], "category": "General / OPEN", "minPercentileOrRank": cutoff_text({**r, "id": i}, cuts),
                            "safeCutoffScore": float(r["safe_score"])},
                "fees": {"tuitionAnnual": int(r["tuition_annual"]), "mandatoryInstituteFeesAnnual": int(r["mandatory_fees_annual"]),
                         "hostelAndMessAnnual": int(r["hostel_mess_annual"]), "estimatedLivingAnnual": int(r["estimated_living_annual"]),
                         "totalFourYearCostINR": int(r["total_degree_cost_inr"])},
                "placement": {"headlineCTC": float(r["headline_ctc_lpa"]) if r["headline_ctc_lpa"] else None,
                              "medianBaseSalary": float(r["median_base_salary_lpa"]), "batchSize": el + hs, "eligibleStudents": el,
                              "actuallyPlaced": int(r["actually_placed"]), "higherStudiesOrFounders": hs,
                              "disclosedPlacementRate": float(r["disclosed_placement_rate"]),
                              "placementAuditNote": f"{r['placement_notes']} Supplied dataset, not independently verified; graduating batch as supplied: {r['graduating_batch']} students; the file does not say which branches the figures cover. Headline package status: {r['policy_status']}."},
                "sources": {"nirfDisclosureUrl": r["source_nirf_url"], "feeCircularDate": r["source_fee_circular"], "verificationStatus": STATUS,
                            "retrievedAt": "2026-11-12", "snapshots": {}, "provenance": {}},
                "commercialRelationship": COMMERCIAL,
            }
            College.model_validate(rec)  # shape check only
            (OUT / f"{i}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            n += 1
    print(f"{n} records written to {OUT.relative_to(ROOT)} from {SRC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
