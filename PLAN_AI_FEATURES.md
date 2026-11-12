# EduClear — Plan: AI fixes and features (DRAFT, 2026-11-12)

Status: plan only. Nothing here is built. Read with `AGENT_MANUAL.md`, `decisions.md` (D-07, D-29, D-46, D-55, D-56, D-59, D-60, D-61) and `requirements.md` (FR-01, FR-11, NFR-02, NFR-04, INT-06, INT-09).
Timing: `AGENT_MANUAL.md` says 13 Nov; D-45 says submissions close 12 Nov 2026, 12:00 pm PT. If D-45 holds, only Stage 1 is realistic before the deadline.
Task IDs below are proposed as Phase 15 in `todo.md` (not yet added there). Next free decision number is D-62.

---

## 1. Where we are

- **Model access** (`backend/app/llm/client.py`): hosted model (OpenRouter, OpenCode and others) with local Ollama behind it (`FallbackLLM`), or no model at all. Emails and phone numbers are redacted before any call. Every call may return `None`, which means "use the rules".
- **Intake** (`backend/app/services/intake.py`): English and Hindi regex first; the model fills only fields the rules missed, and each value is checked by `_supported`.
- **Copilot** (`backend/app/services/agent.py`, `routers/agent.py`, `frontend/src/components/Copilot.tsx`): 8 fixed tools, rules-first routing, templated EN/HI replies from the engines, optional guarded rephrasing (`LLM_PHRASING`, off by default), booking only after the user confirms.
- **What the review found** (each checked by running the code on 2026-11-12):
  1. The model router never runs in the real UI. `route_rules` returns `recommend` whenever the profile has a percentile, and the UI always sends one. "What is the refund deadline for JoSAA?", "Is my choice order ok?" and "what does median salary mean" all route to `recommend`.
  2. The `recommend` tool hardcodes Computer Science and passes no seat type, gender or category rank. `agentProfile` in `frontend/src/api.ts` does not send them either.
  3. No memory between turns. `profile.last_college` is read but never written, and the Copilot never sends the returned profile back.
  4. College matching dates from the 7-college set. "tell me about IIIT Hyderabad" explains IIT Hyderabad, because the alias "hyderabad" is found first.
  5. The intake guard accepts any valid region or stream from the model without checking the text, and any budget when the word "crore" appears.
  6. Model timeouts are 60 to 90 s and `/api/agent/chat` and `/api/intake` have no rate limit.
  7. FR-01 names `backend/tests/test_intake.py` with 10 English and 10 Hindi sentences. That file does not exist; the intake tests are a few cases inside `test_agent.py`.

## 2. Rules that do not change

1. The model never produces a number shown to a user (D-07). It may extract, choose a tool, or rephrase a finished answer.
2. Anything the model extracts must be literally present in the user's text, or it is dropped.
3. Rephrased text is rejected unless its numbers equal the template's numbers (`phrase()` in `agent.py`).
4. Every feature works with no model (NFR-04). Tests run offline with a fake model.
5. No PII in prompts (NFR-02): keep `redact()` on every call.
6. A payment order is created only after the user confirms.

## 3. Non-goals

- No free-form chat answers written by the model.
- No vector database or Elastic (INT-06 stays P2); B5 uses the in-memory fallback INT-06 already names.
- No change to payments, accounts or the dataset.
- No streaming replies.

---

## 4. Stage 1 — Fix what exists (about half a day)

### T-15.01 Router: off-topic questions must not get suggestions (A1)
- **Files:** `backend/app/services/agent.py` (`route_rules`, `choose_tool`), `backend/tests/test_agent.py`.
- **Change:** drop the `"recommend" if prof.get("percentile") else "help"` fallback; return `help` when no rule matches. `choose_tool` already asks the model on `help`. With no model, the help text is the answer.
- **Keep:** the guard that the model cannot choose `propose_booking` unless "book" or "reserve" is in the message.
- **Verify:** the three messages in §1.1 return `help` with no model, and a fake model's choice is honoured. An existing test may expect the old fallback; update it deliberately.

### T-15.02 Copilot uses the chosen branch and category (A2)
- **Files:** `agent.py` (`run_tool`, recommend case), `frontend/src/api.ts` (`agentProfile`), `test_agent.py`.
- **Change:** stream = stream parsed from the message (intake already returns it), else `profile.stream`, else Computer Science. Send `stream`, `seat_type`, `gender`, `category_rank` from the UI and pass them as `opts` to `recommend()`. When the deck is empty but `cutoff_only` has rows, list the first three with the label "closing rank only".
- **Verify:** for the same inputs, the Copilot reply for Mechanical names the same colleges as `POST /api/recommend`. MBA returns the "not available" line.

