"""Assemble data/colleges/<id>.json from saved official sources + researched findings.

Inputs per college (all under data/sources/<id>/):
  nirf-2025-dcs.pdf (NIRF placement table), josaa-2025-round6.html (JoSAA colleges), findings.json
Nothing is estimated: any missing required value aborts that record (decision D-05).
Usage: python scripts/assemble_records.py [id ...]
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "sources"
OUT = ROOT / "data" / "colleges"
RANKING = SRC / "nirf-2025-engineering-ranking.html"
NIRF_YEAR = 2025
NIRF_CODES = {
    "iit-bombay": "IR-E-U-0306", "iit-delhi": "IR-E-I-1074", "iit-madras": "IR-E-U-0456",
    "nit-trichy": "IR-E-U-0467", "nit-surathkal": "IR-E-U-0237", "nit-warangal": "IR-E-U-0025",
    "dtu-delhi": "IR-E-U-0098", "iiit-hyderabad": "IR-E-U-0014", "bits-pilani": "IR-E-U-0391",
    "vit-vellore": "IR-E-U-0490",
    "iit-kanpur": "IR-E-I-1075", "iit-kharagpur": "IR-E-U-0573", "iit-roorkee": "IR-E-U-0560",
    "iit-hyderabad": "IR-E-U-0013", "iit-bhu": "IR-E-U-0701", "iit-guwahati": "IR-E-U-0053",
    "nit-rourkela": "IR-E-U-0357", "nit-calicut": "IR-E-U-0263", "mnit-jaipur": "IR-E-U-0410",
    "vnit-nagpur": "IR-E-U-0334", "iiit-delhi": "IR-E-U-0105", "nsut-delhi": "IR-E-C-6379",
    "thapar-patiala": "IR-E-I-1480", "srm-kattankulathur": "IR-E-U-0473", "manipal-mit": "IR-E-C-7252",
    "kiit-bhubaneswar": "IR-E-U-0356", "amrita-coimbatore": "IR-E-U-0436", "jadavpur": "IR-E-U-0575",
}
NAMES = {
    "iit-bombay": ("Indian Institute of Technology Bombay", "IIT Bombay", "West"),
    "iit-delhi": ("Indian Institute of Technology Delhi", "IIT Delhi", "North"),
    "iit-madras": ("Indian Institute of Technology Madras", "IIT Madras", "South"),
    "nit-trichy": ("National Institute of Technology Tiruchirappalli", "NIT Trichy", "South"),
    "nit-surathkal": ("National Institute of Technology Karnataka, Surathkal", "NIT Surathkal", "South"),
    "nit-warangal": ("National Institute of Technology Warangal", "NIT Warangal", "South"),
    "dtu-delhi": ("Delhi Technological University", "DTU Delhi", "North"),
    "iiit-hyderabad": ("International Institute of Information Technology Hyderabad", "IIIT Hyderabad", "South"),
    "bits-pilani": ("Birla Institute of Technology & Science, Pilani", "BITS Pilani", "North"),
    "vit-vellore": ("Vellore Institute of Technology", "VIT Vellore", "South"),
    "iit-kanpur": ("Indian Institute of Technology Kanpur", "IIT Kanpur", "North"),
    "iit-kharagpur": ("Indian Institute of Technology Kharagpur", "IIT Kharagpur", "East"),
    "iit-roorkee": ("Indian Institute of Technology Roorkee", "IIT Roorkee", "North"),
    "iit-hyderabad": ("Indian Institute of Technology Hyderabad", "IIT Hyderabad", "South"),
    "iit-bhu": ("Indian Institute of Technology (BHU) Varanasi", "IIT BHU", "North"),
    "iit-guwahati": ("Indian Institute of Technology Guwahati", "IIT Guwahati", "East"),
    "nit-rourkela": ("National Institute of Technology Rourkela", "NIT Rourkela", "East"),
    "nit-calicut": ("National Institute of Technology Calicut", "NIT Calicut", "South"),
    "mnit-jaipur": ("Malaviya National Institute of Technology Jaipur", "MNIT Jaipur", "North"),
    "vnit-nagpur": ("Visvesvaraya National Institute of Technology Nagpur", "VNIT Nagpur", "West"),
    "iiit-delhi": ("Indraprastha Institute of Information Technology Delhi", "IIIT Delhi", "North"),
    "nsut-delhi": ("Netaji Subhas University of Technology", "NSUT Delhi", "North"),
    "thapar-patiala": ("Thapar Institute of Engineering and Technology", "Thapar", "North"),
    "srm-kattankulathur": ("SRM Institute of Science and Technology, Kattankulathur", "SRM KTR", "South"),
    "manipal-mit": ("Manipal Institute of Technology", "MIT Manipal", "South"),
    "kiit-bhubaneswar": ("Kalinga Institute of Industrial Technology", "KIIT", "East"),
    "amrita-coimbatore": ("Amrita Vishwa Vidyapeetham, Coimbatore", "Amrita Coimbatore", "South"),
    "jadavpur": ("Jadavpur University", "Jadavpur University", "East"),
}
LIVING = {"X": (62500, "Tier 1"), "Y": (37500, "Tier 2"), "Z": (25000, "Tier 3")}  # D-19
JOSAA_URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"


def split_snaps(v):
    v = re.sub(r"\s*\([^)]*\)", "", v or "")
    return [x.strip() for x in re.split(r"[;,]\s*(?=[\w\-.]+\.(?:pdf|html|txt|png|jpg)\b)", v) if x.strip()]


def first_snap(v):
    parts = split_snaps(v)
    return parts[0] if parts else v


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def nirf_rank(code: str) -> int:
    h = RANKING.read_text(errors="ignore")
    ids = [(m.start(), m.group(1)) for m in re.finditer(r"(IR-E-[A-Z]-\d+)</td>", h)]
    for i, (pos, c) in enumerate(ids):
        if c == code:
            end = ids[i + 1][0] if i + 1 < len(ids) else len(h)
            ranks = re.findall(r"<td>(\d+)</td>\s*</tr>", h[pos:end])
            return int(ranks[-1])
    raise ValueError(code)


def nirf_placement(cid: str) -> dict:
    t = subprocess.run(["pdftotext", "-layout", str(SRC / cid / "nirf-2025-dcs.pdf"), "-"], capture_output=True, text=True).stdout
    i = t.find("UG [4 Years Program(s)]: Placement")
    j = t.find("PG [", i + 10)
    best = None
    for line in t[i:j if j > 0 else i + 6000].splitlines():
        m = re.match(r"\s*(\d{4}-\d{2})\s+(\d+)\s+(\d+)\s+(\d{4}-\d{2})\s+(\d+)\s+(2023-24)\s+(\d+)\s+(\d+)\s+(\d{5,8})\D.*?(\d+)\s*$", line)
        if m and best is None:  # first match = UG 4-year block
            best = dict(batch=int(m[7]), placed=int(m[8]), median=int(m[9]), higher=int(m[10]))
    if not best:
        raise ValueError("NIRF row not found")
    return best


def josaa_cutoff(cid: str):
    p = SRC / cid / "josaa-2025-round6.html"
    if not p.exists():
        return None
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", p.read_text(errors="ignore"), re.S)
    out = {}
    for r in rows:
        c = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        if (len(c) >= 7 and c[1] == "Computer Science and Engineering (4 Years, Bachelor of Technology)"
                and c[3] == "OPEN" and c[4] == "Gender-Neutral"):
            out[c[2]] = (int(c[5]), int(c[6]))
    return out


def main(ids):
    OUT.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        d = SRC / cid
        problems = []
        try:
            f = json.loads((d / "findings.json").read_text())
        except Exception as e:  # noqa: BLE001
            print(f"SKIP {cid}: no findings.json ({e})")
            continue
        if f.get("status") == "excluded":
            print(f"EXCLUDED {cid}: {f.get('reason')}")
            continue
        np_ = nirf_placement(cid)
        eligible = np_["batch"] - np_["higher"]
        rate = round(np_["placed"] / eligible * 100, 2)
        fees, hl, acc, hra = f["fees"], f["headlineCTC"], f["accreditation"], f["hra"]
        for k in ["tuitionAnnual", "mandatoryInstituteFeesAnnual", "hostelAndMessAnnual"]:
            if fees.get(k) is None:
                problems.append(f"fees.{k}")
        if hl.get("valueLPA") is None:
            problems.append("headlineCTC")
        if hra.get("class") not in LIVING:
            problems.append("hra.class")
        # cutoff
        jo = josaa_cutoff(cid)
        if jo:
            if cid.startswith("iit"):
                op, cl = jo["AI"]
                text = f"JoSAA {2025} Round 6, CSE (4-yr B.Tech), OPEN, Gender-Neutral, All-India quota: opening AIR {op}, closing AIR {cl} (JEE Advanced rank)"
                cut = dict(primaryExam="JEE Advanced", category="General (OPEN)", minPercentileOrRank=text)
            else:
                text = (f"JoSAA 2025 Round 6, CSE (4-yr B.Tech), OPEN, Gender-Neutral: Other State closing AIR {jo['OS'][1]} "
                        f"(opening {jo['OS'][0]}); Home State closing AIR {jo['HS'][1]} (opening {jo['HS'][0]}) (JEE Main rank)")
                cut = dict(primaryExam="JEE Main", category="General (OPEN)", minPercentileOrRank=text)
            cutoff_url, cutoff_snap = JOSAA_URL, "josaa-2025-round6.html"
            cut_loc = "JoSAA Opening & Closing Rank Archive 2025, Round 6, filtered to CSE 4-yr B.Tech, OPEN, Gender-Neutral"
        else:
            co = f.get("cutoff") or {}
            if not co.get("closingRanks"):
                problems.append("cutoff")
            cut = dict(primaryExam=co.get("exam"), category=co.get("category") or "General",
                       minPercentileOrRank=f"{co.get('exam')} {co.get('year')} {co.get('round')}: {co.get('closingRanks')} ({co.get('region_or_quota')})")
            cutoff_url, cutoff_snap, cut_loc = co.get("url"), co.get("snapshot"), co.get("locator")
        if problems:
            print(f"SKIP {cid}: missing {problems} (D-05: substitute or ask user)")
            continue
        liv, tier = LIVING[hra["class"]]
        annual = fees["tuitionAnnual"] + fees["mandatoryInstituteFeesAnnual"] + fees["hostelAndMessAnnual"] + liv
        # snapshots
        shutil.copy(RANKING, d / RANKING.name)
        snaps = {}
        for obj in (hl, fees, acc, hra):
            obj["snapshot"] = first_snap(obj.get("snapshot"))
        cutoff_snap = first_snap(cutoff_snap)
        cited = {"nirf-2025-dcs.pdf", RANKING.name, hl.get("snapshot"), fees.get("snapshot"), acc.get("snapshot"),
                 hra.get("snapshot"), cutoff_snap}
        for name in filter(None, cited):
            if (d / name).exists():
                snaps[name] = sha(d / name)
            else:
                problems.append(f"snapshot {name} missing")
        if problems:
            print(f"SKIP {cid}: {problems}")
            continue
        nirf_url = f"https://www.nirfindia.org/nirfpdfcdn/{NIRF_YEAR}/pdf/Engineering/{NIRF_CODES[cid]}.pdf"
        rank_url = f"https://www.nirfindia.org/Rankings/{NIRF_YEAR}/EngineeringRanking.html"
        nirf_loc = "Placement & Higher Studies, UG [4 Years Program(s)], row graduating 2023-24"
        P = lambda url, loc, snap: dict(url=url, locator=loc, snapshot=snap)  # noqa: E731
        prov = {
            "placement.batchSize": P(nirf_url, nirf_loc + ": students graduating in minimum stipulated time", "nirf-2025-dcs.pdf"),
            "placement.eligibleStudents": P(nirf_url, nirf_loc + ": graduating minus students selected for higher studies (D-09)", "nirf-2025-dcs.pdf"),
            "placement.actuallyPlaced": P(nirf_url, nirf_loc + ": no. of students placed", "nirf-2025-dcs.pdf"),
            "placement.medianBaseSalary": P(nirf_url, nirf_loc + ": median salary of placed graduates per annum", "nirf-2025-dcs.pdf"),
            "placement.headlineCTC": P(hl["url"], hl["locator"], hl["snapshot"]),
            "fees.tuitionAnnual": P(fees["feeCircularUrl"], fees["locator"], fees["snapshot"]),
            "fees.hostelAndMessAnnual": P(fees["feeCircularUrl"], fees["locator"], fees["snapshot"]),
            "fees.mandatoryInstituteFeesAnnual": P(fees["feeCircularUrl"], fees["locator"], fees["snapshot"]),
            "fees.estimatedLivingAnnual": P(hra["url"], f"HRA class {hra['class']} for {hra['city']}; band midpoint per D-19", hra["snapshot"]),
            "cutoffs.minPercentileOrRank": P(cutoff_url, cut_loc, cutoff_snap),
            "nirfRank": P(rank_url, "NIRF 2025 Engineering ranking table", RANKING.name),
            "accreditation": P(acc["url"], acc["locator"], acc["snapshot"]),
        }
        name, short, region = NAMES[cid]
        fl = lambda x: f"{x:,}"  # noqa: E731
        rec = {
            "id": cid, "name": name, "shortName": short, "stream": "Engineering", "type": f["type"],
            "location": {"city": f["location"]["city"], "state": f["location"]["state"], "tier": tier, "region": region},
            "nirfRank": nirf_rank(NIRF_CODES[cid]),
            "accreditation": acc["text"] or "Not stated in official sources reviewed",
            "flagshipPrograms": f["flagshipPrograms"],
            "cutoffs": {**cut, "safeCutoffScore": None},
            "fees": {"tuitionAnnual": fees["tuitionAnnual"], "mandatoryInstituteFeesAnnual": fees["mandatoryInstituteFeesAnnual"],
                     "hostelAndMessAnnual": fees["hostelAndMessAnnual"], "estimatedLivingAnnual": liv,
                     "totalFourYearCostINR": annual * 4},
            "placement": {
                "headlineCTC": hl["valueLPA"], "medianBaseSalary": round(np_["median"] / 100000, 2),
                "batchSize": np_["batch"], "eligibleStudents": eligible, "actuallyPlaced": np_["placed"],
                "higherStudiesOrFounders": np_["higher"], "disclosedPlacementRate": rate,
                "placementAuditNote": (f"NIRF {NIRF_YEAR} UG 4-year batch graduating 2023-24: {fl(np_['batch'])} graduated, "
                                       f"{fl(np_['higher'])} to higher studies, {fl(np_['placed'])} placed of {fl(eligible)} eligible. "
                                       f"Median Rs {fl(np_['median'])}. Headline CTC: {hl['note']}")},
            "sources": {
                "nirfDisclosureUrl": nirf_url, "feeCircularDate": fees["feeCircularDate"],
                "verificationStatus": "Pending second-pass verification", "nirfYear": NIRF_YEAR, "retrievedAt": f["retrievedAt"],
                "headlineCtcUrl": hl["url"], "feeCircularUrl": fees["feeCircularUrl"], "cutoffUrl": cutoff_url,
                "snapshots": snaps, "provenance": prov},
            "commercialRelationship": "None (100% Student-Funded & Independent)",
        }
        (OUT / f"{cid}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        print(f"WROTE {cid}")


if __name__ == "__main__":
    main(sys.argv[1:] or list(NAMES))
