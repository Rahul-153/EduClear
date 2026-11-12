# EduClear — Data gaps as of 2026-11-11

Measured on the code and data in `main` at commit `8cebc25` (live on https://educlear.onrender.com). Numbers below were computed from the shipped files, not estimated. Rules that stay: zero-synthetic, every figure from an official source with URL, date and hash, gaps stored as "not published" and never filled.

## 1. What exists today

| Level | What is in it | Institutes |
|---|---|---|
| **Fully audited** | Cost, NIRF placement, headline package, accreditation, cutoff. CSE only, general category, batch 2023-24 | 11: DTU Delhi, BITS Pilani, IIT Hyderabad, IIT BHU, IIT Guwahati, MNIT Jaipur, NIT Calicut, NIT Kurukshetra, NIT Silchar, NIT Patna, NIT Raipur |
| **Partly verified** | NIRF 2025 placement row only (graduated, higher studies, placed, median). No cost | 19 IITs (all researched IITs except IIT Goa) |
| **Cutoffs only** | JoSAA 2025 round 6 closing rank. No cost, no placement | 100 of 128 JoSAA institutes: 47 GFTIs, 26 IIITs, 26 NITs, 1 IIT (Goa) |
| **Nothing** | Not in the app at all | Every institute outside JoSAA, except DTU and BITS; all MBA |

JoSAA 2025 round 6 has 128 institutes and 11,944 rows. Of those, 9 audited and 19 partial; DTU and BITS are audited but not in JoSAA.

## 2. What a student actually gets (CSE, budget ₹35 L)

| Percentile | Audited deck cards filled (of 3) | Cutoff-only CSE options (IITs need a JEE Advanced rank, not counted) |
|---|---|---|
| 99.9 | 1 | 80 |
| 99.75 | 1 | 78 |
| 99.5 | 2 | 75 |
| 99 | 2 | 69 |
| 98 | 0 | 56 |
| 97 | 0 | 44 |
| 96 | 0 | 30 |
| 95 | 0 | 24 |
| 94.2 | 0 | 19 |
| 92 | 0 | 2 |
| 90 | 0 | 0 |
| 85 | 0 | 0 |

**Reading this:** at 98 percentile and below the audited deck is empty, and from 92 down even the cutoff list is nearly empty, because almost no JoSAA CSE seat closes beyond rank 1,00,000 (92 percentile is about rank 1,18,000). A student at 90 percentile or lower gets no CSE option from JoSAA. Other branches reach a little lower (the gap map counts 53 programmes of all branches reachable at 90 percentile, mostly in small institutes), but those have no cost or placement data. This is the biggest gap in the product, and more JoSAA data does not fix it.

## 3. Gaps, by severity

### Critical (changes what a family can do)

| # | Gap | Detail | Fix | Effort |
|---|---|---|---|---|
| G1 | **Nothing below about 92 percentile** | State CET seats, private universities and non-JoSAA colleges hold the options for most students. Zero are in the app | State portals one at a time (MHT-CET first, official CAP PDFs), then private universities that publish cutoffs | Weeks |
| G2 | **100 institutes have no cost or placement** | Cutoff-only rows show "Not yet verified". Budget and region filters do not apply to them, so a family can see an option that is out of budget | NIRF 2025 PDFs for every ranked engineering institute (placement), then fee circulars in gap-ranked order (plan C2, phase 4) | Placement 1 to 2 days; fees weeks |
| G3 | **No MBA data** | Dropdown shows "MBA (data pending)". The BRD targets UG and PG | Separate track: NIRF Management, IIM and B-school PDFs, CAT/XAT cutoffs where published | Weeks |
| G4 | **Cost missing for all 19 partly verified IITs** | Tuition derived from per-semester figures for most; mandatory fees conflicting (5 IITs), hostel missing (2), mess missing or conflicting (3) | Resolve per IIT and apply D-19; some need the institute to publish more | Days per wave, blocked by documents |

### High

| # | Gap | Detail |
|---|---|---|
| G5 | **Only CSE has cost and placement** | Other branches show cutoff-only rows and no audited cards. NIRF placement is the whole UG 4-year batch, not by branch. Branch-wise placement was found for 14 of the 20 researched IITs but is not in the app |
| G6 | **Category, gender and quota coverage is thin** | Audited cards use OPEN seats whatever the student selects. IIT rows need an Advanced rank and OPEN seats only. Home-state seats are not applied for the 100 cutoff-only institutes (no institute state in the table); GO, JK and LA quotas skipped; PwD ignored |
| G7 | **Headline package missing for 13 of 20 IITs**, conflicting for 3 | IIT Bombay, Delhi and Madras publish none for 2023-24 (policy or other season). Brochure-vs-audited comparison is impossible for them |
| G8 | **Accreditation not found for 19 of 20 IITs** | Absence from the NBA list is not a statement of non-accreditation. NAAC portal timed out |
| G9 | **One year of cutoffs shown** | 2025 round 6 only. The archive on disk has 504,210 rows for 2016 to 2025, all rounds, opening ranks included, none of it used (no trend, no "closed higher last year") |
| G10 | **CSAB special rounds and 2026 cycle missing** | Extend reach to lower ranks after JoSAA round 6. Official CSAB page lists the 2025 document; contents not read |

### Medium

| # | Gap | Detail |
|---|---|---|
| G11 | **Placement batch is a year old** | NIRF 2025 data covers the batch graduating 2023-24. NIRF 2026 status is unconfirmed (sources conflict) |
| G12 | **IIT Goa has no staged NIRF row**, so it stays cutoff-only although a verified row exists in its research notes | Use the research value or re-stage; small |
| G13 | **Percentile to rank is a model** | Uses 14,75,103 candidates, taken from a second-hand report of the NTA notice (D-28). Fit tiers use fixed margins. No per-session normalisation, no category percentile mapping |
| G14 | **Fee periods are mixed** | Circulars range from AY 2025-26 to 2026-27; some amounts are per semester doubled, some single-semester (Gandhinagar, Tirupati mess). Flagged in notes, not normalised in the app |
| G15 | **Living cost is an assumption** | Midpoint of the 7th CPC HRA band by city class (D-19); class itself derived for 4 IITs |
| G16 | **Three IITs show 100% placed** | Patna, Roorkee, Bombay: placed equals eligible exactly, as NIRF-submitted. Not cross-checked against the institutes' own reports |

### Operational data (not college data)

| # | Gap | Detail |
|---|---|---|
| G17 | Counsellor is a demo profile (D-33). No real, vetted counsellors | Needs verification before any real launch |
| G18 | Tech-kit prices come from Channel3 live or labelled sample fallback; cached 10 minutes | Fine for demo; not a price guarantee |
| G19 | Admissions timeline dates are "indicative, latest published cycle" (D-03, D-31) | JoSAA 2026 dates sourced; JEE Main 2027 and state counselling not covered |
| G20 | Hindi covers headings and controls; long notes, survey prompts and cutoff table headers partly English | |

### Trust and audit gaps

| # | Gap | Detail |
|---|---|---|
| G21 | **Evidence folder was lost once (D-40)** | 47 files re-downloaded, 39 identical, 6 dynamic pages differ byte-wise; per-field verification notes and excluded colleges' documents are gone. `data/sources/` is git-ignored, so the audit trail exists on one machine only |
| G22 | **Second-pass checks are lighter for newer data** | Partly verified IITs rely on one PDF-text parse plus the staged row, not a second agent. The 4 wave-3 NITs had an independent agent pass |
| G23 | **Backups** | No second copy of `data/evidence/` (115 MB) and `data/sources/` is recorded anywhere in the repo |

## 4. Colleges tried and skipped (reasons on record)

| College | Reason |
|---|---|
| IIT Bombay, Delhi, Madras (as full records) | No same-season 2023-24 highest package (D-22) |
| NIT Trichy, Surathkal | No headline package published |
| NIT Warangal, IIIT Hyderabad, VIT Vellore | Hostel and mess not derivable; annual fees not published; no official cutoff (D-24) |
| IIT Roorkee, Kanpur, Kharagpur | No 2023-24 highest package (D-26); Kharagpur later found 1.69 crore institute-wide with a 1.68 crore conflict, undecided |
| NIT Rourkela, VNIT Nagpur, Thapar, SRM, Manipal, Amrita | Drive-only documents, 2022-23 only, no cutoff, undated figures |
| Jadavpur, KIIT, IIIT Delhi, NSUT, NIT Srinagar | Site blocks or TLS errors from automated fetch |
| NIT Durgapur, MNNIT Allahabad, NIT Jalandhar, NIT Hamirpur, MANIT Bhopal | Mess or fee items missing, ambiguous season labels, JS-only data (D-47) |
| NIT Jamshedpur, SVNIT Surat | Researched and skipped; fee periods could not be inferred (see `DATA_PLAN_V2.md` section 1); documents in `data/sources/` |

Under D-49 most of these can now appear as Partly verified or Cutoffs only; the NITs among them already appear as Cutoffs only.

## 5. Recommended order to close gaps

| Order | Action | Closes |
|---|---|---|
| 1 | NIRF 2025 placement for all ranked engineering institutes (plan C2) | G2 (placement), G5 partly, G12 |
| 2 | CSAB 2025 special rounds into the cutoff table (plan C1; needs your OK for csab.nic.in) | G10, extends reach slightly |
| 3 | Use the 2016 to 2025 archive for a trend column | G9 |
| 4 | MHT-CET 2025 CAP rounds | G1 partly |
| 5 | Fee waves for the highest gap-ranked NITs and IIITs | G2 (cost), G4 |
| 6 | Make budget filter honest: hide or flag cutoff-only rows when a budget is set | G2 UX, no new data |
| 7 | Back up `data/evidence/` and `data/sources/` to a second location | G21, G23 |
| 8 | MBA track | G3 |

Step 6 and step 7 need no new data and can be done first.

## 6. Questions for you

1. Which matters more next: reaching lower percentiles (G1: state CETs) or deepening the colleges already shown (G2 to G4)?
2. Is MBA in scope for the next release or after?
3. May I fetch from `csab.nic.in` and `cetcell.mahacet.org` (agent manual: ask before new domains)?
4. Kharagpur headline package: use 1.68 crore (lower figure, D-23) or leave it unpublished?
