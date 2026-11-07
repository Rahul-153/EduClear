# EduClear — Decision Log
Format: **D-nn · date · status** — Decision · Why · Alternatives · Impact. Append only; supersede with a new entry rather than editing history.

**D-01 · 2026-11-06 · Accepted** — Stack: Python 3.12 FastAPI backend + React/Vite/TypeScript frontend, one Render web service serving both. Why: user chose Python backend; AG Grid and Bryntum are JS libraries. Alt: Next.js, Express. Impact: two toolchains, one deploy.

**D-02 · 2026-11-06 · Accepted** — Payback ("Time-to-Debt-Freedom") = total 4-yr cost ÷ monthly *disposable* income (post-tax in-hand minus living cost); gross-pay payback shown as secondary. Why: BRD says disposable; prototype's 8.2 months equals cost ÷ gross pay (₹10.6L ÷ ₹1.29L/mo) and flatters results. Assumptions (tax regime, living cost) visible/editable. Prototype figures are placeholders only.

**D-03 · 2026-11-06 · Accepted** — Admissions dates/deposit windows come from the latest published JoSAA/UGC notices and are labelled "indicative, based on latest published cycle" with citation. Why: prototype dates (Dec 20–24, UGC cutoff 15 Jan 2027) are unsourced; BRD/prototype say 96 h seat-acceptance window, UX spec says 72 h — verify against JoSAA before display.

**D-04 · 2026-11-06 · Accepted** — Master schema kept exactly; only additive fields under `sources`: `nirfYear`, `retrievedAt`, `headlineCtcUrl`, `feeCircularUrl`, `cutoffUrl`, `sha256`. Why: audit trail needs retrieval evidence the manual schema lacks.

**D-05 · 2026-11-06 · Accepted** — Data gaps: if a figure cannot be verified from an official source, skip that college and substitute an alternate (NSUT, IIIT Delhi, SRM, Thapar). Never estimate. Report skips to user.

**D-06 · 2026-11-06 · Accepted** — "Escrow" = capture into platform's PayPal sandbox business account + internal ledger (`funded` → `released`), release via Payouts API on "Confirm Session Completed". Why: PayPal has no escrow product. Disclosed in UI (UX-11).

**D-07 · 2026-11-06 · Accepted** — LLM: Qwen3-4B (≤4B) via hosted API (provider TBD by user keys), Ollama for local dev. Hybrid: all numbers from deterministic Python; LLM parses intake, phrases explanations, and selects from a fixed tool list with schema-constrained JSON; Hindi regex/keyword layer first; rule-based fallback if LLM down. Why: small model weak at tool-calling/Hindi; zero-synthetic policy forbids LLM-made numbers.

**D-08 · 2026-11-06 · Accepted** — UI shows ₹; PayPal sandbox charges in USD at a fixed documented INR→USD rate shown to the user; US-country sandbox Business and Personal accounts. Why: Pay Later and Payouts are unreliable/unavailable for INR.

**D-09 · 2026-11-06 · Accepted** — Eligible students E = batch graduating in time − students going directly to higher studies (manual §3 Step 2); placement rate = Placed ÷ E. One formula everywhere.

**D-10 · 2026-11-06 · Accepted** — JEE percentile→rank for fit tiers: rank ≈ (100 − percentile)/100 × candidates appeared (NTA figure for cited year, recorded with source). Non-JEE institutions (BITS, VIT, etc.) use their own published cutoffs, stated in `primaryExam`; fit tier for those uses a documented mapping.

**D-11 · 2026-11-06 · Accepted** — Sponsor scope: must-have PayPal, AG Grid, Bryntum, Channel3, Render; stretch Postman → Zapier → Elastic, each with fallback.

**D-12 · 2026-11-06 · Accepted** — Dataset: ~10 engineering colleges: IIT Bombay, IIT Delhi, IIT Madras, NIT Trichy, NIT Surathkal, NIT Warangal, DTU, IIIT Hyderabad, BITS Pilani, VIT Vellore. Latest available NIRF edition used (not necessarily 2024).

