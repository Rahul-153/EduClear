# EduClear — clear truth in higher education

An independent, student-funded advisory platform for Indian college choice and financing. Placement numbers show the true
denominator (placed ÷ eligible); payments run **only in the PayPal sandbox**. Built for the PayPal AI Hackathon 2026.

> **Data status (branch `feature/zip-data`, decision D-53):** the 108 engineering colleges in this branch come from a dataset
> supplied to the project (`data/supplied/`, from `rehackathonfileseom.zip`). It is **not source-verified**: no source documents
> are on file and its figures do not match the earlier verified data, so the app labels every record "Supplied dataset, not
> audited". The earlier source-verified data (11 audited colleges, 19 partly verified IITs, the JoSAA 2025 cutoff table) is kept in
> `data/_archive_verified/`. See `DATA_ZIP_REVIEW.md`.

**Live demo:** https://educlear.onrender.com (Render, Postgres, PayPal **sandbox**). The first load after idle can take about a minute while Render wakes the service.

## Try the payment flow
1. Open the live demo, scroll to **Counselling sessions**, and click an open slot in the Bryntum booking calendar.
2. Click the yellow **PayPal** button and log in with a PayPal **sandbox personal (buyer)** account. Any sandbox buyer works: create one free at developer.paypal.com under Testing Tools, or use the demo buyer credentials given in the Devpost submission notes. Nothing real is charged.
3. After approval the booking shows "Funds held in escrow ledger". Click **Confirm session completed (release funds)** to send the PayPal Payouts release to the counsellor sandbox account.
4. Open the **Copilot** and ask "book a branch vs college session": the agent proposes, you confirm, and the order is created through PayPal's official MCP server.
If PayPal's sandbox pop-up hangs on its spinner after login, close it: the app already checks for the approval every few seconds and also offers a "check my payment" link.

## Sponsor tools
| Tool | Use |
|---|---|
| PayPal | Sandbox Orders v2, JS SDK v6 buttons incl. Pay Later, webhooks with signature verification, Payouts, official `@paypal/mcp` server for agent-created orders |
| Bryntum | Scheduler (booking calendar, colour follows payment state) and Gantt (linked counselling-cycle timeline), trial build from public npm |
| AG Grid | Placement Truth matrix (Community) and AG Charts for ROI |
| Channel3 | Live product prices for the campus tech kit, with a labelled sample fallback |
| Render | Docker web service and Postgres via `render.yaml` |
| Postman | Collection with automated tests in `postman/` |
| Zapier | Optional PII-free booking hook (`ZAPIER_WEBHOOK_URL`) |

## Built during the submission period (1 Oct to 12 Nov 2026)
The whole project was built in this period: dataset and verification pipeline, backend engines, the React app, PayPal sandbox payments and payouts, the Bryntum views, the agent, and the Render deployment. `todo.md` and `decisions.md` record each step with its evidence.

## What it does
| Area | Feature |
|---|---|
| Discovery | Smart Sentence filters, plain-language intake in English/हिंदी, Truth Lens (Brochure ⇄ Audited), Safe / Sweet-spot / Reach deck |
| Evaluation | AG Grid Placement Truth matrix, source badges with field-level evidence, ROI and payback charts (AG Charts), family alignment survey |
| Strategy | Choice-filling simulator (order-inversion alerts), admissions timeline from official JoSAA/CSAB/NTA notices |
| Protection | Seat-deposit tracker with UGC refund tiers and a refund-letter generator |
| Commerce | Four counselling programs with a PayPal sandbox escrow ledger and Payouts release, campus tech kit (Channel3) with Pay Later, Copilot agent that proposes and only books after you confirm |

## Data policy (zero-synthetic)
`data/colleges/*.json` holds 11 verified colleges (DTU Delhi, BITS Pilani, IIT Hyderabad, IIT BHU, IIT Guwahati, MNIT Jaipur, NIT Calicut, NIT Kurukshetra, NIT Silchar, NIT Patna, NIT Raipur).
Each field carries its official URL, locator and the SHA-256 of the saved snapshot; `data/VERIFICATION_REPORT.md` lists them all.
The downloaded evidence files themselves (`data/sources/`, hundreds of MB) are **not** published in this repository: the recorded URL and SHA-256 let anyone re-download a document and confirm it is unchanged. Without the folder, `npm run validate:data` skips the file checks and says so.
Further candidates were excluded because their own documents did not support a figure (see `decisions.md` D-22 to D-26 and D-47).
```bash
npm run validate:data      # 6 integrity gates + provenance + snapshot hashes
```
Model assumptions (tax slabs, savings rate, salary growth, loan terms) are not audited data. They are labelled and editable in the UI.

## Run it
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
cd frontend && npm ci && npm run build && cd ..
.venv/bin/uvicorn backend.app.main:app --port 8000      # open http://localhost:8000
```
Dev with hot reload: `cd frontend && npm run dev` (proxies `/api` to port 8000).
Copy `.env.example` to `.env` for keys. With no keys the app runs in **mock payment mode** and uses the rule-based assistant;
a local Ollama `qwen3:4b` is picked up automatically.

## Tests
```bash
.venv/bin/python -m pytest backend/tests tests -q              # offline, 84 tests
.venv/bin/python -m pytest -m paypal_sandbox backend/tests/paypal   # live sandbox (needs keys)
.venv/bin/python scripts/smoke.py http://localhost:8000        # end-to-end smoke against a running instance
```
`postman/` has a collection with automated tests (regenerate with `scripts/make_postman.py`).

## Deploy (Render)
`render.yaml` defines a Docker web service plus Postgres. Connect the repo, create the Blueprint, then set the `sync: false` secrets
in the dashboard. `PAYPAL_ENV` is pinned to `sandbox` and the app refuses to start otherwise. Check the public URL with `scripts/smoke.py <url>`.

## Honest limitations
- Proven against the live sandbox: auth, order, capture, payout, an in-app payment, SDK v6 button. Pay Later and signed-webhook delivery are tested by hand in the sandbox only if noted in `todo.md`.
- A hosted Qwen model is not used in the demo: the assistant is rules-first and calls a local or hosted model only for ambiguous messages.
- Elastic search is not built. The Bryntum trial adds a watermark and expires 45 days after install.
- Accessibility: our own pages pass an axe-core WCAG 2.1 AA scan; the Bryntum Gantt's internal ARIA structure reports `aria-required-children` (third-party widget).
- "Escrow" is a platform ledger plus PayPal Payouts; PayPal has no escrow product. Prices show ₹ and charge USD at a fixed demo rate.
- Only Computer Science is covered; the counsellor profile is a demo placeholder.
See `REQUIREMENTS_STATUS.md` for the requirement-by-requirement status.

## Layout
`backend/` FastAPI (engines, services, integrations) · `frontend/` React + Vite · `data/` verified dataset, schema, sourced admissions data, evidence ·
`scripts/` validators, scrapers, smoke · `plan.md`, `todo.md`, `decisions.md`, `requirements.md`, `AGENT_MANUAL.md` project records.

Licensed under the MIT License.
