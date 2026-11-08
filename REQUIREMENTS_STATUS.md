# Requirements status (checked 2026-11-07 against `requirements.md`)

Legend: **Done** built and tested · **Partial** built with a stated gap · **Open** not built.
"Tested" means automated tests or a browser run. Updated 2026-11-07: PayPal auth, order, capture, payout and a human in-app payment have run against the live sandbox; Channel3 and a hosted Qwen model are still untested (no keys).

## Functional
| ID | Status | Notes |
|---|---|---|
| FR-01 Intake | Partial | EN/HI rules + local Qwen3-4B verified. Hosted model untested. Elastic hybrid search (P2) not built |
| FR-02 Alignment | Done | Deterministic score and discussion guide |
| FR-03 ROI explorer | Partial | Disposable-income payback and AG Charts trajectory done. Mid-career role transitions are not shown; Year 2-10 is an editable growth model, not audited bands |
| FR-04 Truth matrix | Done | Brochure vs audited, denominator, accreditation as stated in sources, 0% commission badge, NIRF rank; sort/filter 2,000 rows in ~20 ms |
| FR-05 Source badges and API | Done | Field-level evidence endpoint and UI popover. Public Postman collection generated, not published |
| FR-06 Choice simulator | Done | Order-inversion alerts, suggested order |
| FR-07 Timeline | Done | Bryntum Gantt: sourced JoSAA 2026 / CSAB / JEE Main 2027 dates grouped by round with linked dependencies, plus the user's own sessions coloured by payment state; simple-bars view kept as fallback. The UX spec's 96/72-hour wording is not in the official schedule |
| FR-08 Tech kit | Partial | Kit, totals, checkout and Pay-in-4 preview done in mock mode. Channel3 live parsing and PayPal Pay Later unproven |
| FR-09 Refund tracker | Partial | UGC tiers, countdowns, letter generator done. PayPal dispute/webhook simulation and push/email alerts not built |
| FR-10 Booking and escrow | Done | Bryntum Scheduler booking calendar (slot colour follows PayPal state). Live sandbox: order, capture and in-app payment verified; payout and signed webhook still to be confirmed. Zapier hook built, not exercised live |
| FR-11 Agent | Done | Tools, guarded model use, confirm-before-order; confirmed orders are created through the official PayPal MCP server with REST fallback (human approval of an MCP-made order still to be tested) |
| FR-12 Deployment | Done | Live on Render (Docker + Postgres) at educlear.onrender.com; smoke script 14/14 against it. Docker image not built locally (daemon off) |

## UX
UX-01 to UX-06 Done · UX-07 Partial (section order differs slightly from the spec) · UX-08 Done · UX-09 Done (375 px; axe-core WCAG 2.1 AA scan clean on our pages, Bryntum Gantt internals report aria-required-children) ·
UX-10 Partial (headings, booking and timeline controls translated; long notes still English) · UX-11 Done (USD and escrow disclosures shown).

## Data
DR-01 to DR-09 Done. DR-10 Partial: 7 verified colleges, not 10 (13 candidates excluded, see decisions D-22 to D-26).

## Non-functional
NFR-01 Done for the grid (see above); page load not measured on a real network, first load is 82 KB gzipped JS · NFR-02 Done (no PII in logs or model prompts, per-browser data) ·
NFR-03 Done · NFR-04 Done (mock fallbacks for PayPal, Channel3, LLM) · NFR-05 Done · NFR-06 Done · NFR-07 Done.

## Integrations
INT-01 PayPal Partial (live sandbox, SDK v6 button and an in-app payment proven; signed webhook, Pay Later and Agent Toolkit unproven) · INT-02 AG Grid Done · INT-03 Bryntum Done (trial packages from public npm; Gantt + Scheduler, one bundle) ·
INT-04 Channel3 Partial · INT-05 Render Done · INT-06 Elastic Open · INT-07 Postman Partial (collection generated and JSON-validated, not run in Postman) ·
INT-08 Zapier Partial · INT-09 LLM Partial.

## Definition of done
DoD-04 MIT licence file Done; public GitHub repo Done (github.com/Rahul-153/EduClear) · DoD-05 demo video Open (script in `DEMO_SCRIPT.md`) · DoD-06 live Render URL Done.
