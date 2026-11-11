# EduClear — Data Plan v2 (DRAFT for approval, 2026-11-09)

Goal: official, source-linked data for every engineering branch and every MBA/PGDM programme, across every exam, category, quota, gender, round and year that the official bodies publish, so that any student profile gets real options. Nothing in this plan is executed until approved.

Hard truth first: the submission deadline is 12 Nov 2026, 12:00 pm PT (D-45). This plan is weeks of work, not days. Section 9 says what can safely land before the deadline.

---

## 1. What went wrong before (and the fix for each)

| # | Mistake | Evidence | Fix in v2 |
|---|---|---|---|
| 1 | Evidence deleted by `git filter-branch`; reports depended on files that were lost | D-40, `make_report.py` needs `verification.json` | Content-addressed evidence store, read-only, backed up to a second location, manifest of hashes committed to git. Reports generated from records + manifest only. No history rewrites. |
| 2 | Colleges picked by name/prestige, one at a time. 11 of 15 attempted were skipped, and the 7 original ones were all too selective | D-26, this session | Pick what to research from a **coverage gap map** computed from the cutoff data (section 5), not from a wish list. |
| 3 | All-or-nothing record: one weak field (a mess advance, a CTC label) killed a whole college | Durgapur, MNNIT, Hamirpur, SVNIT, Jamshedpur | **Field-level status**: every value is `verified`, `derived`, `conflict` or `not_published`. A college can ship with honest gaps; a gap is never filled. |
| 4 | Only one slice stored: CSE, OPEN, one round, one year, one room type | `scrape_josaa.py` filters; schema has one cutoff string | Normalised tables keyed by institute × programme × year × round × quota × seat type × gender (section 4). Scrape the whole archive, not one branch. |
| 5 | Hardest figures were found last: fees from scanned circulars, hostel/mess periods, headline CTC season labels | Silchar, SVNIT, Patna, Raipur | Extraction rules and a **season/period glossary** written before collection (section 6). Scans always get two independent reads. |
| 6 | Verification bolted on at the end by one agent; it died three times on API errors and left nothing on disk | verifier retries | Verification built into the pipeline: each job writes its result to disk, is resumable and idempotent, small batches. No result lives only in a conversation. |
| 7 | Access questions asked late: NIRF 403, Google Drive, broken TLS | NIRF block, Srinagar/NSUT | One up-front **fetch policy** and domain allowlist for you to approve (section 7). |
| 8 | Tests and docs hard-coded "7 colleges" | two tests failed | Counts derived from data; tests assert invariants, not counts. |
| 9 | Wrong form code (`3IT`) in my own JoSAA scan; IIIT/GFTI never scraped | scan output | Scraper enumerates dropdown values at run time and logs any institute/branch it cannot reach. |
| 10 | Recommendation engine and dataset were built for OPEN/CSE only, so empty decks at 98 percentile and below | coverage table | Coverage is measured per percentile × category × home state × branch group, before and after every wave. |

---

## 2. Scope: what "every permutation" means, and what is out of reach

**Engineering dimensions** (official sources publish these):
- Exam: JEE Advanced, JEE Main (via JoSAA/CSAB), BITSAT, state CETs (MHT-CET, KCET, TNEA, WBJEE, UPTAC, HSTES, REAP, KEAM, TS/AP EAMCET, OJEE, BCECE, JAC Delhi, etc.), private-university tests (VITEEE, SRMJEEE, etc.).
- Category: OPEN, EWS, OBC-NCL, SC, ST, and each with PwD.
- Gender: Gender-Neutral, Female-only.
- Quota: AI, HS, OS, GO, JK, LA; state quotas for CETs.
- Round and year: all rounds, 2016 to 2025 (JoSAA archive depth).
- Branch: every programme the institute lists (CSE, IT, ECE, EE, ME, Civil, Chemical, Metallurgy, Aerospace, Biotech, Production, Instrumentation, Mining, Textile, Ceramic, Engineering Physics, Maths and Computing, AI/DS and the rest), plus duration and degree (B.Tech, dual degree, integrated).

**MBA dimensions:**
- Exam: CAT, XAT, GMAT, CMAT, SNAP, NMAT, MAT, state tests.
- Programme: 2-year PGDM/MBA, 1-year executive (flagged separately), specialisation tracks (Finance, Marketing, Operations, Analytics, HR, Consulting) where an institute publishes them.
- Category and gender weightage where published.

