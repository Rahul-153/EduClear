# EduClear — Plan: simpler pages, student/parent views, more data (DRAFT, 2026-11-11)

Status: plan only. Nothing here is built. No code, data or `todo.md` entry was changed when this was written.
Deadline reminder: submissions close 12 Nov 2026, 12:00 pm PT, about 01:30 IST on 13 Nov (D-45).
Read with: `AGENT_MANUAL.md`, `decisions.md`, `DATA_PLAN_V2.md` (this plan reuses its rules and does not replace it).

---

## 1. Why this plan

Review of the running app on 2026-11-11:

- One page, about 5,000 px tall (6.5 screens), 11 stacked sections, 58 controls.
- Default profile (99.75 percentile) shows one filled card and two "No match in this tier" cards.
- Student tasks and parent tasks are mixed at the same level.
- Labels need explaining: "Truth Lens", "Safe anchor", "Intelligent Discovery • Live".
- The app shows 11 colleges, CSE only, OPEN seats only. Much more official data is already on disk but not shown (section 5).

---

## 2. Decisions needed before building

| # | Decision | Recommendation |
|---|---|---|
| Q1 | May a college appear with only some verified fields, under a visible label? (Open decision 3 in `DATA_PLAN_V2.md`.) | **DECIDED 2026-11-11 (user): yes, with labels** — **Fully audited**, **Partly verified**, **Cutoffs only** (D-49). Parts B and C are unblocked. |
| Q2 | Student and parent on one device, or two? | One device. Two devices need a share code and new backend work. |
| Q3 | Is a counsellor view in scope? | No. |
| Q4 | Approve fetching from `csab.nic.in` and `cetcell.mahacet.org`? (Agent manual: ask before new domains.) | Yes for CSAB (same body as JoSAA). MHT-CET after the deadline. |
| Q5 | For reserved categories, ask the student for their category rank? | Yes. It is printed on the scorecard and avoids any estimated mapping. |

---

## 3. Part A — Pages and views (frontend only)

### A1. Page split
Four pages, switched by hash (`#find`, `#cost`, `#apply`, `#help`). No router dependency. Copilot drawer stays on all pages.

| Page | Components moved there | Primary action |
|---|---|---|
| Find | `SmartSentence`, `BentoDeck`, `TruthMatrix` | Pick a college |
| Cost | `RoiPanel`, `TechKit`, `DepositTracker` | See 4-year cost and payback |
| Apply | `ChoiceSimulator`, `AdmissionsTimeline` | Check choice order and dates |
| Get help | `AlignmentSurvey`, `Sessions` (with `CheckoutPanel`) | Book a session |

Steps:
1. `App.tsx`: add `page` state read from `location.hash`, listen for `hashchange`, render only the active page's components. Shared state (`p`, `a`, `rec`, `selected`) stays in `App`.
2. `Header.tsx`: add a four-item nav (`<nav>` with `aria-current`). Keep logo and language toggle. Add the view switch (A2).
3. Move the Brochure/Audited toggle from `Header.tsx` into `TruthMatrix.tsx`'s card header. `BentoDeck` keeps reading the same `truth` prop.
4. "View ROI" on a card sets `selected` and navigates to `#cost`.
5. `styles.css`: nav styles only, using existing tokens.

### A2. Student and parent view
A two-option switch in the header, saved in `localStorage` (`educlear.view`), default Student. No login (D-32).

| | Student | Parent |
|---|---|---|
| Nav order | Find, Apply, Cost, Get help | Find, Cost, Get help, Apply |
| Deck card headline | Fit tier and closing rank | 4-year cost and debt-free clock |
| Alignment survey | Student column only | Parent column only; score shown when both are saved |
| Sessions | Slots visible, button reads "Ask a parent to book" | Full PayPal checkout |
| Copilot starter prompts | Cutoffs, choice order | Cost, EMI, refunds |

Steps:
1. `App.tsx`: `view` state, passed to `Header`, `BentoDeck`, `AlignmentSurvey`, `Sessions`, `Copilot`.
2. `BentoDeck.tsx`: swap which figure is the large one by `view`. Same data.
3. `AlignmentSurvey.tsx`: store each side's answers in `localStorage`; call `/api/alignment` when both exist. No backend change.
4. `Sessions.tsx`: hide `CheckoutPanel` in student view.
5. `Copilot.tsx`: two starter-prompt lists.

