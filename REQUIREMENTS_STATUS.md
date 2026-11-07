# Requirements status (checked 2026-11-07 against `requirements.md`)

Legend: **Done** built and tested · **Partial** built with a stated gap · **Open** not built.
"Tested" means automated tests or a browser run; nothing below has run against the real PayPal sandbox, Channel3 or a hosted Qwen model (no keys were available).

## Functional
| ID | Status | Notes |
|---|---|---|
| FR-01 Intake | Partial | EN/HI rules + local Qwen3-4B verified. Hosted model untested. Elastic hybrid search (P2) not built |
| FR-02 Alignment | Done | Deterministic score and discussion guide |
| FR-03 ROI explorer | Partial | Disposable-income payback and AG Charts trajectory done. Mid-career role transitions are not shown; Year 2-10 is an editable growth model, not audited bands |
| FR-04 Truth matrix | Done | Brochure vs audited, denominator, accreditation as stated in sources, 0% commission badge, NIRF rank; sort/filter 2,000 rows in ~20 ms |
| FR-05 Source badges and API | Done | Field-level evidence endpoint and UI popover. Public Postman collection generated, not published |
| FR-06 Choice simulator | Done | Order-inversion alerts, suggested order |
| FR-07 Timeline | Partial | Sourced JoSAA 2026 / CSAB / JEE Main 2027 data with countdowns. Bryntum not integrated (no credentials). The UX spec's 96/72-hour wording is not in the official schedule |
| FR-08 Tech kit | Partial | Kit, totals, checkout and Pay-in-4 preview done in mock mode. Channel3 live parsing and PayPal Pay Later unproven |
| FR-09 Refund tracker | Partial | UGC tiers, countdowns, letter generator done. PayPal dispute/webhook simulation and push/email alerts not built |
| FR-10 Booking and escrow | Partial | Booking, capacity, ledger, payout, retries and idempotency tested in mock mode. Live sandbox untested; Bryntum Scheduler not integrated; Zapier hook built, not exercised live |
| FR-11 Agent | Partial | Tools, guarded model use and confirm-before-order done. Official PayPal Agent Toolkit/MCP not integrated |
| FR-12 Deployment | Partial | Dockerfile, render.yaml, smoke script ready; image contents verified in a clean venv. Not built with Docker (daemon off) and not deployed (needs your Render account) |

## UX
UX-01 to UX-06 Done · UX-07 Partial (section order differs slightly from the spec) · UX-08 Done · UX-09 Partial (checked at 375 px; no full AA audit) ·
UX-10 Partial (main strings translated; secondary strings still English) · UX-11 Done (USD and escrow disclosures shown).

## Data
DR-01 to DR-09 Done. DR-10 Partial: 7 verified colleges, not 10 (13 candidates excluded, see decisions D-22 to D-26).

## Non-functional
NFR-01 Done for the grid (see above); page load not measured on a real network, first load is 82 KB gzipped JS · NFR-02 Done (no PII in logs or model prompts, per-browser data) ·
NFR-03 Done · NFR-04 Done (mock fallbacks for PayPal, Channel3, LLM) · NFR-05 Done · NFR-06 Done · NFR-07 Done.

## Integrations
INT-01 PayPal Partial (mock-tested; live sandbox, JS SDK v6, Pay Later, Agent Toolkit unproven) · INT-02 AG Grid Done · INT-03 Bryntum Open ·
INT-04 Channel3 Partial · INT-05 Render Partial (files only) · INT-06 Elastic Open · INT-07 Postman Partial (collection generated and JSON-validated, not run in Postman) ·
INT-08 Zapier Partial · INT-09 LLM Partial.

## Definition of done
DoD-04 MIT licence file Done; public GitHub repo Open (needs your OK and account) · DoD-05 demo video Open (script in `DEMO_SCRIPT.md`) · DoD-06 live Render URL Open.
