# EduClear — Plan: separate login for parents and students (DRAFT, 2026-11-11)

Status: phases 1 and 2 built on branch `feature/auth` (2026-11-11), not merged, not deployed. Phases 3 to 5 and a real email provider remain. Read with `AGENT_MANUAL.md`, `decisions.md` (D-32, D-34, D-36, D-49), `PLAN_VIEWS_AND_DATA.md` (Part A views).
Timing: submissions close 12 Nov 2026, 12:00 pm PT (D-45). This plan is for after the deadline. The live demo stays account-free.

---

## 1. Where we are

- **No accounts.** Each browser gets a random UUID in `localStorage`, sent as `X-Client-Id`. Bookings and deposits are scoped to it (D-32). Nothing follows the family to another device or browser.
- **One identity seam.** `owner()` in `backend/app/routers/payments.py` (and the deposit and agent routes) turns the header into an owner string. `Booking.owner` and `Deposit.owner` in `backend/app/db.py` hold it. That is where accounts plug in.
- **Student and Parent are a UI switch** (Part A), stored in `localStorage`. It hides the booking UI for students but enforces nothing on the server: any caller can post a booking or confirm a session.
- **Alignment survey** keeps each side's answers in the browser only.
- **Payments** are PayPal sandbox only. The buyer identity is whoever approves in the PayPal pop-up, unrelated to the app.
- **Webhook** (`/api/webhooks/paypal`) is server to server and verified by signature. It must stay outside the login system.

## 2. Goals and non-goals

Goals
1. A student and a parent each sign in with their own credentials, and the server knows which role is calling.
2. A parent and student can be linked into one **family**, sharing a shortlist and survey, with role-based limits.
3. Only a parent can pay, book, confirm a session (release escrow) or manage deposits. The server enforces it.
4. Students who are minors are protected: no student account without a linked parent's consent.
5. Guests keep working. The demo, judges and the smoke script need no account.

Non-goals (for now): a counsellor login (D-33: no real counsellors yet), social features, password reset flows (we use no passwords), admin console.

## 3. Decisions to make first

| # | Decision | Recommendation | Why |
|---|---|---|---|
| A1 | Login method | **Email one-time code** (6 digits, 10 minutes), no passwords. Optional Google sign-in later | No password storage or reset flow; works for students without phones; no SMS cost or DLT registration |
| A2 | Phone OTP | Not in v1 | Needs an Indian SMS provider and template registration; add later if families ask |
| A3 | Can a student under 18 sign up alone? | **No.** A parent creates the family and invites the student; a student who signs up first gets a read-only "waiting for a parent to join" state | Child data rules and the BRD safeguard (section 5) |
| A4 | Can a student of 18 or more sign up alone? | Yes, and invite a parent. Age is self-declared | We do not verify age; say so in the consent text |
| A5 | Must a parent be signed in to pay? | **Yes.** Guest checkout stays only in the demo build (`DEMO_GUEST_CHECKOUT=true`) | Payments need an accountable person |
| A6 | Survey privacy | Each side's answers stay private until both have submitted, then both see the score and guide | The point is honest answers; a parent reading first defeats it |
| A7 | One parent or two | One parent per family in v1, up to two later | Keeps the permission model simple |
| A8 | Email sender | Resend or SendGrid free tier behind `backend/app/integrations/mailer.py`, with a mock that logs the code in dev | Matches the integration rule in `AGENT_MANUAL.md` section 5; keys go in `.env` and `KEYS_CHECKLIST.md` |

## 4. Roles and permissions

| Action | Guest | Student (linked) | Parent |
|---|---|---|---|
| Browse colleges, cutoffs, matrix, ROI | Yes | Yes | Yes |
| Edit own profile (percentile, budget) | Local only | Saved to family | Saved to family |
| Shortlist, choice rehearsal | Local only | Yes | Yes |
| Own survey side | Local only | Yes | Yes |
| See the other side's answers | No | After both submit | After both submit |
| Book a session, pay, tech-kit order | Demo build only | No (sees price, "ask a parent") | Yes |
| Confirm session completed (release funds) | No | No | Yes |
| Deposit tracker and refund letter | Local only | Read | Read and write |
| Copilot chat | Yes | Yes | Yes |
| Copilot "confirm and create order" | Demo build only | No | Yes |
| Invite or remove a family member | n/a | No | Yes |
| Delete the family's data | n/a | Own account only | Whole family |

## 5. Children's data (check with counsel before launch)

The BRD already commits to safeguarding users under 18 (`EduClear_BRD.md` section 7). India's Digital Personal Data Protection Act, 2023 treats under-18s as children and requires verifiable parental consent for processing their data; how the rules apply in practice should be confirmed with a lawyer, since I have not verified the current rules. Design choices that keep us safe either way:

- Collect the minimum: email, display name, role, and the profile fields already used (percentile, budget, region). No exam roll numbers, no phone, no address, no photos.
- Consent record per student: parent user id, timestamp, consent text version. Stored with the link.
- Student under 18 cannot be created without that record.
- Never send emails, names or ids to the LLM (the existing redaction stays) or to Zapier (the hook is PII-free today and must stay so).
- Delete and export: a parent can export or delete the family; deletion removes the student account and its answers. Ledger rows are kept without personal fields, because payment records have their own retention duty.

## 6. Design

### 6.1 Data model (new tables)

```
User(id, role {student|parent}, email unique, email_verified_at, display_name, is_minor, created_at, last_login_at)
Family(id, created_by, created_at)
FamilyMember(family_id, user_id unique, role)          one family per user in v1
Invite(id, family_id, role_to_join, token_hash, expires_at, used_by, used_at)
Consent(student_user_id, parent_user_id, text_version, given_at)
AuthCode(id, email, code_hash, expires_at, attempts, used_at)
Session(id_hash, user_id, created_at, expires_at, last_seen_at, user_agent_hash)
FamilyProfile(family_id, percentile, budget_lakhs, region, home_state, seat_type, gender, category_rank, updated_by, updated_at)
SurveyAnswers(family_id, side {student|parent}, answers_json, submitted_at)
```

Existing tables: add nullable `user_id` and `family_id` to `Booking` and `Deposit`; keep `owner` for guests. Bookings made by a parent carry their `user_id` and the family id, so the student can see status (read only).

### 6.2 Sessions and tokens
- Server-side sessions in the database. The cookie holds a random 256-bit id; only its hash is stored.
- Cookie: `HttpOnly`, `Secure`, `SameSite=Lax`, 14-day sliding expiry, 90-day absolute.
- The frontend is served by the same FastAPI service, so there is no CORS and no token in JavaScript.
- CSRF: `SameSite=Lax` plus a required `X-Requested-With` header on every state-changing call, checked server side. Webhook route excluded.
- Rotate the session id on login and on role or family change.

### 6.3 Email code flow
1. `POST /api/auth/start {email, role}` always answers the same message (no account enumeration).
2. A 6-digit code is stored hashed, expires in 10 minutes, 5 attempts, then burned.
3. `POST /api/auth/verify {email, code}` creates the user on first success and starts a session.
4. Limits: 5 codes per email per hour and 20 per IP per hour; sliding-window counter in the database (no new infrastructure).
5. The role is fixed at first sign-up; an email cannot be both parent and student. A second account needs another email.
6. Mock mailer prints the code to the server log in dev; with `DEMO_AUTH_SHOW_CODE=true` it returns the code in the response so a judge can sign in without email. That flag is refused when `ENV=production`.

### 6.4 Family linking
- Parent creates the family on first sign-in and gets an invite link or 8-character code for the student (expires in 7 days, single use, stored hashed).
- Student signs in, opens the link, sees who invited them and what will be shared, accepts. If the student is under 18 the consent record is written at that moment from the parent's earlier consent tick.
- Student first (age 18+): student creates the family and invites a parent; same acceptance step on the parent side.
- Either side can leave; the parent can remove the student; removing the parent of a minor locks the student account to read-only until another parent joins.

### 6.5 Authorization in code
- `current_user` dependency (optional) and `require_user`, `require_role("parent")`, `require_family_member` in `backend/app/auth/deps.py`.
- Replace `owner()` with `actor()` that returns the signed-in user, or a guest owner from `X-Client-Id` only when the route allows guests.
- Route guards: bookings, kit order, complete, cancel, capture, deposits write, agent confirm all `require_role("parent")` unless guest checkout is enabled for the demo.
- Every query on `Booking` and `Deposit` filters by `family_id` (accounts) or `owner` (guests), never by an id alone. Existing "wrong owner" tests extend to wrong family.

### 6.6 Moving guest data to an account
On first sign-in, if the browser holds an `X-Client-Id` with bookings or deposits, show "Add your earlier bookings to this account?" and, on yes, copy `owner` rows to `user_id` and `family_id` in one transaction. Never automatic, never for a student account (only a parent can hold payment records).

### 6.7 Frontend
- `AuthContext` with `user`, `family`, `role`. `GET /api/auth/me` on load.
- New `#login` page: pick role (Parent or Student), enter email, enter code. No password field.
- The header Student/Parent switch becomes the signed-in role and is hidden when signed in. Guests keep the switch as today.
- Family panel on the Get help page: invite link, member list, consent status, leave and delete.
- `Sessions`, `CheckoutPanel`, `Copilot` confirm: gated on role, with a clear "ask a parent" or "sign in as a parent" state instead of a silent hide.
- Family profile saved to the server when signed in; stays in `localStorage` for guests.
- All new strings in English and Hindi (`i18n.ts`).