### A3. Simplifications
1. Rename labels in `i18n.ts` (en and hi): "Find colleges", "Safe / Good fit / Stretch", "Real placement numbers", "Brochure numbers / Audited numbers".
2. `BentoDeck.tsx`: when a tier is empty, do not render an empty card. Show one line under the deck that names what is missing (for example a JEE Advanced rank) and links to "More inputs".
3. Remove the "Intelligent Discovery • Live" eyebrow.

### A4. Verification for Part A
- `cd frontend && npm run build` passes.
- In the browser: each hash shows only its page; view switch survives reload; student view shows no PayPal button; parent view completes a mock-mode booking; Hindi toggle covers the new labels.
- `scripts/smoke.py` still passes (no API change).
- Page height on Find is under 2 screens at 1280 x 768.

---

## 4. Part B — Show the data already on disk

This is the largest gain for the least risk. Needs Q1 = yes.

### What exists today but is not in the app

| Asset | Where | Size | In app? |
|---|---|---|---|
| Fully audited records | `data/colleges/*.json` | 11 colleges | Yes |
| IIT research with field status | `data/sources/iit-*/research.json`, `data/iit_round_summary.md` | 20 IITs | No |
| Researched but excluded NITs and others | `data/sources/<id>/` | about 12 institutes | No |
| JoSAA archive | `data/evidence/josaa.sqlite` (git-ignored) | 504,210 rows, 2016 to 2025; 2025 alone has 72,183 rows from 128 institutes | No |

### B1. Slim cutoff table for the app
1. New script `scripts/export_cutoffs.py`: from `josaa.sqlite`, export 2025 final-round rows (all institutes, programmes, quotas, seat types, genders) to `data/cutoffs_2025.sqlite`. Target under 10 MB so it can be committed and shipped in the Docker image.
2. Record source round, row count and SHA-256 in `data/josaa_manifest.csv` terms already used (D-48).
3. Check: row count equals the count in `josaa.sqlite` for the same filter; the 11 existing records' cutoffs still match.

### B2. Backend
1. `backend/app/data.py`: loader for the slim table.
2. `services/recommend.py`: after the audited matches, add "cutoffs only" institutes reachable at the student's rank. Each carries `data_level: "cutoffs_only"` and no cost, placement or ROI fields (null, never estimated).
3. `Profile` gains optional `branch`, `seat_type`, `gender`, `category_rank`. Defaults keep today's behaviour (CSE, OPEN, Gender-Neutral).
4. Fit tiers for non-OPEN seat types use `category_rank` as entered (Q5). If absent, those rows go to `needs_more_input`.
5. Tests: defaults return the same audited matches as now; a 92 percentile profile returns cutoff-only options; no cutoff-only row has a money field.

### B3. Frontend
1. `SourceBadge`-style label on every card and matrix row: Fully audited / Partly verified / Cutoffs only.
2. Cutoff-only rows show closing rank and a JoSAA source link; cost and placement cells read "Not yet verified".
3. Deck cards stay reserved for Fully audited and Partly verified colleges; cutoff-only institutes appear in a list below.
4. `SmartSentence`: branch selector fed from the table; category and gender under "More inputs".

### B4. Partly verified IITs
1. Extend `scripts/assemble_records.py` to build records from `research.json` where status is V or D; C uses the lower figure (D-23); missing fields stay null with `not_published`.
2. `scripts/validate_data.py`: gates run only on fields that exist; a null with a recorded reason passes.
3. Second-pass re-read of each new record before it ships, as for earlier waves.

Expected effect: the gap map shows 0 audited colleges reachable at 92 percentile and below, against 20 institutes in the JoSAA table at 92 and 9 at 85. Part B makes those visible.

---

## 5. Part C — New data found by search (2026-11-11)

Official sources only may enter the dataset. Aggregator pages below are leads, not sources.

