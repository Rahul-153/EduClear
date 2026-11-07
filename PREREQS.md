# Prerequisite check — 2026-11-06 (Phase 0b)

## Toolchain
| Check | Result | Note |
|---|---|---|
| uv | PASS 0.6.17 | |
| Python 3.12 | PASS | `uv`/anaconda 3.12.7 present, so no install needed; system 3.9.6 not used (D-14). `.venv` created in T-1.01 |
| Node / npm | PASS v26.8.1 / 11.19.0 | |
| git | PASS 2.50.1 | folder is not a repo yet; I ask before `git init`/push |
| Ollama | PASS 0.13.5 | **`qwen3:4b` already installed** (2.5 GB), usable as local dev LLM (D-07); `nomic-embed-text` also present |

## Network (curl)
| Host | Result | Note |
|---|---|---|
| nirfindia.org | PASS with browser user-agent | plain curl got 403; use browser UA/headers or built-in browser |
| josaa.admissions.nic.in | PASS 200 | archive is a form; may need browser-driven fetch |
| ugc.gov.in | PASS with browser UA | |
| nitt.edu, bits-pilani.ac.in | PASS | |
| iitb.ac.in | **FAIL (timeout 25 s)** | retry later / use built-in browser; IIT Bombay data may need NIRF PDF only |
| api.trychannel3.com, api-m.sandbox.paypal.com | reachable (403 on root, expected without auth) | |
| npm.bryntum.com, openrouter.ai, api.together.xyz, huggingface.co, render.com, github.com | PASS 200 | |
| dashscope.aliyuncs.com | 404 on root (reachable) | |

## Credentials (names only)
No `.env` exists; none of PAYPAL_*, CHANNEL3_*, LLM_*, BRYNTUM_* set. **Phase 1 not blocked.** Blocks: PayPal/Channel3/Bryntum → Phase 3–5, LLM key → Phase 6 (local Ollama qwen3:4b works for dev meanwhile).

## Disk / ports
`data/sources/` writable; 73 GiB free; ports 8000 and 5173 free.

## Accounts to confirm with user (not verifiable by me)
PayPal sandbox US Business + Personal accounts and Payouts enabled · Bryntum trial access · Render credits · GitHub public-repo permission · hosted Qwen provider choice.

## Verdict
**GO for Phase 1** (toolchain and network OK). Watch items: IIT Bombay site timeout, NIRF needs browser UA, JoSAA archive needs form-driven fetch.