**D-13 · 2026-11-06 · Accepted** — Licensing: Bryntum via trial/sponsor registry access; AG Grid Community + Charts unless a prize requires Enterprise. Repo MIT licence; no Bryntum source committed.

**D-14 · 2026-11-06 · Accepted** — Tooling: system Python is 3.9.6, so Python 3.12 installed via `uv` into project `.venv` only. No global installs.

**D-15 · 2026-11-06 · Accepted** — 7-day schedule (to 13 Nov) with priority tiers P0/P1/P2 (see plan.md); if behind, cut P2 then P1 in reverse order.

**D-16 · 2026-11-06 · Accepted** — Validator is Python (`scripts/validate_data.py`) porting the manual's 6 TypeScript gates; root `package.json` script `validate:data` wraps it so `npm run validate:data` still works.

**D-17 · 2026-11-06 · Accepted** — Process: dataset first, hard gate for user sign-off before app code; PayPal tested in sandbox only with a startup guard refusing live credentials.

**D-18 · 2026-11-06 · Accepted** — D-04 extended: `sources.snapshots` (filename→sha256) and `sources.provenance` (field path→{url, locator, snapshot}) are required by the validator for key fields so the verification report can be generated and hashes re-checked. Validator also enforces D-09 (eligible = batch − higher studies) as an extra gate.

**D-19 · 2026-11-06 · Accepted** — Fee accounting rules: general category, B.Tech CSE, latest incoming-batch circular. One-time non-refundable fees are summed and divided by 4, then added to annual mandatory fees; refundable deposits excluded. `estimatedLivingAnnual` = midpoint of the manual's HRA band (X ₹62,500; Y ₹37,500; Z ₹25,000), with the city's class cited from the 7th CPC HRA order. Schema `tier`: X→"Tier 1", Y→"Tier 2", Z→"Tier 3".

**D-20 · 2026-11-06 · Accepted** — Placement figures come from NIRF 2025 (India Rankings 2025) institute-submitted data, UG 4-year programme, latest graduating batch 2023-24 (the NIRF 2026 Engineering list was not published at the 2026 URL when checked). `batchSize` = graduating in minimum time; `higherStudiesOrFounders` = students selected for higher studies; `eligibleStudents` = batch − higher studies (D-09). NIRF DCS does not state founders; field name kept per schema.

**D-21 · 2026-11-06 · Accepted** — Cutoffs are stored exactly as the official counselling body publishes them (JoSAA 2025 Round 6, CSE 4-yr B.Tech, OPEN, Gender-Neutral; NIT: OS and HS closing ranks; IIT: All-India closing rank, which is a JEE **Advanced** rank, `primaryExam` = "JEE Advanced"). `safeCutoffScore` (a JEE Main percentile) is therefore null unless an official percentile exists; rank↔percentile mapping is computed in the Phase 2 engine from NTA's published candidate count (D-10), not stored as data. JoSAA 2026 archive not yet listed (latest year 2025).

**D-22 · 2026-11-06 · Accepted (user)** — Strict headline-CTC rule: a college is included only if its own official documents state a same-season (2023-24) highest package. Excluded after wave 1: IIT Bombay (only 2022-23), IIT Delhi (policy: not published), IIT Madras, NIT Trichy, NIT Surathkal (none published). Their findings stay in `data/sources/<id>/` for reference.

**D-23 · 2026-11-06 · Accepted (user)** — Ambiguous headline figures (domestic vs international, CTC vs base, internal discrepancies) use the lower official figure with the ambiguity stated in `placementAuditNote`.

**D-24 · 2026-11-06 · Accepted (user)** — Replace with alternates: NIT Warangal (hostel+mess not derivable), IIIT Hyderabad (annual fees not published per year), VIT Vellore (no official cutoff). Wave 2 researches a wider candidate pool; first 8 that pass all gates join DTU and BITS Pilani to reach 10.