**Not obtainable from official sources, so the plan says so up front and stores `not_published`:**
- Branch-wise placement for most institutes (NIRF reports UG 4-year as a whole; only some institutes publish by branch).
- Final MBA admission cutoffs for most B-schools (IIMs publish shortlisting criteria and category weightages, rarely final percentiles; some, such as FMS Delhi, publish them).
- Per-branch fees (NIT/IIT B.Tech tuition is branch-independent; stored once and marked `applies_to: all B.Tech`).
- Percentile-to-rank: computed by the engine from NTA's published candidate counts (D-10), never stored as data.

---

## 3. Source map (official only)

| Domain | Source | What it gives | Access |
|---|---|---|---|
| Engineering cutoffs, JoSAA institutes | JoSAA opening/closing archive | Every institute (IIT, NIT, IIIT, GFTI) × programme × quota × seat type × gender × round × year | Official ASP.NET form; structured HTML. Works with plain `requests` (confirmed this session). |
| CSAB special rounds | csab.nic.in | Extra rounds for NITs/IIITs/GFTIs | Same pattern |
| State and private counselling | State CET portals, each institute's own cutoff page | Cutoffs for non-JoSAA seats | Per-portal parser, one at a time |
| Placement (engineering) | NIRF DCS PDFs (Engineering, plus Overall and University bands) | UG 4-year batch, placed, median salary, higher studies, intake, accreditation text | `nirfindia.org/nirfpdfcdn/...`; plain `requests` works, `curl` with a short user-agent gets 403 |
| Placement (MBA) | NIRF Management DCS; each IIM/B-school placement report | PG 2-year placed, median, highest | Institute PDFs |
| Fees | Institute fee circulars (`.ac.in`/`.edu`), hostel and mess notices | Tuition, line items, hostel, mess | Mostly scanned PDFs |
| Highest package | Institute's own annual report/placement report, same season | Headline CTC | PDFs, sometimes JS pages |
| Accreditation | nbaind.org, naac.gov.in, institute pages | NBA/NAAC status and validity | Per-programme for NBA |
| Living cost | DoE 7th CPC HRA order (2017) | X/Y/Z city class | One document, already read |
| Refund and admissions rules | UGC, JoSAA business rules | Deposit windows | Already collected |

---

## 4. New data model (v2)

Normalised tables (SQLite or Parquet in git for the small ones, evidence store outside git):

- `institutes(id, name, type, city, state, hra_class, region, nirf_ids...)`
- `programmes(id, institute_id, name, degree, duration_years, stream, branch_group)`
- `cutoffs(institute_id, programme_id, exam, year, round, quota, seat_type, gender, opening, closing, source_id)`
- `fees(institute_id, programme_id|null, academic_year, category, item, amount, period {one_time|per_sem|per_year}, refundable, source_id, locator, read_method {text|scan_dual_read})`
- `placements(institute_id, programme_id|null, batch, level {UG4|PG2}, graduating, higher_studies, placed, median, highest, definitions, source_id, locator)`
- `accreditations(institute_id, programme_id|null, body, valid_from, valid_to, source_id)`
- `sources(id, url, retrieved_at, sha256, kind, store_path)`

Every numeric cell has a status column: `verified | derived | conflict | not_published`, plus the source and locator. The old `data/colleges/*.json` records become a **generated view** over these tables, so the existing app, validator and tests keep working while the data underneath widens.

Rules carried over unchanged (they were right): zero-synthetic; D-09 eligible = graduating minus higher studies; D-19 fee accounting; D-20 NIRF 2025 batch 2023-24; D-21 cutoffs stored as published; D-22/D-23 same-season CTC, lower figure on conflict. New: a conflict or a missing figure lowers that field's status; it does not remove the college.

---

## 5. Order of work: coverage-driven, cheapest and most official first

**Phase 0 — Safety and setup (half a day)**
- Create the immutable evidence store, back up `data/sources/` now, commit a hash manifest. Write the fetch policy and glossary (sections 6 and 7). Get your approvals.

**Phase 1 — Full JoSAA archive (1 to 2 days, fully automated, official, structured)**
- Scrape every institute, programme, quota, seat type, gender, round, for 2016 to 2025. Log unreachable combinations instead of failing silently. Store raw HTML in the evidence store, parsed rows in `cutoffs`.
- Output: every engineering stream at every JoSAA institute, with trends. This alone answers "all branches, all categories, all quotas" for roughly 120 institutes.

