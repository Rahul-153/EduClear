# EduClear — Implementation Plan (PayPal AI Hackathon, deadline 13 Nov 2026)

## Context
The folder holds the BRD, UX spec, data-ingestion manual and an HTML prototype for **EduClear**, an independent college-advisory and financial-planning platform. Nothing is built yet. Today is 6 Nov, so there are **7 days**. The user wants (a) a streamlined, complete, trackable plan, (b) the **dataset built and verified first**, and only then the app. After approval I create the project docs, then start Phase 1 (dataset) and **stop at a user verification gate**.

**Confirmed decisions (from Q&A):** Python backend (FastAPI) + React/Vite/TS frontend (AG Grid and Bryntum are JS-only) · ~10 verified engineering colleges · core sponsors must-have = PayPal, AG Grid, Bryntum, Channel3, Render; Elastic, Zapier, Postman = stretch with fallbacks · LLM = Qwen3-4B (≤4B) via hosted API, **hybrid**: all numbers from deterministic Python, the LLM only parses intake / phrases explanations / picks from a fixed tool list · data gaps → skip college and substitute · UI in ₹, PayPal sandbox charged in USD at a fixed documented rate.

## Deliverables created first (Phase 0, in `/Users/rahul/Desktop/Gen AI/Paypal-hackthon/`)
| File | Purpose |
|---|---|
| `plan.md` | This plan, cleaned: phases, day-by-day schedule, architecture, repo layout, gates, risks |
| `todo.md` | Phase → task checklist, IDs `T-<phase>.<nn>`, status/date/evidence per task. **Updated after every completed task** |
| `decisions.md` | Numbered ADR log (D-01…): decision, why, date, alternatives, impact. Includes the doc-conflict resolutions below |
| `AGENT_MANUAL.md` | Rules every session must read first: folder map, read-order, "how to run a task" loop, data rules, coding standards, secrets rules, definition of done, update-todo rule |
| `CLAUDE.md` | 3 lines pointing to `AGENT_MANUAL.md` so the harness auto-loads it each session (keeps sessions anchored to this folder) |
| `requirements.md` | Traceable requirements derived from BRD + UX spec (see below) |
| `KEYS_CHECKLIST.md` + `.env.example` | The credentials table below; no real secrets committed; `.env` git-ignored |
| `PREREQS.md` | Result of the Phase 0b prerequisite check (below) |

`AGENT_MANUAL.md` loop: read manual → `todo.md` (next unchecked task) → `decisions.md` → `requirements.md` IDs for the task → do it → run its verification → tick `todo.md` with date + evidence → log any new decision → report.

