"""Smoke test for a running EduClear instance (local or the public Render URL).

  python scripts/smoke.py http://localhost:8000
In mock payment mode it also walks book -> approve -> capture -> release. In live-sandbox mode it stops after creating the
order, because the buyer must approve in the PayPal pop-up. Exit code is non-zero if any check fails.
"""
import sys
import uuid
from datetime import date, timedelta

import httpx

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
H = {"X-Client-Id": "smoke-" + uuid.uuid4().hex[:16]}
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        fails.append(name)


c = httpx.Client(base_url=base, timeout=40, headers=H)
r = c.get("/api/health"); check("health", r.status_code == 200 and r.json()["colleges"] >= 1, r.text[:80])
n = r.json().get("colleges", 0)
rows = c.get("/api/colleges").json(); check("colleges listed with sources", len(rows) == n and all(x["source_url"].startswith("http") for x in rows))
cid = rows[0]["id"]
check("college sources evidence", "placement.batchSize" in c.get(f"/api/colleges/{cid}/sources").json()["provenance"])
rec = c.post("/api/recommend", json={"percentile": 99.75, "budget_lakhs": 18}).json(); check("recommend deck", rec["supported"] and len(rec["matches"]) > 0)
check("roi", c.post("/api/roi", json={"college_id": cid}).json()["payback"]["payback_months"] > 0)
check("alignment", c.post("/api/alignment", json={"student": dict(brand_prestige=3, branch_passion=3, location_safety=3, budget_strictness=3),
                                                    "parent": dict(brand_prestige=3, branch_passion=3, location_safety=3, budget_strictness=3)}).json()["alignment_score"] == 100)
tl = c.get("/api/admissions/timeline").json(); check("timeline sourced", len(tl["events"]) > 0 and "latest published cycle" in tl["disclaimer"])
check("intake", c.post("/api/intake", json={"text": "99 percentile budget 15 lakh south"}).json()["profile"]["region"] == "South")
chat = c.post("/api/agent/chat", json={"message": "Can I afford NIT Calicut with 8 lakh savings?"}).json(); check("agent affordability", chat["tool"] == "affordability" and "shortfall" in chat["reply"])
d = c.post("/api/deposits", json={"college_id": cid, "amount_inr": 30000, "paid_on": date.today().isoformat(),
                                  "closure_date": (date.today() + timedelta(days=30)).isoformat()}).json()
check("deposit refund calc", d["refund_if_withdrawn_today"]["refund_percent"] in (100, 90)); c.delete(f"/api/deposits/{d['id']}")
cfg = c.get("/api/payments/config").json(); check("payments config sandbox", cfg["environment"] == "sandbox", cfg["mode"])
kit = c.get("/api/kit").json(); check("tech kit", kit["supported"] and kit["total_inr"] > 0)
prog = c.get("/api/programs").json()
free = [x for x in c.get(f"/api/programs/{prog[0]['id']}/slots").json() if x["left"] > 0]
check("a free slot exists", bool(free)); slot = (free or [{"start": ""}])[0]["start"]
b = c.post("/api/bookings", json={"program_id": prog[0]["id"], "slot_start": slot})
check("create sandbox order", b.status_code == 200 and b.json()["paypal_order_id"], b.text[:120])
if b.status_code == 200 and cfg["mode"] == "mock":
    bid = b.json()["id"]
    c.post(f"/api/bookings/{bid}/mock-approve", json={})
    cap = c.post(f"/api/bookings/{bid}/capture").json(); check("capture -> escrow", cap.get("status") == "escrow_funded", str(cap)[:120])
    rel = c.post(f"/api/bookings/{bid}/complete").json(); check("release payout", rel.get("status") == "released", str(rel)[:120])
elif b.status_code == 200:
    print("live-sandbox mode: approve the order in the PayPal pop-up to continue manually")
print(f"\n{'ALL CHECKS PASSED' if not fails else 'FAILED: ' + ', '.join(fails)}  ({base}, payments={cfg['mode']})")
sys.exit(1 if fails else 0)