**D-25 · 2026-11-06 · Accepted (user)** — Fees may use published mess advances, 4-year averages and scanned circulars, each flagged in provenance/report for spot-check.

**D-26 · 2026-11-06 · Proposed** — Wave 2 outcome: passing = DTU Delhi, BITS Pilani, IIT Hyderabad, IIT BHU, IIT Guwahati, MNIT Jaipur, NIT Calicut (7). Excluded: IIT Roorkee/Kanpur/Kharagpur (no 2023-24 highest package), NIT Rourkela, VNIT Nagpur (Drive-only), Thapar (2022-23 only), SRM (no published cutoff), Manipal/Amrita (undated figures), Jadavpur/KIIT/IIIT Delhi/NSUT (site blocks or TLS errors from automated fetch). Shipping 7 vs researching a third wave is awaiting user decision.

**D-27 · 2026-11-06 · Accepted (user)** — Dataset gate passed: user signed off the 7-college dataset (DTU Delhi, BITS Pilani, IIT Hyderabad, IIT BHU, IIT Guwahati, MNIT Jaipur, NIT Calicut). D-26 closed. Phase 2 starts.

**D-28 · 2026-11-06 · Accepted** — Engine assumptions are model parameters, not audited data, and are always shown/editable in the UI: (a) JEE Main 2025 unique candidates appeared = 14,75,103 (NTA result notice of 18 Apr 2025 as reported secondhand; official page jeemain.nta.nic.in not directly readable) used only to approximate AIR from percentile; (b) new-regime income tax FY2025-26 slabs (nil to ₹4L, 5/10/15/20/25/30% per ₹4L band, standard deduction ₹75,000, 87A rebate to ₹12L taxable, 4% cess; surcharge ignored) — verify against Income Tax Dept before launch; (c) savings rate 40% of in-hand pay for payback; (d) salary growth 10%/yr for the illustrative Year 2–10 trajectory (labelled "illustrative, not audited"); (e) loan rate 9.5% and tenure 10 yrs for EMI. Year-0 values come only from audited NIRF medians.

**D-29 · 2026-11-06 · Accepted** — Verified data covers CSE only, so the Smart Sentence stream list is limited to "Computer Science" (ECE/MBA from the prototype return `supported:false` until data exists). IIT fit needs a JEE Advanced rank and BITS needs a BITSAT score; with only a JEE Main percentile those cards are returned in `needs_more_input` rather than guessed. Fit margins: Safe if rank <= 0.8 x closing, Target <= closing, Reach <= 1.5 x closing (editable). Note: the prototype persona (94.2 percentile, AIR ~85,000) is out of reach for every JEE Main college in the dataset; demo defaults should use 99.7+.

**D-30 · 2026-11-06 · Accepted** — Frontend: FastAPI serves `frontend/dist` from the same service (one Render service, D-01). AG Grid 36 and AG Charts 14 are registered via `AllCommunityModule` (bundle 2.2 MB unminified-gzip 650 KB; trim later for NFR-01 page load). Brochure mode shows disclosed placement % and struck-through headline CTC; Audited mode shows median base and the Placed / Eligible denominator. Dev: `npm run dev` in `frontend/` proxies /api to :8000; demo: `npm run build` then run uvicorn.

**D-31 · 2026-11-06 · Accepted** — Admissions facts come only from official documents (data/sources/_admissions/): JoSAA 2026 had 5 rounds (no Round 6); seat acceptance fee is Rs 30,000 general / Rs 15,000 reserved (includes Rs 5,000 processing; Rs 7,000 withheld on valid withdrawal) paid by a 17:00 IST date per round. This corrects the UX spec/prototype (Rs 35,000 within 72 or 96 hours — no such hour limit is printed). UGC refund tiers (2018 notification, restated 2024 and Oct 2025): 100% if notice is 15+ days before the institution's last date of admission, 90% <15 days before, 80% up to 15 days after, 50% 16-30 days after, 0% after; processing fee 5% (max Rs 5,000) on the first tier only; refund within 15 days of written application. No 2026-27-specific UGC policy was found; AICTE student refund rules are unverified (aicte.gov.in is outside the approved domains, the one file saved from there was deleted). JoSAA files were read from josaa.nic.in and its CDN (the official redirect target of josaa.admissions.nic.in).

