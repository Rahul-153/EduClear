"""Stage the deterministic inputs for one IIT before the document hunt (IIT round, 2026-11-09).

Writes data/sources/<id>/: nirf-2025-dcs.pdf (scripted fetch with the project's plain User-Agent), prestage.json with
the NIRF UG 4-year placement rows, the NIRF rank, and every JoSAA 2025 round-6 row for the institute (all programmes,
quotas, seat types, genders; read from data/evidence/josaa.sqlite). Fees, hostel/mess, headline package and
accreditation come from the institute's own documents and are NOT staged here.
Usage: python scripts/iit_prestage.py iit-indore [...]
"""
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
IITS = {  # id: (NIRF 2025 engineering code or None, official JoSAA institute name)
    "iit-bombay": ("IR-E-U-0306", "Indian Institute of Technology Bombay"),
    "iit-delhi": ("IR-E-I-1074", "Indian Institute of Technology Delhi"),
    "iit-madras": ("IR-E-U-0456", "Indian Institute of Technology Madras"),
    "iit-kanpur": ("IR-E-I-1075", "Indian Institute of Technology Kanpur"),
    "iit-kharagpur": ("IR-E-U-0573", "Indian Institute of Technology Kharagpur"),
    "iit-roorkee": ("IR-E-U-0560", "Indian Institute of Technology Roorkee"),
    "iit-indore": ("IR-E-U-0273", "Indian Institute of Technology Indore"),
    "iit-ism-dhanbad": ("IR-E-U-0205", "Indian Institute of Technology (ISM) Dhanbad"),
    "iit-patna": ("IR-E-U-0064", "Indian Institute of Technology Patna"),
    "iit-gandhinagar": ("IR-E-U-0139", "Indian Institute of Technology Gandhinagar"),
    "iit-mandi": ("IR-E-U-0184", "Indian Institute of Technology Mandi"),
    "iit-jodhpur": ("IR-E-U-0395", "Indian Institute of Technology Jodhpur"),
    "iit-ropar": ("IR-E-U-0378", "Indian Institute of Technology Ropar"),
    "iit-bhubaneswar": ("IR-E-U-0355", "Indian Institute of Technology Bhubaneswar"),
    "iit-jammu": ("IR-E-U-0906", "Indian Institute of Technology Jammu"),
    "iit-tirupati": ("IR-E-U-0844", "Indian Institute of Technology Tirupati"),
    "iit-palakkad": ("IR-E-U-0878", "Indian Institute of Technology Palakkad"),
    "iit-bhilai": ("IR-E-U-0946", "Indian Institute of Technology Bhilai"),
    "iit-dharwad": ("IR-E-U-0899", "Indian Institute of Technology Dharwad"),
    "iit-goa": (None, "Indian Institute of Technology Goa"),
}


def main(ids):
    db = sqlite3.connect(ROOT / "data" / "evidence" / "josaa.sqlite")
    rank_html = (ROOT / "data" / "sources" / "nirf-2025-engineering-ranking.html").read_text(errors="ignore")
    for cid in ids:
        code, jname = IITS[cid]
        d = ROOT / "data" / "sources" / cid
        d.mkdir(parents=True, exist_ok=True)
        out = {"id": cid, "nirfCode": code, "josaaName": jname, "nirfRank": None, "nirfPlacementUG4": [], "notes": []}
        if code:
            pdf = d / "nirf-2025-dcs.pdf"
            if not pdf.exists():
                r = requests.get(f"https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Engineering/{code}.pdf", headers=UA, timeout=90)
                if r.ok:
                    pdf.write_bytes(r.content)
                else:
                    out["notes"].append(f"NIRF DCS fetch failed: HTTP {r.status_code}")
            if pdf.exists():
                t = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
                i = t.find("UG [4 Years Program(s)]: Placement")
                j = t.find("PG [", i + 10)
                for line in t[i:j if j > 0 else i + 6000].splitlines():
                    m = re.match(r"\s*(\d{4}-\d{2})\s+(\d+)\s+(\d+)\s+(\d{4}-\d{2})\s+(\d+)\s+(\d{4}-\d{2})\s+(\d+)\s+(\d+)\s+(\d{5,8})\D.*?(\d+)\s*$", line)
                    if m:
                        out["nirfPlacementUG4"].append(dict(intakeYear=m[1], intake=int(m[2]), admitted=int(m[3]), graduatingYear=m[6],
                                                            graduated=int(m[7]), placed=int(m[8]), medianSalary=int(m[9]), higherStudies=int(m[10])))
                if not out["nirfPlacementUG4"]:
                    out["notes"].append("NIRF UG 4-year placement rows not parsed; read the PDF by hand")
            m = re.search(re.escape(code) + r"</td><td>.*?<td>(\d+)</td>\s*</tr>", rank_html, re.S)
            parts = re.split(r"(?=IR-E-[A-Z]-\d+</td>)", rank_html)
            for p in parts[1:]:
                if p.startswith(code):
                    out["nirfRank"] = int(re.findall(r"<td>(\d+)</td>", p)[-1])
                    break
        else:
            out["notes"].append("No NIRF 2025 Engineering code (not in the top-100 list); NIRF rank/placement need other NIRF pages")
        rows = db.execute("""SELECT program, quota, seat_type, gender, opening_raw, closing_raw, is_prep FROM cutoffs
                             WHERE year=2025 AND round=6 AND institute=? ORDER BY program, seat_type, gender""", (jname,)).fetchall()
        out["josaa2025Round6"] = [dict(zip(("program", "quota", "seatType", "gender", "opening", "closing", "isPrep"), r)) for r in rows]
        out["josaaYearsAvailable"] = [r[0] for r in db.execute("SELECT DISTINCT year FROM cutoffs WHERE institute=? ORDER BY 1", (jname,))]
        (d / "prestage.json").write_text(json.dumps(out, indent=1))
        print(cid, "rank", out["nirfRank"], "placement rows", len(out["nirfPlacementUG4"]), "josaa rows", len(rows), out["notes"])


if __name__ == "__main__":
    main(sys.argv[1:] or list(IITS))