### `requirements.md` structure
IDs with source + priority (P0 must / P1 should / P2 stretch) + acceptance criteria + test reference:
- **FR-01…FR-12** one per BRD feature (intake, alignment matrix, ROI explorer, Placement Truth matrix, source badges, choice-filling simulator, admissions timeline, tech-kit, refund tracker, counsellor escrow booking, PayPal agent, deployment).
- **UX-xx** design tokens (#FAFAFA/#FFFFFF/#0F172A/#475569/#94A3B8, emerald #059669, amber #D97706), Plus Jakarta Sans + JetBrains Mono, Smart Sentence, Truth Lens capsule, Bento deck, 400px Copilot drawer, 4 session programs (₹2,499 / ₹2,999 / ₹999 / ₹3,499), English/हिंदी toggle.
- **DR-xx** data policy (zero-synthetic, denominator integrity, all-inclusive cost, audit URL), master schema, 6 gates.
- **NFR-xx** grid filter <50 ms on 1,000+ rows, page load <1.8 s, DPDP-style minor-data privacy (no PII to LLM/logs), timestamped citations, resilience via mock fallbacks for PayPal/Channel3/LLM.
- **INT-xx** per-sponsor integration contract + fallback.
- **DoD-xx** BRD §8: public repo + open-source license (MIT), <3-min demo video, Render URL.

### Phase 0b — Prerequisite check (before any Phase 1 work; results in `PREREQS.md`, ticked in `todo.md`)
Read-only/version checks first, installs only into the project (no global changes), each with PASS/FAIL + fix:
- **Toolchain:** `uv`, Python 3.12 (install via `uv` into `.venv`; system 3.9.6 is too old), Node ≥20, npm, git, `ollama` (optional dev LLM). Create `.venv`, install FastAPI/pydantic/pytest and confirm `pytest` and `npm run validate:data` stubs run.
- **Network reachability** (HEAD/GET only): nirfindia.org, josaa.admissions.nic.in, ugc.gov.in, institute `.ac.in` domains, `api.trychannel3.com`, `api-m.sandbox.paypal.com`, npm.bryntum.com, chosen LLM provider; flag any that are blocked or need a browser-driven fetch.
- **Credentials presence** (names only, never values): which of the `.env` keys below are set; report missing ones and which phase they block. Phase 1 needs none.
- **Account prerequisites to confirm with you:** PayPal sandbox US Business + Personal accounts, Payouts enabled, Bryntum trial access, Render credits, GitHub repo permission, Qwen provider chosen.
- **Disk/permissions:** write access to `data/sources/`, ports 8000/5173 free.
- **Go/No-go:** Phase 1 starts once the toolchain and network checks pass; missing keys only block their own later phase.

## PayPal sandbox testing (sandbox only — never live credentials)
Hard guard: `PAYPAL_ENV=sandbox` is the only accepted value; base URL pinned to `https://api-m.sandbox.paypal.com`; app refuses to start if a live client ID is detected. Test plan (`backend/tests/paypal/` + `scripts/paypal_sandbox_smoke.py`, results logged in `todo.md`):
1. **Auth:** OAuth token fetch with sandbox Client ID/Secret.
2. **Orders v2:** create (USD, fixed INR→USD rate) → buyer approval with the sandbox Personal account → capture; verify amounts, status, and ledger `funded`.
3. **Pay Later:** Smart Buttons render with Pay Later for US sandbox buyer; Pay in 4 flow on the tech-kit order.
4. **Webhooks:** register sandbox webhook; signature verification via `/v1/notifications/verify-webhook-signature`; replay of `CHECKOUT.ORDER.APPROVED` and `PAYMENT.CAPTURE.COMPLETED`; idempotency (duplicate event ignored).
5. **Payouts:** on "Confirm Session Completed" send a sandbox payout to the counsellor test account; check batch status and ledger `released`.
6. **Failure paths:** declined/cancelled approval, capture failure, insufficient Business balance, payout failure, timeouts → mock fallback + clear UI state.
7. **Agent Toolkit/MCP:** agent creates a sandbox order via the toolkit; same ledger assertions.
8. **Unit tests** use recorded/mocked responses (run offline in CI); the live-sandbox suite is a separate marked run (`pytest -m paypal_sandbox`) executed only with sandbox keys present.

## Phase 1 — Dataset (first work after docs, ends at USER GATE)
Layout: `data/schema/college.schema.json`, `data/colleges/<id>.json`, `data/sources/<id>/` (saved PDFs/HTML snapshots with SHA-256 + retrieved date), `data/VERIFICATION_REPORT.md`, `scripts/validate_data.py`, root `package.json` script `validate:data` → calls the Python validator (keeps the manual's `npm run validate:data` command).

Steps:
1. **Pydantic model** mirroring the manual's master JSON schema exactly. Additive-only source fields (`nirfYear`, `retrievedAt`, `headlineCtcUrl`, `feeCircularUrl`, `cutoffUrl`, `sha256`) logged as D-xx.
2. **Port the 6 gates to Python** (batch denominators, rate math ±0.5, headline ≥ median, total = 4× annual sum (2× for IIM), valid NIRF URL, commercialRelationship string) plus extra checks: URL reachable, year recorded, fee-circular date present.
3. **Candidate list (10, with alternates NSUT, IIIT Delhi, SRM, Thapar):** IIT Bombay, IIT Delhi, IIT Madras, NIT Trichy, NIT Surathkal, NIT Warangal, DTU, IIIT Hyderabad, BITS Pilani, VIT Vellore. Covers North/South/West and ₹10L–₹35L+ cost range, includes the prototype's three.
4. **Per-college SOP (manual §3):** NIRF DCS Table 3.A/3.B (latest NIRF edition available, not necessarily 2024) → batch/eligible/placed/median; fee circular (tuition, mandatory fees, hostel+mess); HRA-tier living cost; JoSAA Round-6 closing rank (CSE, OS/HS, OPEN) — drive the archive form with the built-in browser if it is not scrapable; non-JoSAA institutions (BITS, DTU/JAC Delhi, VIT, IIIT-H) use their own published cutoffs and say so in `primaryExam`; headline CTC from the official placement report/press release only.
5. **Two-pass verification:** I extract; a separate subagent re-opens each source and re-reads every number independently; mismatches block the record. Anything unverifiable → skip college, substitute alternate (D-xx).
6. **`VERIFICATION_REPORT.md`:** per-college table of every field → source URL → table/page → retrieved date → SHA-256, plus gate results and a 5-item spot-check list for the user.
7. **GATE:** `python scripts/validate_data.py` exits 0 for all 10 records and the report is delivered. **I stop and wait for your sign-off before any app code.**

Downloads: I will fetch ~10–20 public NIRF/fee-circular/placement PDFs (a few MB each) from `nirfindia.org` and the institutes' own `.ac.in/.edu` sites into `data/sources/`. Approving this plan covers those downloads; I will not download from any other domain.

## Phase 2–7 — Application (starts only after the data gate)

**Architecture:** FastAPI (Python 3.12 via `uv`) serves `/api/*` and the built React app from one Render web service. SQLModel → SQLite locally, Postgres (`DATABASE_URL`) on Render for bookings, escrow ledger, deposits. Colleges are loaded from the verified JSON, not a DB.

```
backend/app/{main.py, config.py, models/, routers/, services/, engines/, llm/, integrations/, db.py}
backend/tests/   frontend/src/{pages,components,lib,i18n}   postman/   render.yaml   LICENSE(MIT)
```

| Phase | Days | Scope (requirement IDs) |
|---|---|---|
| 2 Backend core | 8–9 Nov | Dataset API + source badges (FR-05); deterministic engines: 4-yr cost, payback/Time-to-Debt-Freedom, EMI, per-semester deficit, fit tier Safe/Target/Reach, Alignment Score (FR-02/03/11); percentile→rank mapping; tests |
| 3 Frontend core | 9–10 Nov | Design tokens/layout from prototype, Smart Sentence, Truth Lens, Bento deck, **AG Grid Placement Truth Matrix** with denominator renderer, **AG Charts** career curve, EN/हिंदी, alignment survey + discussion guide (FR-01…04) |
| 4 Planning tools | 10–11 Nov | **Bryntum** admissions timeline + deadline countdowns, refund tracker + refund-letter generator, choice-filling drag/drop simulator with order-inversion alerts (FR-06/07/09) |
| 5 Payments & commerce | 10–11 Nov | PayPal Orders v2 + JS SDK v6 Smart Buttons/Pay Later, webhook handler, internal escrow ledger (funded → released), Payouts on "Confirm Session Completed", **Bryntum Scheduler** booking for the 4 programs, **Channel3** tech-kit with cached/mock fallback (FR-08/10) |
| 6 Agent | 11–12 Nov | Qwen3-4B client (OpenRouter/other, Ollama dev fallback); hybrid agent with fixed tool list (affordability, EMI compare, slots, create PayPal order via Agent Toolkit/MCP); Hindi keyword/regex layer before LLM; Copilot drawer (FR-01/11) |
| 7 Ship | 12–13 Nov | Render deploy via `render.yaml`, E2E smoke, README, MIT license, demo script + <3-min video outline; stretch in order: Postman collection → Zapier webhook → Elastic hybrid search (each with working fallback) (FR-12) |

Scope tiers if time runs short: P0 = data, Truth Matrix, Bento/Truth Lens, ROI, timeline, PayPal booking+payout, tech kit, Render; P1 = agent, alignment matrix, simulator, refund tracker; P2 = Elastic, Zapier, Postman.

## Conflicts in the source docs to record in `decisions.md`
1. **Payback maths:** prototype's "8.2 months" for ₹10.6L equals cost ÷ *gross* monthly pay; BRD says *disposable* salary. Default: post-tax in-hand minus living costs, assumptions shown in UI and parameterised; gross shown as a secondary figure. Prototype numbers are placeholders.
2. **Seat-deposit window:** BRD/prototype say 96 h, UX spec says 72 h; prototype dates (Dec 20–24) and "UGC cutoff Jan 15, 2027" are unsourced. Verify against JoSAA/UGC notices; label timeline dates "indicative, based on the latest published cycle" with citation.
3. **"Escrow":** PayPal has no escrow product. Implement as capture into the platform sandbox merchant account + internal ledger, release via Payouts API on completion. Disclose in UI.
4. **Currency/Pay Later:** Pay Later is unavailable for INR/India; use USD with a US sandbox buyer and Business account; fixed documented INR→USD rate.
5. **Eligible-students definition** (manual §3 Step 2): admitted-in-time minus direct higher-studies; one formula, applied consistently.
6. **JEE percentile → rank** needed for fit tiers: derived from NTA candidate counts for the cited year; method and source recorded.
7. **Qwen3-4B limits:** numbers never come from the LLM; JSON-schema-constrained outputs; deterministic fallbacks so the demo works with the LLM down.
8. **Bryntum/AG Grid licensing:** Bryntum via trial/sponsor-provided registry access; AG Grid Community + Charts unless the prize requires Enterprise.

## Credentials / licences needed (you provide; I never see them in chat — they go in `.env`)
| # | Service | What I need | Needed by |
|---|---|---|---|
| 1 | **PayPal Developer** (sandbox) | REST app **Client ID + Secret**; sandbox **Business** (US) + **Personal** (US) test accounts; Payouts enabled on the Business account; **Webhook ID** (needs public URL: Render, or ngrok/cloudflared locally) | Phase 5 |
| 2 | **Channel3** | API key (hackathon sponsor portal) | Phase 5 |
| 3 | **Qwen hosted API** | API key + exact model slug for Qwen3-4B on OpenRouter / Together / DashScope / HF (tell me which provider you can access) | Phase 6 |
| 4 | **Bryntum** | Trial/sponsor registry credentials for `npm.bryntum.com` (Scheduler, Gantt/Timeline) and any licence key | Phase 3–4 |
| 5 | **Render** | Account, hackathon credit code applied, GitHub connected (API key only if you want me to use the CLI) | Phase 7 |
| 6 | **GitHub** | Account/org + OK to create a **public** repo with MIT licence (I will ask before any push) | Phase 7 |
| 7 | **AG Grid** | None for Community/Charts; Enterprise trial key only if needed | Phase 3 |
| 8 | Stretch — **Elastic Cloud** | Elasticsearch URL + API key | Phase 7 |
| 9 | Stretch — **Zapier** | Catch-hook URL (or MCP server URL) with a Zap that sends Calendar/Zoom invite | Phase 7 |
| 10 | Stretch — **Postman** | Account (and API key if you want me to publish the collection/monitor; otherwise I export JSON) | Phase 7 |
| – | NIRF / JoSAA / UGC / fee circulars | **No keys** (public) — needed for Phase 1 | now |

**To start Phase 1 I need no keys at all.** Credentials 1–4 are needed from Phase 3–6. Local tooling: `uv` and Node 26 are present; system Python is 3.9.6, so I will install Python 3.12 with `uv` into a project venv (no global changes).

## Verification (how we know each stage is done)
- **Docs:** all 7 files exist; `todo.md` covers every requirement ID; every FR/UX/DR/NFR/INT has an acceptance criterion.
- **Dataset gate:** `npm run validate:data` (→ Python) passes 6 gates for all records; second-pass independent re-read matches; `VERIFICATION_REPORT.md` reviewed and signed off by you.
- **Backend:** `pytest` — engine unit tests with hand-computed expected values; API contract tests; PayPal/Channel3/LLM mocked and live-sandbox modes.
- **Frontend:** dev-server run in the built-in browser; Truth Lens, grid sort/filter (<50 ms), Hindi toggle, Bryntum views checked via screenshots.
- **Payments:** full sandbox path: create order → approve → capture → ledger "funded" → confirm session → Payout → ledger "released"; webhook replay test.
- **Deploy:** public Render URL passes a smoke script; demo path rehearsed with all external services in both live and fallback mode.