| # | Source | What it adds | Status from search | Effort |
|---|---|---|---|---|
| C1 | CSAB special rounds 2025, `csab.nic.in/news-events-special/` | Opening and closing ranks after JoSAA round 6 for NITs, IIITs, GFTIs; extends reach to lower ranks | Official page lists a "DASA and CSAB Special Round 2025 Opening and Closing Ranks" document. Contents not opened. | Low: one document, same shape as JoSAA |
| C2 | NIRF 2025 data PDFs for every ranked engineering institute | UG 4-year graduating, placed, median salary, higher studies for roughly 100 to 200 institutes | Ranking page already saved at `data/sources/nirf-2025-engineering-ranking.html`; fetch method known (`DATA_PLAN_V2.md` section 3) | Medium: automated fetch and table parse, review queue for misreads |
| C3 | NIRF 2026 | Newer placement batch (2024-25) | Unconfirmed. Most pages say not released; one says released 12 Aug 2026. Check `nirfindia.org` directly before relying on either. | Unknown |
| C4 | MHT-CET CAP 2025, `cetcell.mahacet.org` | Maharashtra state seats; three CAP rounds in 2025 | Official site named by secondary pages; PDFs not opened | Medium: new parser |
| C5 | KCET (KEA), JAC Delhi, WBJEE | Other state seats | Search did not reach official cutoff files | Needs a separate look per portal |
| C6 | AICTE mandatory disclosures | Fees and placement per college | No central dataset found; published per college and reported as inconsistent | Not recommended |

Order: C1, then C2, then C3 check, then C4. C2 turns many "Cutoffs only" institutes into "Partly verified" (placement known, fees pending). Fees and highest package still need per-institute documents (`DATA_PLAN_V2.md` phase 4).

Rules that stay: zero synthetic values, D-09, D-19 to D-23, hashes and snapshots for every source, second-pass re-read, one request per second per host.

---

## 6. Order of work

| Step | Part | When | Risk to live app |
|---|---|---|---|
| 1 | A1 to A4 (pages, views, labels) | Before deadline, about half a day | Low; frontend only |
| 2 | B1 to B3 (cutoff-only tier) | Before deadline only if step 1 is done and verified with time left | Medium; touches `recommend` |
| 3 | B4 (partly verified IITs) | After deadline | Medium; validator change |
| 4 | C1 (CSAB) | After deadline | Low |
| 5 | C2, C3 (NIRF at scale) | After deadline | Low |
| 6 | C4, C5 (state CETs) | After deadline | Low |

Each step ends with: tests and `npm run validate:data` pass, browser check, `todo.md` ticked with evidence, decisions appended to `decisions.md`.

Suggested `todo.md` entries when work starts: T-10.01 page split · T-10.02 view switch · T-10.03 labels and empty tiers · T-10.04 slim cutoff export · T-10.05 recommend with data levels · T-10.06 data-level labels in UI · T-10.07 partly verified IITs · T-10.08 CSAB 2025 · T-10.09 NIRF 2025 at scale · T-10.10 MHT-CET.

---

## 7. Competitor positioning (for README and demo script, not the app)

Compared with Collegedunia and Shiksha (from general knowledge; not re-checked on their sites):

| | Collegedunia / Shiksha | EduClear |
|---|---|---|
| Who pays | Colleges | The family; no commission from colleges |
| Placement figures | Highest and average package as reported | Median pay and placed ÷ eligible, with source and hash |
| Cost | Fee tables | 4-year total cost and payback on disposable income |
| Counselling | Free, college-funded | Paid; money held until the session is confirmed |
| Coverage | Very wide | Narrow today; Part B and C widen cutoffs to about 128 institutes |

Position: a decision tool for the final shortlist, not a directory. In the app, say "commission-funded portals" rather than naming companies.

---

## 8. Sources for section 5

- https://csab.nic.in/news-events-special/
- https://engineering.careers360.com/articles/csab-or-cr-2025 (lead only)
- https://engineering.careers360.com/articles/mht-cet-cutoff (lead only; names cetcell.mahacet.org)
- https://www.collegedekho.com/amp/news/nirf-ranking-2026-release-date-november-category-wise-list-80389/ (lead only; says NIRF 2026 due November 2026)
- https://distanceeducationschool.com/?p=152006 (lead only; says NIRF 2026 released 12 Aug 2026; uncorroborated)
- https://www.careers360.com/articles/aicte-regulator-which-doesnt-share-data (lead only)
