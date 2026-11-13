# Plan — Round-by-round counselling co-pilot (Phase 16)

Written 2026-11-13. Status: Stages 1 and 2 built the same day (T-16.01 to T-16.07, D-66); Stages 3 to 5 open. Tasks are T-16.xx in `todo.md`.

## 1. What it is

After each JoSAA round the family tells EduClear what happened (round number, the seat allotted or "no seat", their rank and category, the choices they listed above that seat). EduClear answers three questions:

1. **Can a higher choice still open up?** For each higher choice: how far its closing rank moved from this round to the final round in past years, and in how many of those years it reached the student's rank.
2. **Freeze, float or slide?** The option that fits the student's own list, with the official rule quoted beside it.
3. **What money is at risk, and by when?** Seat acceptance fee paid, the deduction on withdrawal, the last withdrawal date, and any institute deposit already in the Deposit tracker.

Why this is the differentiator: paid predictors (Careers360 ₹499, PW ₹199) stop when the choice list is exported. Nobody shows round-to-round history next to the refund money, for parent and student together.

## 2. What already exists and is reused

| Piece | Where | Used for |
|---|---|---|
| Round-wise closing ranks 2016-2025, all rounds (504,210 rows) | `data/evidence/josaa.sqlite` (git-ignored, 92 MB) | History of round-to-final movement |
| Seat matching by branch, quota, seat type, gender | `services/cutoff_options.py` | Finding the right row for a student |
| Percentile to rank, tier margins | `engines/fit.py`, `engines/assumptions.py` | Rank basis |
| Order-inversion check | `engines/choice.py` | Warn if the list above the seat is badly ordered |
| Round dates, withdrawal windows, seat acceptance fee rule | `data/admissions/timeline.json` | Deadlines and money at risk |
| UGC refund tiers | `engines/refund.py`, `Deposit` table | Institute deposit at risk |
| Copilot tools, EN+HI templates | `services/agent.py` | A `round_advice` tool |
| Family accounts, parent/student roles | `routers/auth.py`, `db.py` | Saving the season per family |

Sample of the signal (JoSAA 2025, NIT Calicut, CSE 4-year, Other State, OPEN, Gender-Neutral): closing rank 4,678 in round 1, then 4,846, 4,886, 4,957, 4,966 and 5,222 in round 6. A student at rank 5,000 had no seat there in round 1 and had one by round 6.

## 3. Rules the build must keep

- **No predictions and no invented numbers** (manual section 4). The output is history: "in 4 of the last 5 years the final closing rank was at or beyond your rank". Never "you will get it", never a probability.
- **Freeze / float / slide and fee rules come from a sourced file**, extracted from the saved JoSAA 2026 Business Rules (`data/sources/_admissions/josaa2026_business_rules.txt`) with clause locators, the same way `timeline.json` is built. Nothing is written from memory.
- **The model never chooses the action or produces a number.** A deterministic engine does; the model may only route the question to the tool.
- **A year is used only if the exact programme name, quota, seat type and gender match.** Missing years are shown as missing, not filled.
- **Known gaps are stated on screen:** 2024 has rounds 1-5 only in the archive; 2026 had 5 rounds and 2025 had 6, so the comparison is "this round to the last published round"; CSAB special rounds are out of scope until T-10.08.

## 4. Stages

### Stage 1 — Data and engine (offline, testable)
- **T-16.01 Slim round-history export.** `scripts/export_round_history.py` reads the evidence archive and writes `data/round_history.sqlite`: one row per (year, institute, programme, quota, seat type, gender) with the closing rank of each round. Only 4-year programmes in the five branch groups, last 5 years. Check: row counts against `data/josaa_manifest.csv`, three raw rows spot-checked, file size recorded (must be small enough to commit and copy in the Dockerfile).
- **T-16.02 Sourced JoSAA rules file.** `data/admissions/josaa_rules.json`: definitions of freeze, float, slide, what happens to the old seat on upgrade, withdrawal rule and deduction, with clause, page and snapshot for each. Check: second-pass re-read of every clause against the saved text.
- **T-16.03 Round engine.** `engines/rounds.py`:
  - `movement(seat, round, rank)` returns per year the closing rank at that round and at the final round, and whether the final reached the rank.
  - `advise(allotted, higher_choices, round, rank)` returns the action by rule: no higher choice wanted gives freeze; higher choices only in the same institute give slide; otherwise float. Each higher choice carries its history line. If no seat is allotted, it returns the history for every listed choice and the next-round and CSAB dates.
  - `money_at_risk(category, round, today)` from the fee rule, withdrawal windows and the family's deposits.
  - Check: hand-computed tests (the Calicut row above), missing-year test, no-seat test.
