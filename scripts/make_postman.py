"""Generates postman/EduClear.postman_collection.json (documented requests + automated tests) and a local environment."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "postman"
OUT.mkdir(exist_ok=True)


def req(name, method, path, body=None, tests=None, desc="", client_id=False):
    headers = [{"key": "Content-Type", "value": "application/json"}]
    if client_id:
        headers.append({"key": "X-Client-Id", "value": "{{clientId}}"})
    r = {"name": name, "request": {"method": method, "header": headers, "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"], "path": path.strip("/").split("/")},
                                    "description": desc}}
    if body is not None:
        r["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2)}
    if tests:
        r["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}]
    return r


ok = lambda extra=[]: ["pm.test('status 200', () => pm.response.to.have.status(200));"] + extra  # noqa: E731
same = dict(brand_prestige=3, branch_passion=3, location_safety=3, budget_strictness=3)
items = [
    {"name": "Colleges and audit trail", "item": [
        req("Health", "GET", "/api/health", tests=ok(["pm.test('has colleges', () => pm.expect(pm.response.json().colleges).to.be.above(0));"]),
            desc="Service health and number of verified colleges loaded."),
        req("List colleges", "GET", "/api/colleges", tests=ok(["const rows = pm.response.json();", "pm.test('every row links to an official filing', () => pm.expect(rows.every(r => r.source_url.startsWith('http'))).to.be.true);",
                                                               "pm.collectionVariables.set('collegeId', rows[0].id);"]),
            desc="Verified colleges sorted by NIRF rank, each with a link to its official NIRF filing."),
        req("College record", "GET", "/api/colleges/{{collegeId}}", tests=ok(["pm.test('verified', () => pm.expect(pm.response.json().sources.verificationStatus).to.eql('Audited & Verified'));"])),
        req("College source evidence", "GET", "/api/colleges/{{collegeId}}/sources",
            tests=ok(["pm.test('provenance + hashes', () => { const j = pm.response.json(); pm.expect(Object.keys(j.provenance).length).to.be.above(5); pm.expect(Object.keys(j.snapshots_sha256).length).to.be.above(0); });"]),
            desc="Field-by-field evidence: official URL, table/page locator and SHA-256 of the saved snapshot."),
    ]},
    {"name": "Planning engines", "item": [
        req("Recommend (Smart Sentence)", "POST", "/api/recommend", {"percentile": 99.75, "budget_lakhs": 18, "region": "All"},
            tests=ok(["pm.test('deck present', () => pm.expect(pm.response.json().deck).to.have.property('safe_anchor'));"])),
        req("ROI and payback", "POST", "/api/roi", {"college_id": "{{collegeId}}"},
            tests=ok(["const p = pm.response.json().payback; pm.test('disposable payback is slower than gross-pay view', () => pm.expect(p.payback_months).to.be.above(p.payback_months_gross_pay));"])),
        req("Funding plan and EMI", "POST", "/api/finance/plan", {"college_id": "{{collegeId}}", "family_savings": 800000, "annual_contribution": 0},
            tests=ok(["pm.test('eight semester deficits', () => pm.expect(pm.response.json().deficit_per_semester_inr.length).to.eql(8));"])),
        req("Family alignment", "POST", "/api/alignment", {"student": same, "parent": same},
            tests=ok(["pm.test('identical ratings score 100', () => pm.expect(pm.response.json().alignment_score).to.eql(100));"])),
        req("Choice-order check", "POST", "/api/choice-order", {"college_ids": ["mnit-jaipur", "nit-calicut"], "percentile": 99.75},
            tests=ok(["pm.test('inversion flagged', () => pm.expect(pm.response.json().alerts.length).to.eql(1));"])),
    ]},
    {"name": "Admissions and refunds", "item": [
        req("Admissions timeline", "GET", "/api/admissions/timeline", tests=ok(["pm.test('disclaimer says latest published cycle', () => pm.expect(pm.response.json().disclaimer).to.include('latest published cycle'));"])),
        req("UGC refund policy", "GET", "/api/admissions/refund-policy", tests=ok(["pm.test('five percent tiers', () => pm.expect(pm.response.json().tiers.length).to.be.at.least(5));"])),
        req("Track deposit", "POST", "/api/deposits", {"college_id": "{{collegeId}}", "amount_inr": 30000, "paid_on": "2026-11-06", "closure_date": "2026-12-31"}, client_id=True,
            tests=ok(["pm.collectionVariables.set('depositId', pm.response.json().id);"])),
        req("Refund letter", "POST", "/api/refund-letter", {"student_name": "A Student", "college_name": "Example Institute", "amount_inr": 30000,
                                                           "paid_on": "2026-11-06", "closure_date": "2026-12-31", "notice_date": "2026-11-20"},
            tests=ok(["pm.test('100 percent tier', () => pm.expect(pm.response.json().calculation.refund_percent).to.eql(100));"])),
        req("Remove deposit", "DELETE", "/api/deposits/{{depositId}}", client_id=True, tests=ok()),
    ]},
    {"name": "Payments (PayPal sandbox only)", "item": [
        req("Payments config", "GET", "/api/payments/config", tests=ok(["pm.test('sandbox only', () => pm.expect(pm.response.json().environment).to.eql('sandbox'));"]),
            desc="Reports mock or live-sandbox mode. Live PayPal is never used."),
        req("Programs", "GET", "/api/programs", tests=ok(["pm.test('four programs', () => pm.expect(pm.response.json().length).to.eql(4));", "pm.collectionVariables.set('programId', pm.response.json()[0].id);"])),
        req("Slots", "GET", "/api/programs/{{programId}}/slots", tests=ok(["pm.collectionVariables.set('slotStart', pm.response.json()[0].start);"])),
        req("Create booking (creates PayPal sandbox order)", "POST", "/api/bookings", {"program_id": "{{programId}}", "slot_start": "{{slotStart}}"}, client_id=True,
            tests=ok(["pm.collectionVariables.set('bookingId', pm.response.json().id);", "pm.test('order id', () => pm.expect(pm.response.json().paypal_order_id).to.be.a('string'));"])),
        req("Mock approve (mock mode only)", "POST", "/api/bookings/{{bookingId}}/mock-approve", {"approve": True}, client_id=True, desc="Simulates the buyer's PayPal approval. 404 in live-sandbox mode."),
        req("Capture (escrow funded)", "POST", "/api/bookings/{{bookingId}}/capture", client_id=True, tests=ok(["pm.test('funded', () => pm.expect(pm.response.json().status).to.eql('escrow_funded'));"])),
        req("Confirm session completed (payout)", "POST", "/api/bookings/{{bookingId}}/complete", client_id=True, tests=ok(["pm.test('released', () => pm.expect(pm.response.json().status).to.eql('released'));"])),
        req("PayPal webhook (mock signature)", "POST", "/api/webhooks/paypal", {"id": "WH-DEMO-1", "event_type": "CHECKOUT.ORDER.APPROVED", "resource": {}},
            desc="Add header x-mock-signature: valid in mock mode. In live-sandbox mode PayPal signs the request."),
        req("Tech kit", "GET", "/api/kit", tests=ok(["pm.test('kit total', () => pm.expect(pm.response.json().total_inr).to.be.above(0));"])),
    ]},
    {"name": "Intake and agent", "item": [
        req("Intake (English or Hindi)", "POST", "/api/intake", {"text": "मेरे 99.5 पर्सेंटाइल हैं, बजट १८ लाख है, दक्षिण भारत"},
            tests=ok(["pm.test('parsed', () => { const p = pm.response.json().profile; pm.expect(p.percentile).to.eql(99.5); pm.expect(p.budget_lakhs).to.eql(18); pm.expect(p.region).to.eql('South'); });"])),
        req("Agent chat", "POST", "/api/agent/chat", {"message": "Can I afford NIT Calicut with 8 lakh savings?", "profile": {}, "lang": "en"}, client_id=True,
            tests=ok(["pm.test('numbers from calculators', () => pm.expect(pm.response.json().reply).to.include('shortfall'));"])),
    ]},
]
col = {"info": {"name": "EduClear API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "description": "Public API of EduClear, the independent college advisory platform. Every college figure links to an official source; payments run only in the PayPal sandbox."},
       "item": items, "variable": [{"key": k, "value": v} for k, v in
                                    (("collegeId", "nit-calicut"), ("programId", ""), ("slotStart", ""), ("bookingId", ""), ("depositId", ""))]}
env = {"name": "EduClear local", "values": [{"key": "baseUrl", "value": "http://localhost:8000", "enabled": True},
                                             {"key": "clientId", "value": "postman-demo-client-0001", "enabled": True}]}
(OUT / "EduClear.postman_collection.json").write_text(json.dumps(col, indent=2, ensure_ascii=False))
(OUT / "EduClear.local.postman_environment.json").write_text(json.dumps(env, indent=2))
print("wrote", sum(len(g["item"]) for g in items), "requests")