**Phase 2 — Coverage gap map (hours)**
- From `cutoffs`, compute for each percentile bucket (use the app's dropdown plus finer steps) × category × home state × branch group how many institutes are reachable. Rank institutes by how many empty cells they would fill. This decides who gets the expensive research in Phase 4.

**Phase 3 — NIRF at scale (1 to 2 days, mostly automated)**
- Fetch every engineering and management DCS PDF that NIRF 2025 lists, parse the UG 4-year and PG 2-year placement tables deterministically with a layout parser plus a sanity check (placed ≤ eligible ≤ graduated). Anything that does not parse goes to a review queue, not into the data.

**Phase 4 — Institute documents for the gap-ranked list (the slow part)**
- Fee circular, hostel/mess, same-season highest package, accreditation. Work in waves of 5 institutes. Every scanned figure gets two independent reads that must agree. Colleges ship with whatever verified fields exist; the rest stay `not_published`.

**Phase 5 — Non-JoSAA admissions (state CETs, BITSAT, private universities)**
- One portal at a time, ordered by how many gap cells they fill and how parseable the official cutoff is.

**Phase 6 — MBA (parallel track, starts after Phase 3)**
- NIRF Management ranked list, IIM and top B-school fee and placement PDFs, CAT/XAT/GMAT cutoff or shortlisting criteria where published. MBA has a different schema shape (2-year cost multiplier, specialisation placement, entrance-percentile bands), so it gets its own validator gates.

**Phase 7 — Engine and app follow-through (out of data scope, listed so it is not forgotten)**
- The engine reads OPEN/CSE only. To use the new dimensions it needs category, gender, branch and home-state inputs, and a "data not published" display. This is a separate approved task.

---

## 6. Extraction rules (written once, applied everywhere)

- **Season labels:** "2023-24 season" = batch graduating in 2024. A page labelled by a single year (e.g. "2024 Batch") is accepted only with a second document that fixes the convention; otherwise the field is `conflict`.
- **Periods:** a fee column counts as per-semester or per-year only if the document says so. If it does not, the field is `not_published`, never inferred (this is what blocked SVNIT).
- **Mess/hostel:** published advances count; an odd-semester-only figure is not doubled. Room type is recorded.
- **Rounding:** all money is integer rupees; fractional results are stored as exact integers of the 4-year total, not rounded per year.
- **Scans:** render at 200 dpi, read by two independent readers, compare to printed totals. Disagreement or no printed total means a human spot-check flag.
- **Conflicts:** keep both figures with sources in the table; the app shows the lower per D-23.
- **Currency of documents:** use the newest circular that applies; if the newest is older than the batch, store the date and flag it (Patna).

---

## 7. Fetch policy and approvals needed from you (once, up front)

1. Scripted fetch of `nirfindia.org` with the plain `requests` user-agent used by the project (you approved this on 2026-11-09). No header spoofing beyond that, no captcha handling.
2. Domains outside `plan.md`'s list: `drive.google.com` (many NIT/NSUT documents live there), Maharashtra and other state CET portals, `nbaind.org`, `naac.gov.in`. Approve per domain.
3. Sites with broken TLS chains (NSUT, IIIT Delhi, NIT Raipur): allow fetching the missing intermediate from the certificate's own AIA URL and verifying with it, never disabling verification. Or skip those sites.
4. Rate limits: one request per second per host, resumable, with a log of every URL and hash.

---

## 8. Quality gates (extended)

- Existing 6 gates and the D-09 gate, applied wherever the inputs exist.
- New: row-count checks per JoSAA page (expected vs parsed), closing ≥ opening, rank monotonicity across rounds, no duplicate keys.
- New: every non-null value must have a source and a hash that exists in the manifest; the validator re-hashes the store.
- New: two-reader agreement recorded for every scanned figure.
- New: a coverage report generated on every run, so progress is measured in filled cells, not colleges.
- Tests assert invariants (all records valid, every id unique), never counts.

---

## 9. Timeline reality and options

Today is 9 Nov; submission closes 12 Nov 12:00 pm PT.

- **Option A: freeze now.** Ship the 11 verified colleges. Run v2 after the deadline. No risk to the live app.
- **Option B: Phase 0, 1 and 2 before the deadline.** The JoSAA archive scrape is automated and official, so it is feasible in the window. It fills `cutoffs` for all branches and categories. It does **not** by itself change what the app shows, because placement and fees would still be missing for most institutes. Showing cutoff-only colleges would need a UI label ("fees and placement not yet verified") and your decision, since it relaxes today's "complete record only" rule.
- **Option C: full plan.** Not achievable by the deadline; it is a multi-week effort. Treat it as the post-hackathon roadmap.

Recommendation: A for the live app, plus Phase 0 to 2 as a side track that touches only new tables, so nothing in the shipped app can break.

---

## 10. Open decisions for you

1. Which option (A, B or C) for the deadline?
2. Approve the domain list and TLS handling in section 7?
3. Is a college with some `not_published` fields allowed into the app (with a visible label), or must it stay all-or-nothing?
4. MBA scope: only 2-year PGDM/MBA, or also 1-year and executive programmes?
5. State CET and private-university cutoffs: include, or JoSAA-only for the first release?