### 6.8 API surface
```
POST /api/auth/start        POST /api/auth/verify       POST /api/auth/logout      GET /api/auth/me
POST /api/family            POST /api/family/invite     POST /api/family/join      DELETE /api/family/members/{id}
GET/PUT /api/family/profile GET/PUT /api/family/survey/{side}   GET /api/family/survey/result
POST /api/account/claim-guest-data     GET /api/account/export     DELETE /api/account
```
The Postman collection and `scripts/smoke.py` gain an authenticated path; the guest path in smoke stays as it is.

## 7. Schema change risk
D-35 says no migrations: tables come from `create_all`. New tables will be created on the next deploy, but **adding columns to `Booking` and `Deposit` will not happen on the existing Render Postgres**. Two safe options: (a) add Alembic and a first migration; (b) a one-off `ALTER TABLE ... ADD COLUMN` script run once. Recommend (a) now, since further changes will follow. A local SQLite file must still be deleted when models change.

## 8. Security checklist
- Codes and invite tokens and session ids stored hashed; compare in constant time.
- Same response and similar timing for known and unknown emails.
- Rate limits on start, verify, invite join; lock after repeated bad codes.
- No email, name or token in logs, URLs, analytics, LLM prompts or the Zapier hook.
- Cookie flags as in 6.2; `Cache-Control: no-store` on `/api/auth/*` and `/api/family/*`.
- Clickjacking and content headers on the HTML shell (`X-Frame-Options`, a restrictive CSP that still allows the PayPal SDK, AG Grid and Bryntum).
- Secrets only in `.env`; mailer key name added to `.env.example` and `KEYS_CHECKLIST.md`.
- PayPal stays sandbox-only (`PAYPAL_ENV=sandbox`); auth work must not touch that guard.

## 9. Tests
- Role matrix: a parametrised test per route and role (guest, student, parent, parent of another family) with the expected status.
- Student cannot pay, book, complete, cancel or confirm an agent order; cannot read another family's data.
- Code expiry, attempt burn, rate limit, no account enumeration (identical bodies).
- Invite single use, expiry, wrong role, a minor cannot exist without a consent record.
- Session rotation on login, logout invalidates, expired session rejected.
- CSRF header required on writes; webhook still works without a session.
- Guest-data claim moves rows once and only for a parent.
- Survey privacy: no side visible before both submit.
- Existing 101 tests and the smoke script pass unchanged in guest mode.
- Browser checks: parent and student in two browser profiles, both languages, phone width.

## 10. Phases and effort

| Phase | Scope | Effort |
|---|---|---|
| 0 | Decisions A1 to A8, counsel check on section 5, mail provider account and key | 0.5 day plus waiting |
| 1 | User, AuthCode, Session tables; email code flow; mock mailer; `/me`; login page; cookie and CSRF | 1.5 days |
| 2 | Family, Invite, Consent; invite and join; role guards on payments, deposits, agent confirm | 2 days |
| 3 | Family profile and private-then-shared survey on the server; frontend family panel | 1.5 days |
| 4 | Guest-data claim; export and delete; Alembic migration; headers and CSP | 1.5 days |
| 5 | Test matrix, Postman, smoke, browser checks in two profiles, README and demo script update | 1 day |

About 8 days of work; phases 1 and 2 alone give separate logins with enforced roles (3.5 days).

## 11. Risks
- **Email delivery** to student mailboxes can land in spam; mitigate with a clear sender name and a resend limit message.
- **Scope creep into counsellor accounts.** Keep it out; D-33 says no real counsellors exist yet.
- **Judges and demo.** Any friction in the demo path costs more than accounts add. Keep guest mode default until the hackathon is judged.
- **Migration on live Postgres** (section 7).
- **Legal.** Children's data duties are unverified here (section 5).
- **Lost devices and shared emails.** A family sharing one email cannot have two roles; document it and offer a second email.

## 12. Questions for you
1. Email code as the only login in v1, or add Google sign-in at the same time?
2. Students under 18: parent-invite only (recommended), or may they sign up alone with a consent checkbox?
3. Must a parent sign in to pay, with guest checkout removed after the hackathon?
4. Survey: private until both submit (recommended), or visible to the parent immediately?
5. Which email provider can you create a key for, and is a custom sender domain available?
6. Start after the deadline (recommended), or build phases 1 and 2 on a branch now?