- **T-16.04 Backtest.** A test replays 2025: using 2021-2024 history only, for each seat and round, compare "reached in most past years" with what 2025 actually did. The result is reported as a count in the test output and in this file. It is a measurement, not a pass mark, and it decides the wording in the UI.

### Stage 2 — API and screen
- **T-16.05 `POST /api/rounds/advise`** (rate-limited like the other tools) and `GET /api/rounds/options` for the seat picker.
- **T-16.06 `RoundCoach.tsx` on the Apply page.** Inputs: round, allotted seat, rank, category, higher choices. Output: action card with the quoted rule, history table per higher choice, money-at-risk strip with dates. EN+HI. Parent view leads with money; student view leads with the choices.
- **T-16.07 Replay mode.** The next live cycle is June 2027, so the screen needs a "Try it with JoSAA 2025" switch that walks rounds 1 to 6 for a chosen rank. This is also the demo path. Check in the browser at 375 px and desktop.

### Stage 3 — Copilot and saved season
- **T-16.08 `round_advice` Copilot tool**, rules-first routing ("I got NIT Patna in round 2, should I float?"), answers templated from the engine, test that numbers equal engine output.
- **T-16.09 Save the season per family.** `RoundState` table (owner column, like `Deposit`): one row per round with the allotment and the action taken. Parent and student see the same record; the student can enter, only the parent records payments (existing guard).

### Stage 4 — Alerts (needs owner choices)
- **T-16.10 Deadline alerts by email** through the existing mailer interface. Blocked on T-11.04 (real email provider).
- **T-16.11 WhatsApp alerts.** Needs a provider account, approved message templates and an explicit opt-in. Ask before any setup. Content is dates and amounts only, no personal data beyond the first name.
- **T-16.12 Load the JoSAA 2027 schedule and rules** when published (expected about June 2027), same sourcing as `timeline.json`.

### Stage 5 — Charging for it
- **T-16.13 Season pass.** History table free; saved season, alerts and the family record paid once per season through the existing PayPal checkout (sandbox only until the owner decides otherwise).

## 5. Decisions for the owner before building

1. **Wording threshold.** What counts as "often reached": I suggest plain counts only ("4 of 5 years") with no label, until the backtest in T-16.04 shows how reliable history is.
2. **History window.** Last 5 years (suggested) or all 10. Older years include different seat matrices.
3. **Free or paid line** in Stage 5.
4. **Alert channel first:** email (cheaper, already half built) or WhatsApp (where parents are).
5. **Scope:** JoSAA rounds only for now. CSAB and state counselling need new data.

## 6. Smallest useful slice

Stages 1 and 2 (T-16.01 to T-16.07). That gives a working screen with replay on official 2025 data, no new accounts, keys or providers.

## 7. Backtest result (T-16.04, 2026-11-13) and what it changed

`python scripts/backtest_rounds.py` on JoSAA 2025 with 2020-2024 as history. A case is one seat, one round (not the last) and a student whose rank is 2%, 5% or 10% beyond that round's closing rank. Share of cases in which the seat reached the student's rank by the last round:

| What the past years said | Relative reading, 2% / 5% / 10% | Direct-rank reading, 2% / 5% / 10% |
|---|---|---|
| No past year | 14% / 13% / 7% | 47% / 31% / 13% |
| Fewer than half | 34% / 28% / 18% | 49% / 36% / 21% |
| Half or more | 66% / 57% / 46% | 62% / 51% / 37% |
| Every past year | 92% / 88% / 84% | 70% / 62% / 48% |

Relative reading: a past year says yes when the closing rank moved after this round by at least the share the student is short by now. Direct-rank reading: a past year says yes when its closing rank reached the student's rank itself (the plan's first design). The direct reading barely separates the cases because closing ranks drift from year to year, so the app uses the relative one and needs this round's closing rank (read from the archive in a replay, typed in for a live round). 10,641 cases had fewer than three past years and were left out.

