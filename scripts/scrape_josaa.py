"""Fetch JoSAA opening/closing-rank archive (official ASP.NET form) for given institutes.

Usage: python scripts/scrape_josaa.py --year 2025 --round 6 --out data/sources
Saves the raw result HTML per institute as data/sources/<id>/josaa-<year>-round<round>.html
and prints CSE rows (OPEN seat type). Read-only HTTP; no data is sent other than form selections.
"""
import argparse
import re
import sys
from pathlib import Path

import requests

URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
P = "ctl00$ContentPlaceHolder1$"
TARGETS = {  # id -> (instype code, substring of the official institute name)
    "iit-bombay": ("IIT", "Indian Institute of Technology Bombay"),
    "iit-delhi": ("IIT", "Indian Institute of Technology Delhi"),
    "iit-madras": ("IIT", "Indian Institute of Technology Madras"),
    "nit-trichy": ("NIT", "Tiruchirappalli"),
    "nit-surathkal": ("NIT", "Karnataka"),
    "nit-warangal": ("NIT", "Warangal"),
    "iit-kanpur": ("IIT", "Indian Institute of Technology Kanpur"),
    "iit-kharagpur": ("IIT", "Indian Institute of Technology Kharagpur"),
    "iit-roorkee": ("IIT", "Indian Institute of Technology Roorkee"),
    "iit-hyderabad": ("IIT", "Indian Institute of Technology Hyderabad"),
    "iit-bhu": ("IIT", "BHU"),
    "iit-guwahati": ("IIT", "Indian Institute of Technology Guwahati"),
    "nit-rourkela": ("NIT", "Rourkela"),
    "nit-calicut": ("NIT", "Calicut"),
    "mnit-jaipur": ("NIT", "Malaviya National Institute of Technology Jaipur"),
    "vnit-nagpur": ("NIT", "Visvesvaraya"),
}


def hidden(html):
    return {k: (re.search(r'id="%s" value="([^"]*)"' % k, html) or [None, ""])[1]
            for k in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]}


def options(html, name):
    m = re.search(r'<select[^>]*name="%s%s".*?</select>' % (re.escape(P), name), html, re.S)
    if not m:
        return []
    return [(v, re.sub(r"\s+", " ", t).strip()) for v, t in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', m.group(0), re.S)]


def post(s, html, target, values):
    data = {**hidden(html), "__EVENTTARGET": target, "__EVENTARGUMENT": "", **values}
    r = s.post(URL, data=data, headers=UA, timeout=60)
    r.raise_for_status()
    return r.text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default="2025")
    ap.add_argument("--round", default="6")
    ap.add_argument("--out", default="data/sources")
    ap.add_argument("--only", nargs="*", default=[])
    a = ap.parse_args()
    only = set(a.only)
    s = requests.Session()
    html = s.get(URL, headers=UA, timeout=60).text
    vals = {P + "ddlYear": a.year}
    html = post(s, html, P + "ddlYear", vals)
    vals[P + "ddlroundno"] = a.round
    html = post(s, html, P + "ddlroundno", vals)
    inst_types = options(html, "ddlInstype")
    print("types:", inst_types, file=sys.stderr)
    for iid, (want_type, needle) in TARGETS.items():
        if only and iid not in only:
            continue
        tv = next(v for v, t in inst_types if v == want_type)
        v2 = {**vals, P + "ddlInstype": tv}
        h2 = post(s, html, P + "ddlInstype", v2)
        inst = next((v, t) for v, t in options(h2, "ddlInstitute") if needle in t)
        v2[P + "ddlInstitute"] = inst[0]
        h3 = post(s, h2, P + "ddlInstitute", v2)
        branches = options(h3, "ddlBranch")
        v2[P + "ddlBranch"] = "ALL"
        h4 = post(s, h3, P + "ddlBranch", v2)
        v2[P + "ddlSeatType"] = "ALL"
        v2[P + "btnSubmit"] = "Submit"
        h5 = post(s, h4, P + "btnSubmit", v2)
        out = Path(a.out) / iid
        out.mkdir(parents=True, exist_ok=True)
        (out / f"josaa-{a.year}-round{a.round}.html").write_text(h5)
        print(iid, inst[1], "branches:", len(branches), "bytes:", len(h5))


if __name__ == "__main__":
    main()
