# EduClear — Agent Manual (READ THIS FIRST, EVERY SESSION / EVERY TASK)

You are working inside `/Users/rahul/Desktop/Gen AI/Paypal-hackthon/`. Stay inside this folder. Hackathon deadline: **13 Nov 2026**.

## 1. Read order (do this before any task or after any context reset)
1. `AGENT_MANUAL.md` (this file)
2. `todo.md` → find the next unchecked task (lowest ID in the current phase)
3. `decisions.md` → honour every decision; do not re-litigate
4. `requirements.md` → read the FR/UX/DR/NFR/INT IDs the task cites
5. Source docs only when needed: `EduClear_BRD.md`, `EduClear_UX_Spec.md`, `DATA_INGESTION_MANUAL.md`, `prototype.html` (visual reference only; its numbers are placeholders)

## 2. The task loop
1. Pick the next task in `todo.md`. Do not skip ahead past a **GATE**.
2. Do the task. Keep changes minimal and inside the task's scope.
3. Run the task's verification (listed in `todo.md`). Failing verification = task not done.
4. Tick `todo.md`: `- [x]`, add date and one-line evidence (command + result, or file path).
5. If you made or discovered a decision, append it to `decisions.md` (next D-number).
6. Report to the user in a few lines: what was done, evidence, what is next.

## 3. Hard gates
- **Data gate (end of Phase 1):** no application code until the user signs off the dataset and `data/VERIFICATION_REPORT.md`.
- **PayPal is sandbox only.** Never use or request live credentials. `PAYPAL_ENV` must be `sandbox`.
- Ask before: pushing to GitHub, creating a public repo, downloading from any domain not listed in `plan.md`, installing anything globally.

## 4. Data rules (zero-synthetic)
- Every number comes from an official source (NIRF, JoSAA/CSAB, UGC/AICTE, institute fee circular, official placement report) and is recorded with URL, retrieval date, SHA-256 of the saved snapshot in `data/sources/<id>/`.
- Never estimate, round up, or fill a gap. Unverifiable college → skip and substitute an alternate (D-05).
- Every record must pass `npm run validate:data` (6 gates, ported to Python in `scripts/validate_data.py`) and an independent second-pass re-read.
- The LLM never produces numbers shown to users; deterministic Python engines do.

## 5. Coding standards
- Backend: Python 3.12 in `.venv` (via `uv`), FastAPI, Pydantic v2, SQLModel, pytest. Type hints everywhere. Money in integer INR (rupees) / integer USD cents; never floats for money.
- Frontend: React + Vite + TypeScript. Design tokens from `requirements.md` UX section. Tabular numerals (JetBrains Mono) for figures.
- Every external integration (PayPal, Channel3, LLM, Elastic, Zapier) sits behind an interface in `backend/app/integrations/` with a mock fallback so the demo never breaks.
- Tests live beside the layer they test. Mocked tests must run offline.

## 6. Secrets
- Real keys only in `.env` (git-ignored). Names listed in `.env.example`. Never print, log, commit, or echo values. Report presence by name only.

## 7. Definition of done (per task)
Code/doc written · verification passed · `todo.md` ticked with evidence · decisions logged · no stray files outside the folder map.

## 8. Folder map
```
plan.md  todo.md  decisions.md  requirements.md  AGENT_MANUAL.md  CLAUDE.md
KEYS_CHECKLIST.md  PREREQS.md  .env.example  .gitignore
data/{schema,colleges,sources,VERIFICATION_REPORT.md}
scripts/            validate_data.py, paypal_sandbox_smoke.py
backend/app/{main.py,config.py,models,routers,services,engines,llm,integrations,db.py}  backend/tests/
frontend/src/{pages,components,lib,i18n}
postman/  render.yaml  LICENSE
```

## 9. Commands
- Validate dataset: `npm run validate:data` · Tests: `.venv/bin/python -m pytest backend/tests tests -q`
- Run API (from repo root): `.venv/bin/uvicorn backend.app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run build` (type-check + bundle) · dev: `npm run dev` (proxy to :8000)
