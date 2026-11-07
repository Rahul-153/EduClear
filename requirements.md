# EduClear — Requirements (derived from BRD, UX Spec, Data Ingestion Manual)

Priority: **P0** must · **P1** should · **P2** stretch. Source: B = BRD section, U = UX Spec section, D = Data Manual section.
Each requirement has acceptance criteria (AC) and a test reference (T). `todo.md` tasks cite these IDs.

---
## 1. Functional requirements (one per BRD feature)

### FR-01 Guided AI intake & bilingual profiler — P0 (B F1, U §2)
- Accept English or Hindi free text (e.g. "93 percentile JEE Main, 18 lakh budget, North or West") and convert to editable profile: stream, percentile/score, 4-yr budget, region.
- Hindi/English keyword+regex parser runs first; Qwen3-4B refines/falls back only for unparsed text.
- Parsed fields appear in the Smart Sentence pills and can be edited in one click.
- AC: 10 sample English and 10 Hindi sentences parse to correct fields (≥90%); LLM-down mode still parses via regex. T: `backend/tests/test_intake.py`.
- P2 add-on: Elastic hybrid vector search matching interests to curricula (INT-06).

### FR-02 Family Alignment Matrix — P1 (B F2)
- Student and parent each rate Brand Prestige, Branch Passion, Location/Safety, Budget Strictness (2-min survey).
- Output: Alignment Score % (deterministic formula) and a "Dinner Table Discussion Guide" with compromises.
- AC: identical ratings → 100%; max-opposed → lowest score; formula documented in `decisions.md`. T: `test_alignment.py`.

### FR-03 Career pathways & degree ROI explorer — P0 (B F3)
- Show Year 0 audited median base, Year 2–5 mid-career, Year 5–10 senior bands, and Time-to-Debt-Freedom (payback months).
- Payback uses disposable salary (D-02); gross-pay figure shown as secondary; assumptions visible and editable.
- AG Charts area chart for trajectory; AG Grid table for comparison.
- AC: payback matches hand-computed values for 3 colleges; shows "15 years of debt" style output when loan-financed. T: `test_roi.py`.

### FR-04 Placement Truth matrix — P0 (B F4, U §2)
- AG Grid comparing: headline brochure CTC, audited median base, true denominator (Placed ÷ Eligible with counts), NAAC/NBA/NIRF rank, Zero-Commission badge.
- Truth Lens toggle (Brochure ⇄ Audited) morphs salary and exposes denominator; brochure CTC shown muted/strikethrough.
- Multi-column sort, filter; <50 ms on 1,000+ rows (NFR-01).
- AC: toggling changes values without reload; denominator renderer shows "X / Y". T: frontend smoke + perf script.

### FR-05 Source-linked regulatory filings & audit trail — P0 (B F5)
- Every datum and AI rationale has a clickable badge to its official source with retrieved date.
- Public API collection documents `/api/colleges`, `/api/colleges/{id}/sources`, etc. (Postman = INT-07, P2).
- AC: 100% of displayed metrics carry a source badge; badge URLs pass the URL gate. T: `test_sources.py`.

### FR-06 Choice-filling rehearsal simulator — P1 (B F6)
- Drag-and-drop preference list of college-branch pairs; real-time alerts for order inversion (lower-cutoff above higher-cutoff option).
- AC: reordering that places easier seat above harder one raises an alert; deterministic rule using verified closing ranks. T: `test_choice_order.py`.

### FR-07 Admissions milestone & fee-deposit roadmap — P0 (B F7, U §5)
- Bryntum timeline of exam dates, allotment rounds, seat-acceptance deposit windows (amount + hours), with countdowns.
- Dates labelled "indicative, based on latest published cycle" with citation (D-03).
- AC: timeline renders from data file; countdown correct against a fixed clock in tests.

