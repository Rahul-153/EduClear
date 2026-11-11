# Prompt: add more verified colleges to EduClear

Copy everything below the line into a new Claude Code session opened in `/Users/rahul/Desktop/Gen AI/Paypal-hackthon`.

---

You are extending the verified college dataset of **EduClear**, a PayPal AI Hackathon project (submission deadline 12 Nov 2026, 12:00 pm Pacific). Work only inside this folder.

## Read first, in this order
1. `AGENT_MANUAL.md` (working style and rules; follow it)
2. `DATA_INGESTION_MANUAL.md` (the data procedure; sections 2 to 5 matter most)
3. `decisions.md` entries D-04, D-05, D-09, D-18 to D-26, D-40 (data rules and what was excluded and why)
4. `data/VERIFICATION_REPORT.md` and one finished record such as `data/colleges/nit-calicut.json` (this is the exact shape and level of evidence expected)
5. `scripts/college_model.py` (schema), `scripts/validate_data.py` (6 integrity gates plus provenance checks)

## Why this task exists
Only 7 audited colleges exist (DTU Delhi, BITS Pilani, IIT Hyderabad, IIT BHU, IIT Guwahati, MNIT Jaipur, NIT Calicut). They are all very selective, so a student at 99 percentile or below gets an empty recommendation deck, and the Safe / Sweet spot / Dream reach cards are almost never all filled. **Goal: add at least 10 more colleges, prioritising institutes whose closing ranks are reachable at roughly 94 to 99 JEE Main percentile**, so that every percentile in the app's dropdown (99.9, 99.75, 99.5, 99, 98, 96, 94.2) returns something real.

## Non-negotiable data rules
- **Zero synthetic data.** Every number comes from an official document (NIRF institute-submitted data, JoSAA/CSAB archive, the institute's own fee circular and placement report). Never estimate, round up, interpolate, copy from a news site, or fill a gap.
- **If any required figure cannot be verified, skip that college and move to the next one.** Do not substitute a guess. Report each skip with the reason (see D-22 to D-26 for how earlier skips were handled).
- Placement figures: NIRF 2025 institute-submitted data, UG 4-year programme, latest graduating batch 2023-24 (D-20). Eligible students = batch minus direct higher studies (D-09). Placement rate = placed / eligible.
- Headline CTC must come from the institute's own same-season (2023-24) document (D-22). If two official figures conflict, use the lower one and state the conflict in `placementAuditNote` (D-23).
- Fees: general category, B.Tech CSE, latest incoming-batch circular; apply the accounting rules in D-19 and D-25. Flag every scanned or averaged figure in provenance.
- Cutoffs: JoSAA 2025 Round 6 closing ranks for CSE (open seats, All India and the home-state / other-state quota where it applies). IIT cutoffs are JEE Advanced ranks and `safeCutoffScore` stays null (D-21). Non-JoSAA institutes (BITS, IIIT-Delhi style) use their own published cutoff and say so in `primaryExam`.
- Every field in `sources.provenance` needs `url`, `locator` (table / page / section) and the `snapshot` file. Save each source document to `data/sources/<college-id>/` and record its SHA-256 in `sources.snapshots`.
- `commercialRelationship` must be exactly `None (100% Student-Funded & Independent)`. `sources.verificationStatus` becomes `Audited & Verified` only after the second pass below.

## Suggested candidate pool (check in this order, stop when you have enough passes)
Mid-tier NITs and IIITs first because they widen the reachable range: MNNIT Allahabad, NIT Durgapur, NIT Kurukshetra, NIT Hamirpur, NIT Jalandhar, NIT Patna, NIT Silchar, NIT Raipur, NIT Agartala, NIT Goa, IIIT Allahabad, IIIT Gwalior, IIIT Kota, IIIT Vadodara, NSUT Delhi, IGDTUW, PEC Chandigarh, BIT Mesra, COEP Pune, Thapar. Already excluded earlier, do not retry unless an official source now exists: IIT Bombay, IIT Delhi, IIT Madras, IIT Roorkee, IIT Kanpur, IIT Kharagpur, NIT Rourkela, VNIT Nagpur, NIT Trichy, NIT Surathkal, NIT Warangal, IIIT Hyderabad, VIT Vellore (see D-22 to D-26). If a college's record cannot reach the standard, skip it and say why.

## Procedure per college
1. Research with the browser tools or `requests`. Official sources only: nirfindia.org, josaa.admissions.nic.in (use `scripts/scrape_josaa.py`; the JoSAA form needs the seat-type postback order the script already handles), csab.nic.in, and the institute's `.ac.in` or `.edu` domain.
2. Save every source file under `data/sources/<id>/` and compute its SHA-256.
3. Build the JSON in `data/colleges/<id>.json` following `scripts/college_model.py` exactly (use `scripts/assemble_records.py` if it helps).
4. **Second pass:** a separate subagent, given only the saved snapshots and the record, re-reads every figure independently. Any mismatch blocks the record until resolved or the college is skipped.
5. Run `npm run validate:data` and `.venv/bin/python scripts/validate_data.py --check-urls`. Every record must pass all 6 gates and the URL check.

## Keep the app consistent
- The backend loads `data/colleges/*.json` automatically. After adding records, check `/api/recommend` for the profile `{stream: "Computer Science", budget_lakhs: 35, region: "All"}` at each dropdown percentile and report how many deck cards are filled before and after.
- Update `data/VERIFICATION_REPORT.md` (run `scripts/make_report.py`), add a decision entry in `decisions.md` listing included and skipped colleges with reasons, tick or add tasks in `todo.md`, and update the college count in `README.md` and `REQUIREMENTS_STATUS.md` (DR-10).
- Run `.venv/bin/python -m pytest backend/tests tests -q`. Fix any test that hard-codes "7 colleges" only if the new count is legitimately correct, and say what you changed.

## Hard constraints
- **Do not commit or push `data/sources/`**. It is git-ignored; keep it that way (D-40).
- **Never rewrite git history.** Once, `git filter-branch` destroyed the evidence folder. Back up `data/sources/` before any bulk operation.
- Do not commit or push anything yourself. Leave all changes uncommitted and tell me what changed; I will review and push.
- No secrets in files. No new dependencies unless unavoidable (ask first).

## Report when done
A table of every college tried: included or skipped, the reason for each skip, which figures were hardest to verify, the before and after deck coverage per percentile, the validator and test results, and anything I should spot-check by hand.