**D-32 · 2026-11-06 · Accepted** — Deposits are stored per anonymous browser ID (X-Client-Id header, localStorage UUID), never shared across visitors (NFR-02). Refund letters are generated from request data and not stored. Bryntum timeline/scheduler swap-in is deferred until credentials are supplied (T-4.01).

**D-33 · 2026-11-06 · Accepted** — Counsellor: BRD persona "Dr. Ramesh Sharma, ex-IIT Roorkee Dean" is NOT used as a real vetted person; the app shows "Demo counsellor (sandbox profile)" so no real identity or credential is implied. Real counsellors need verification before launch.

**D-34 · 2026-11-06 · Accepted** — Payments design: bookings are scoped to an anonymous browser id; amounts are computed server-side (clients never set price); USD cents = round(INR x 0.012 x 100); funds are captured to the platform sandbox account and recorded in a ledger (unique PayPal reference = idempotency, plus a processed-webhook table); escrow release uses Payouts with a deterministic sender_batch_id per booking; PayPal live is impossible (pinned sandbox base URL, startup guard). Mock mode runs when no sandbox keys exist; live-sandbox mode uses PayPal JS SDK v6 (`@paypal/paypal-js/sdk-v6`, `paypal-button` and `paypal-pay-later-button`), written against the published types but NOT yet exercised against the real sandbox. Pay Later needs a US sandbox buyer (D-08). Channel3 response schema is parsed tolerantly (docs not verified); sample listings are labelled and are not live prices.

**D-35 · 2026-11-06 · Accepted** — No DB migrations in the hackathon build: schema is created from models (`create_all`); a stale local SQLite file must be deleted when models change. Fresh Render Postgres is created from current models.

**D-36 · 2026-11-06 · Accepted** — Agent safety and speed: (1) tool routing is rules-first; the model is consulted only when rules find no intent (measured ~18 s per message when the model routed and re-phrased every turn on local Qwen3-4B; rules path is instant); (2) re-phrasing by the model is opt-in (`LLM_PHRASING=true`) and rejected unless the answer contains exactly the same numbers; (3) intake only calls the model for missing percentile/budget/region (stream defaults to Computer Science) and discards any value not literally supported by the user's text; (4) the agent cannot create a payment order itself: it returns a pending action that the user must confirm (10-minute, single-use, owner-bound); (5) emails and phone numbers are redacted before any text reaches a model. Hosted Qwen needs LLM_PROVIDER/LLM_API_KEY/LLM_MODEL; local Ollama is auto-detected for development.

**D-37 · 2026-11-06 · Open** — The BRD targets the PayPal Agent Toolkit / MCP server for the agentic-commerce prize. Phase 6 delivers the agentic flow (propose -> human confirm -> sandbox order) on our own service layer, not the official toolkit. Decide whether to add the toolkit once sandbox keys exist (it would sit behind the same confirm step).

**D-38 · 2026-11-07 · Accepted** — Deploy shape: Docker web service (Node build stage + Python runtime) with Postgres via render.yaml; `data/sources` (363 MB of evidence) is excluded from the image and only needed in the repo as the audit trail; consider Git LFS or trimming the excluded colleges' PDFs before pushing publicly. MIT licence holder is written as "EduClear contributors" (change if you want a named holder). No Elastic search was built (P2): it would need Elastic Cloud keys and the dataset has little free text to search.

**D-39 · 2026-11-07 · Accepted** — Frontend performance: AG Grid and AG Charts are lazy-loaded and registered only inside their components (first load 82 KB gzipped, grid chunk 254 KB, chart chunk 323 KB); `frontend/perf.html` is a dev-only harness with synthetic rows, excluded from the production build.