### T-15.03 Memory between turns (A3)
- **Files:** `agent.py` (`handle`), `Copilot.tsx`, `api.ts` (`AgentReply` gains `profile`).
- **Change:** when a reply is about one college, set `merged["last_college"]`. The Copilot keeps the returned `profile` in state and merges it into the next request (page profile first, then the chat's extras).
- **Verify:** test with two calls: "Tell me about NIT Calicut", then "can I afford it with 5 lakh savings" answers for NIT Calicut. Browser check of the same exchange.

### T-15.04 College name matching for 108 colleges (A4)
- **Files:** `agent.py` (`ALIASES`, `_find_colleges`), `test_agent.py`.
- **Change:** match `name` and `shortName` longest first and remove the matched span before looking for the next, so "IIIT Hyderabad" cannot also match "IIT Hyderabad". Keep only aliases that point to exactly one college (`nitc`, `iitg`, `iith`, `dtu`, `bits`); drop bare cities (`hyderabad`, `jaipur`, `delhi tech` stays). If a single-college tool finds two or more, reply "Which one: X or Y?".
- **Verify:** parametrised test: IIIT Hyderabad, IIT Hyderabad, IIIT Delhi, IIT Delhi, DTU each resolve to themselves; "Hyderabad" alone asks which one.

---

## 5. Stage 2 — New tools and the claim checker (about one day)

### T-15.05 Four more Copilot tools over existing engines (B1)
- **Files:** `agent.py` (`TOOLS`, `TOOL_SYSTEM`, `route_rules`, `run_tool`), `test_agent.py`, `Copilot.tsx` (suggested prompts).
- **Tools:**
  | Tool | Trigger words (en / hi) | Source | Reply |
  |---|---|---|---|
  | `deadlines` | deadline, when is, round, last date / कब, अंतिम तिथि | `services/admissions.timeline()` | next three dated events with days left |
  | `refund` | refund, withdraw, cancel seat / रिफंड, वापसी | `engines/refund.milestones()` and `admissions.refund_policy()` | the UGC tiers with dates; amount only if the user gave one |
  | `check_choice_order` | choice order, preference list, filling / वरीयता | `engines/choice.analyse()` | alerts, or "no inversions"; needs two or more colleges in the message |
  | `compare` | compare, vs, versus, better / तुलना | `recommend.card()` per college | one line per college: cost, median, placed of eligible, payback |
- **Rule:** each reply is a template in English and Hindi; numbers only from the engine output.
- **Verify:** one routing test and one "numbers equal the engine" test per tool; no-model mode passes.

### T-15.06 Brochure claim checker (B2)
- **What it does:** the user pastes a brochure or advert line. The app shows each claim next to the record.
- **Files:** new `backend/app/services/claims.py`, `POST /api/claims/check` in `routers/agent.py`, new `frontend/src/components/ClaimChecker.tsx` on the Find page, a `check_claim` Copilot tool, `backend/tests/test_claims.py`, `i18n.ts`.
- **Flow:**
  1. Rules extract: college (T-15.04 matcher), a percentage near "placement", an LPA or crore figure near "package / CTC / highest / average".
  2. The model fills only what the rules missed, as JSON `{college, claimed_rate_pct, claimed_package_lpa, package_kind}`; each number must appear in the text.
  3. Python compares with the college record: claimed package against `headlineCTC` and `medianBaseSalary`; claimed rate against `actuallyPlaced / eligibleStudents`.
  4. Templated verdict lines, for example: "Brochure: 45 LPA. Record: median 9.2 LPA, headline 44 LPA." and "Brochure: 100% placed. Record: 412 of 520 eligible (79%)."
- **Edge cases:** college not found → ask which one; record has no figure → "not in our data", never an estimate; show the "Supplied, not audited" label and the source link (D-57).
- **Verify:** tests for a rate claim, a package claim, an unknown college, a model-invented number being dropped, and no-model mode. Browser check with one pasted line.

---

## 6. Stage 3 — Guard, limits and tests (about half a day)

### T-15.07 Close the intake guard holes (A5)
- **Files:** `intake.py` (`_supported`), `test_agent.py` or the new `test_intake.py`.
- **Change:** region and stream from the model count only if the matching `REGIONS` or `STREAMS` pattern is found in the text. The crore exception holds only when a number in the text × 100 equals the returned value; also accept "करोड़". Add brackets so the `and` / `or` order is explicit.
- **Verify:** for "I have 1.5 crore and like the mountains": budget 250, region South and stream Civil are rejected; budget 150 is accepted.

### T-15.08 Short chat timeout and a rate limit (A6)
- **Files:** `llm/client.py` (timeout parameter), `routers/agent.py`, `config.py` (`llm_chat_timeout_s: 8`, `agent_per_minute: 30`), `test_llm_client.py`, `test_agent.py`.
- **Change:** chat and intake calls use the short timeout; `scripts/llm_smoke.py` keeps the long one. Add a small in-memory per-IP counter for `/api/agent/chat`, `/api/intake` and `/api/claims/check` (the auth limiter counts `AuthCode` rows, so it cannot be reused; `_client_ip` can).
- **Open point:** a reasoning model may not answer in 8 s, so more answers will come from rules. Decide the number after one live run; log as D-62.
- **Verify:** a fake model that stalls yields a rules answer inside 10 s; the 31st call in a minute returns 429.

### T-15.09 Golden test set (B6)
- **Files:** new `backend/tests/test_intake.py`, additions to `test_agent.py`.
- **Change:** 10 English and 10 Hindi intake sentences with expected fields (include Devanagari digits, crore, and romanised Hindi such as "mera 94 percentile hai, budget 10 lakh"), pass mark 90% (FR-01). Five scripted Copilot conversations whose numbers equal the engine outputs (FR-11).
- **Verify:** `.venv/bin/python -m pytest backend/tests -q` passes offline.

---

## 7. Stage 4 — Optional features (as time allows)

### T-15.10 "Why this college" line on deck cards (B3)
- **Files:** `services/recommend.py` (`card` gains `why`), `BentoDeck.tsx`, `i18n.ts`.
- **Change:** a template sentence from the card's own facts (tier, cost against budget, median, payback). Optional rephrasing through `phrase()`, cached in memory per (college, inputs, language) so a render never waits on a model.
- **Verify:** the line's numbers equal the card's; with no model the template shows.

### T-15.11 Family discussion brief (B4)
- **Files:** `engines/alignment.py` (or a new `services/brief.py`), `AlignmentSurvey.tsx`, `i18n.ts`.
- **Change:** after the survey, three or four talking points built from the gaps and the current deck colleges (for example the budget gap next to the EMI of the Reach college), in English and Hindi, with a link to the family session.
- **Verify:** identical answers give no points; a budget gap of 2 or more names a real college and its engine EMI.

### T-15.12 Grounded glossary answers (B5)
- **Files:** new `data/glossary.json` (about 30 entries, en + hi, each with a source URL), new `services/glossary.py` (in-memory TF-IDF), an `explain_term` Copilot tool.
- **Change:** the shown text is always the curated entry. The model may only pick among the top three matches; below a score threshold the answer is "I do not have that".
- **Rule:** entries state definitions and official rules only, each with its source (zero-synthetic data rule).
- **Verify:** "what does median salary mean" and "होम स्टेट कोटा क्या है" return the right entries; an unrelated question returns the refusal.

---

## 8. Order and dependencies

1. T-15.01 → T-15.04 (Stage 1). T-15.04 before T-15.05 and T-15.06, which rely on the matcher.
2. T-15.05, then T-15.06.
3. T-15.07, T-15.08, T-15.09.
4. T-15.10 to T-15.12 in any order.

## 9. Definition of done (every task)

- Tests pass offline: `.venv/bin/python -m pytest backend/tests tests -q`.
- `cd frontend && npm run build` passes when the frontend changed; the changed flow is checked in the browser.
- One live check with the real model for tasks that touch a prompt (T-15.01, T-15.05, T-15.06, T-15.07).
- `todo.md` ticked with evidence; decisions logged from D-62.

## 10. Risks

- **Free hosted model is rate-limited (D-55, D-56).** After T-15.01 the model is called more often. The pause-on-429 and the Ollama fallback already cover it; on Render there is no Ollama, so those answers fall to the help text.
- **Small models route badly in Hindi (D-07).** Keep adding Hindi trigger words to the rules so the model is the last resort.
- **Claim checker on supplied data.** A verdict is only as good as the record; always show the data label and source.
