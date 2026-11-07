# Keys, licences and accounts needed
Put values only in `.env` (never in chat). Names are in `.env.example`. **Phase 1 (dataset) needs none.**

| # | Service | You provide | Env names | Needed by |
|---|---|---|---|---|
| 1 | PayPal Developer (sandbox) | REST app Client ID + Secret; sandbox **US** Business + Personal accounts; Payouts enabled on Business; Webhook ID (needs a public URL: Render, or ngrok/cloudflared) | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_COUNSELLOR_PAYOUT_EMAIL` | Phase 5 |
| 2 | Channel3 | API key from hackathon portal | `CHANNEL3_API_KEY` | Phase 5 |
| 3 | Qwen3-4B hosted API | Provider choice (OpenRouter / Together / DashScope / HF), API key, exact model slug | `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` | Phase 6 |
| 4 | Bryntum | Trial/sponsor registry credentials for npm.bryntum.com + licence key if any | `BRYNTUM_NPM_USER`, `BRYNTUM_NPM_PASSWORD`, `BRYNTUM_LICENSE_KEY` | Phase 3–4 |
| 5 | Render | Account, hackathon credit code applied, GitHub connected | (none; dashboard) | Phase 7 |
| 6 | GitHub | Account + OK to create a public MIT repo (I ask before any push) | (none) | Phase 7 |
| 7 | AG Grid | None for Community/Charts; Enterprise trial key only if needed | — | Phase 3 |
| 8 | Elastic Cloud (stretch) | Endpoint URL + API key | `ELASTIC_URL`, `ELASTIC_API_KEY` | Phase 7 |
| 9 | Zapier (stretch) | Catch-hook URL with Zap for Calendar/Zoom | `ZAPIER_WEBHOOK_URL` | Phase 7 |
| 10 | Postman (stretch) | Account (+ API key to publish) | `POSTMAN_API_KEY` | Phase 7 |