### FR-08 Campus essentials & tech-kit budgeting — P0 (B F8, D §3 Step 5)
- Branch → required kit (CS/AI: GPU laptop ≥16GB RAM RTX 3050/4060 + peripherals; Mech/Civil: CAD laptop; MBA: ultraportable + attire).
- Channel3 `/v1/search` gives live title, price, buy link; added to all-inclusive budget; PayPal Checkout / Pay Later button.
- Fallback: cached last-good Channel3 response or mock catalog flagged "sample listing".
- AC: kit total updates budget; Pay Later offered for USD sandbox order. T: `test_channel3.py`, PayPal sandbox suite.

### FR-09 Seat deposit & UGC refund tracker — P1 (B F9)
- Track deposits per institution; countdown alerts before UGC 100% refund cutoff; generate refund-request letter (template, no LLM numbers).
- PayPal webhook / dispute simulation hooks (sandbox).
- AC: adding deposit shows countdown; letter includes institution, amount, dates. T: `test_refund.py`.

### FR-10 Counsellor booking with escrow payouts — P0 (B F10, U §3–4)
- 4 programs: Branch vs College 1:1 45 min ₹2,499 (escrow); JoSAA Audit 1:1 60 min ₹2,999 (escrow); Year-1 Roadmap cohort 90 min max 25 ₹999/seat (direct); Family Consensus 1:1 60 min ₹3,499 (escrow).
- Bryntum Scheduler slot selection → create PayPal sandbox order → approve/capture → ledger `funded` → (Zapier P2: calendar/Zoom invite; fallback: confirmation email stub) → "Confirm Session Completed" → Payout to counsellor → ledger `released`.
- Cohort capacity enforced (25). Double-booking prevented.
- AC: full path passes in sandbox; replayed webhook does not double-fund. T: PayPal sandbox suite.

### FR-11 Autonomous financial & admissions agent — P1 (B F11)
- Chat Copilot: affordability over 4 years, per-semester net deficit, loan EMI comparison, slot lookup, creates PayPal sandbox order on request (Agent Toolkit/MCP).
- Hybrid: Python tools compute; Qwen3-4B selects tool from a fixed list and phrases output (D-07).
- AC: 5 scripted conversations produce correct tool calls and numbers equal to engine outputs; works in fallback (no LLM) with canned intents.

### FR-12 Deployment & hosted demo — P0 (B F12)
- One Render web service (FastAPI + built React), `render.yaml`, env vars, health check, public URL.
- AC: smoke script passes against public URL.

---
## 2. UX requirements

| ID | Requirement | Pri |
|---|---|---|
| UX-01 | Palette: canvas #FAFAFA; cards #FFFFFF with shadow `0 1px 3px rgba(0,0,0,.02), 0 12px 32px -8px rgba(0,0,0,.04)`; hairline `1px solid rgba(0,0,0,.07)`; headings #0F172A (600, −0.02em); body #475569; meta #94A3B8 uppercase 0.06em | P0 |
| UX-02 | Accents: emerald #059669 only for audited salaries, debt-free clocks, 0% commission badges; amber #D97706 for deposit deadlines; strikethrough #94A3B8 for brochure CTC | P0 |
| UX-03 | Fonts: Plus Jakarta Sans (−0.011em); JetBrains Mono/tabular numerals for figures | P0 |
| UX-04 | Header: logo, English/हिंदी toggle, Independent badge, Truth Lens capsule (Brochure ⇄ Audited Truth) | P0 |
| UX-05 | Smart Sentence bar: pill dropdowns for stream, score, budget, region; live update | P0 |
| UX-06 | Bento Match Deck: Safe Anchor / Sweet Spot / Dream Reach with 4-yr cost, audited salary, Debt-Free clock | P0 |
| UX-07 | Sections in order: Bento deck → Admissions & Deposit timeline → Counselling sessions → Student hardware kit | P0 |
| UX-08 | Floating Copilot pill bottom-right; 400px drawer, no intrusive popups | P1 |
| UX-09 | Responsive down to 375px; keyboard accessible; contrast AA | P0 |
| UX-10 | Hindi translations for all static UI strings (i18n file) | P1 |
| UX-11 | Visible disclosure of USD sandbox conversion and "escrow = platform ledger" | P0 |

---
## 3. Data requirements (D = Data Manual)

