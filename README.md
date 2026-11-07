# EduClear — clear truth in higher education

An independent, student-funded advisory platform for Indian college choice and financing. Every college figure links to an
official filing; placement numbers show the true denominator (placed ÷ eligible); payments run **only in the PayPal sandbox**.
Built for the PayPal AI Hackathon 2026.

## What it does
| Area | Feature |
|---|---|
| Discovery | Smart Sentence filters, plain-language intake in English/हिंदी, Truth Lens (Brochure ⇄ Audited), Safe / Sweet-spot / Reach deck |
| Evaluation | AG Grid Placement Truth matrix, source badges with field-level evidence, ROI and payback charts (AG Charts), family alignment survey |
| Strategy | Choice-filling simulator (order-inversion alerts), admissions timeline from official JoSAA/CSAB/NTA notices |
| Protection | Seat-deposit tracker with UGC refund tiers and a refund-letter generator |
| Commerce | Four counselling programs with a PayPal sandbox escrow ledger and Payouts release, campus tech kit (Channel3) with Pay Later, Copilot agent that proposes and only books after you confirm |

## Data policy (zero-synthetic)
`data/colleges/*.json` holds 7 verified colleges (DTU Delhi, BITS Pilani, IIT Hyderabad, IIT BHU, IIT Guwahati, MNIT Jaipur, NIT Calicut).
Each field carries its official URL, locator and the SHA-256 of the saved snapshot; `data/VERIFICATION_REPORT.md` lists them all.
The downloaded evidence files themselves (`data/sources/`, hundreds of MB) are **not** published in this repository: the recorded URL and SHA-256 let anyone re-download a document and confirm it is unchanged. Without the folder, `npm run validate:data` skips the file checks and says so.
Thirteen further candidates were excluded because their own documents did not support a figure (see `decisions.md` D-22 to D-26).
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
.venv/bin/python -m pytest backend/tests tests -q              # offline, 80 tests
.venv/bin/python -m pytest -m paypal_sandbox backend/tests/paypal   # live sandbox (needs keys)
.venv/bin/python scripts/smoke.py http://localhost:8000        # end-to-end smoke against a running instance
```
`postman/` has a collection with automated tests (regenerate with `scripts/make_postman.py`).

## Deploy (Render)
`render.yaml` defines a Docker web service plus Postgres. Connect the repo, create the Blueprint, then set the `sync: false` secrets
in the dashboard. `PAYPAL_ENV` is pinned to `sandbox` and the app refuses to start otherwise. Check the public URL with `scripts/smoke.py <url>`.

## Honest limitations
- PayPal live-sandbox calls, PayPal JS SDK v6 buttons, Pay Later, Channel3 live prices and a hosted Qwen model are written but unproven until keys are added.
- The Bryntum timeline/scheduler and Elastic search are not built; plain components stand in. The official PayPal Agent Toolkit / MCP is not integrated.
- "Escrow" is a platform ledger plus PayPal Payouts; PayPal has no escrow product. Prices show ₹ and charge USD at a fixed demo rate.
- Only Computer Science is covered; the counsellor profile is a demo placeholder.
See `REQUIREMENTS_STATUS.md` for the requirement-by-requirement status.

## Layout
`backend/` FastAPI (engines, services, integrations) · `frontend/` React + Vite · `data/` verified dataset, schema, sourced admissions data, evidence ·
`scripts/` validators, scrapers, smoke · `plan.md`, `todo.md`, `decisions.md`, `requirements.md`, `AGENT_MANUAL.md` project records.

Licensed under the MIT License.