| ID | Requirement |
|---|---|
| DR-01 | Zero-synthetic: every figure from signed NIRF filing / audited report / official circular (D §1.1) |
| DR-02 | Denominator integrity: Placed ÷ Eligible stated; batch, eligible, placed, higher studies separated (D §1.2) |
| DR-03 | All-inclusive 4-yr cost = 4 × (tuition + mandatory fees + hostel/mess + tier living); 2× for IIM (D §1.3, Gate 4) |
| DR-04 | Each record has public, timestamped source URL (D §1.4) |
| DR-05 | Records match master JSON schema (D §4); additive source fields only (D-04) |
| DR-06 | Gates 1–6 pass (D §5): placed ≤ eligible ≤ batch; rate within ±0.5; headline ≥ median; cost multiplier; valid NIRF URL; commercialRelationship string |
| DR-07 | Living cost by HRA tier X/Y/Z bands (D §2 row 4) |
| DR-08 | Cutoffs from JoSAA Round 6 (CSE, OS/HS, OPEN) or the institution's own published cutoff, stated in `primaryExam` |
| DR-09 | `npm run validate:data` runs the validator; passes before any merge |
| DR-10 | ~10 colleges at launch; alternates substituted if unverifiable (D-05) |

---
## 4. Non-functional requirements

| ID | Requirement | Pri |
|---|---|---|
| NFR-01 | Grid filter on 1,000+ rows <50 ms; page load <1.8 s | P0 |
| NFR-02 | Minor-data safeguarding (DPDP principles): no PII in logs or LLM prompts; nothing sold/shared | P0 |
| NFR-03 | Auditability: every metric has timestamped citation | P0 |
| NFR-04 | Resilience: PayPal/Channel3/LLM each have mock fallback; demo stable if any is down | P0 |
| NFR-05 | Secrets only in `.env`; PayPal sandbox-only guard at startup | P0 |
| NFR-06 | Offline-runnable unit tests; live sandbox tests marked `paypal_sandbox` | P0 |
| NFR-07 | Idempotent webhooks and payments (no double fund/payout) | P0 |

---
## 5. Integration requirements

| ID | Sponsor | Contract | Fallback | Pri |
|---|---|---|---|---|
| INT-01 | PayPal | Orders v2 (USD), JS SDK v6 Smart Buttons + Pay Later, webhooks with signature verification, Payouts API, Agent Toolkit/MCP | Recorded-response mock | P0 |
| INT-02 | AG Grid | Community + Charts: Truth matrix, trajectory charts | n/a | P0 |
| INT-03 | Bryntum | Timeline/Gantt (admissions), Scheduler (booking) | Plain HTML timeline | P0 |
| INT-04 | Channel3 | `GET/POST https://api.trychannel3.com/v1/search` | Cached/mock catalog | P0 |
| INT-05 | Render | Web service + Postgres via `render.yaml` | Local run instructions | P0 |
| INT-06 | Elastic | Hybrid vector search over curricula | In-memory TF-IDF search | P2 |
| INT-07 | Postman | Public collection + endpoint tests | Exported JSON in repo | P2 |
| INT-08 | Zapier | Catch-hook/MCP → Calendar + Zoom invite | Email stub, ledger note | P2 |
| INT-09 | LLM | Qwen3-4B hosted API; Ollama dev fallback | Rule-based intents | P0 |

---
## 6. Definition of done (BRD §8, UX §7)
- DoD-01 Brand identity EduClear applied · DoD-02 All pillars demo-able end to end · DoD-03 PayPal, AG Grid, Bryntum, Channel3, Render integrated for real · DoD-04 Public GitHub repo with MIT licence · DoD-05 Demo video <3 min · DoD-06 Live Render URL · DoD-07 Porcelain aesthetic, Smart Sentence, Truth Lens, 4 programs, PayPal escrow + Pay Later working in sandbox.

## 7. Traceability (feature → phase)
FR-05/03 → Phase 2 · FR-01/02/03/04 UI → Phase 3 · FR-06/07/09 → Phase 4 · FR-08/10 → Phase 5 · FR-11/01 LLM → Phase 6 · FR-12 + stretch → Phase 7 · DR-* → Phase 1.
