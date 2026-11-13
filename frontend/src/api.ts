export interface Fit { tier: "Safe" | "Target" | "Reach" | "Out of reach" | null; reason: string | null; quota?: string; closing_rank_used?: number; approx_user_rank?: number }
export interface Payback { total_cost_inr: number; median_base_lpa: number; in_hand_monthly_inr: number; disposable_monthly_inr: number; payback_months: number; payback_months_gross_pay: number }
export type DataLevel = "audited" | "supplied" | "partly_verified" | "cutoffs_only";
export interface CutoffOption {
  institute: string; kind: string; program: string; quota: string; seat_type: string; gender: string; closing_rank: number; user_rank: number;
  tier: "Safe" | "Target" | "Reach"; data_level: DataLevel; source: string; source_url: string;
  nirf_rank?: number | null;
  placement?: { batch: string; placed: number; eligible: number; placement_rate: number; median_base_lpa: number; source_url: string };
}
export interface Card {
  id: string; data_level: DataLevel; name: string; short_name: string; city_state: string; region: string; nirf_rank: number; fit: Fit;
  four_year_cost_inr: number; headline_ctc_lpa: number; median_base_lpa: number; placed: number; eligible: number;
  placement_rate: number; payback: Payback; source_url: string; accreditation: string; commercial_relationship: string;
  why?: { en: string; hi: string };
  branch_scope?: boolean;  // placement and payback are this branch's own figures, not the institute-wide ones
}
export interface Recommendation {
  supported: boolean; message?: string;
  deck: { safe_anchor: Card | null; sweet_spot: Card | null; dream_reach: Card | null };
  matches: Card[]; needs_more_input: { id: string; reason: string }[];
  cutoff_only?: { items: CutoffOption[]; iits_need_rank: boolean };
}
export interface Assumptions { savings_rate: number; salary_growth: number }
export interface Profile {
  stream: string; percentile: number; budget_lakhs: number; region: string;
  home_state: string; jee_advanced_rank: string; bitsat_score: string;
  seat_type: string; gender: string; category_rank: string;
}
export interface Roi { payback: Payback; trajectory: { points: { year: number; salary_lpa: number }[]; note: string } }
export interface Sources { retrieved_at: string; nirf_year: number | null; verification: string; provenance: Record<string, { url: string; locator: string }> }

async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-Requested-With": "educlear" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

export const recommend = (p: Profile, a: Assumptions) =>
  post<Recommendation>("/api/recommend", {
    stream: p.stream, percentile: p.percentile, budget_lakhs: p.budget_lakhs, region: p.region,
    home_state: p.home_state || null,
    jee_advanced_rank: p.jee_advanced_rank ? Number(p.jee_advanced_rank) : null,
    bitsat_score: p.bitsat_score ? Number(p.bitsat_score) : null,
    seat_type: p.seat_type, gender: p.gender, category_rank: p.category_rank ? Number(p.category_rank) : null,
    assumptions: a,
  });
export const roi = (id: string, a: Assumptions) => post<Roi>("/api/roi", { college_id: id, assumptions: a });
export const alignment = (student: Record<string, number>, parent: Record<string, number>, college_ids: string[] = []) =>
  post<{ alignment_score: number; verdict: string; discussion_guide: { dimension: string; gap: number; higher_priority: string; prompt: string }[];
    brief: { dimension: string; en: string; hi: string }[] }>("/api/alignment", { student, parent, college_ids });
export const sources = (id: string) => fetch(`/api/colleges/${id}/sources`).then((r) => r.json() as Promise<Sources>);

export interface ChoiceResult {
  items: { position: number; id: string; name: string; basis: string | null; closing_rank: number | null; fit: string | null }[];
  alerts: { severity: "high" | "medium"; message: string; easier_option: string; harder_option: string }[];
  suggested_order: string[]; notes: string[];
}
export const choiceOrder = (ids: string[], p: Profile) =>
  post<ChoiceResult>("/api/choice-order", {
    college_ids: ids, percentile: p.percentile, home_state: p.home_state || null,
    jee_advanced_rank: p.jee_advanced_rank ? Number(p.jee_advanced_rank) : null,
  });

export interface TimelineEvent { id: string; label: string; kind: string; start: string; end: string | null; status: "upcoming" | "ongoing" | "past";
  days_until_start: number; days_until_end: number; note?: string; source: { url: string; locator: string } }
export interface Timeline { cycle: string; retrieved_at: string; disclaimer: string; events: TimelineEvent[];
  seat_acceptance_fee: { generalInr: number; reservedInr: number; url: string; rule_text: string } }
export const timeline = () => fetch("/api/admissions/timeline").then((r) => r.json() as Promise<Timeline>);

export interface DepositView {
  id: number; college_id: string; amount_inr: number; paid_on: string; closure_date: string; note: string | null; alert: boolean;
  refund_if_withdrawn_today: { refund_percent: number; window: string; gross_refund_inr: number; max_processing_fee_inr: number; minimum_net_refund_inr: number };
  milestones: { tier_id: string; refund_percent: number; last_day: string; days_left: number }[];
  next_cutoff: { refund_percent: number; last_day: string; days_left: number } | null;
}
const cid = () => {
  try {
    let v = localStorage.getItem("educlear-client");
    if (!v) { v = crypto.randomUUID(); localStorage.setItem("educlear-client", v); }
    return v;
  } catch { return "anonymous-session-" + Math.random().toString(36).slice(2); }
};
const H = () => ({ "Content-Type": "application/json", "X-Client-Id": cid(), "X-Requested-With": "educlear" });  // the second header is the CSRF check for signed-in sessions
export const listDeposits = () => fetch("/api/deposits", { headers: H() }).then((r) => r.json() as Promise<DepositView[]>);
export const addDeposit = (b: { college_id: string; amount_inr: number; paid_on: string; closure_date: string }) =>
  fetch("/api/deposits", { method: "POST", headers: H(), body: JSON.stringify(b) }).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); });
export const deleteDeposit = (id: number) => fetch(`/api/deposits/${id}`, { method: "DELETE", headers: H() });
export const refundLetter = (b: Record<string, unknown>) =>
  post<{ letter: string; calculation: { refund_percent: number }; disclaimer: string }>("/api/refund-letter", b);

// ---- payments (Phase 5) ----
export interface PayConfig { mode: "mock" | "live-sandbox"; currency_note: string; escrow_note: string; client_id: string | null; counsellor: string }
export interface Program { id: string; title: string; kind: string; minutes: number; price_inr: number; usd: string; escrow: boolean; capacity: number; summary: string }
export interface Slot { start: string; left: number }
export interface BookingView { id: number; program: string; title: string; amount_inr: number; usd: string; slot_start: string | null; status: string;
  paypal_order_id: string; payout_batch_id: string | null; note: string | null; ledger: { kind: string; usd: string; ref: string }[] }
export interface Kit { supported: boolean; items: { id: string; requirement: string; title: string; price_inr: number; url: string | null; source: string; currency_note: string | null }[];
  total_inr: number; sample_data: boolean; note: string; pay_in_4_inr: number }

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, { method, headers: H(), body: body === undefined ? undefined : JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j as { detail?: string }).detail ?? `Request failed (${r.status})`);
  return j as T;
}
export const payConfig = () => fetch("/api/payments/config").then((r) => r.json() as Promise<PayConfig>);
export const programs = () => fetch("/api/programs").then((r) => r.json() as Promise<Program[]>);
export const slotsFor = (id: string) => fetch(`/api/programs/${id}/slots`).then((r) => r.json() as Promise<Slot[]>);
export const bookSlot = (program_id: string, slot_start: string) => call<BookingView>("POST", "/api/bookings", { program_id, slot_start });
export const myBookings = () => call<BookingView[]>("GET", "/api/bookings");
export const mockApprove = (id: number, approve: boolean) => call<unknown>("POST", `/api/bookings/${id}/mock-approve`, { approve });
export const captureBooking = (id: number) => call<BookingView>("POST", `/api/bookings/${id}/capture`);
export const completeBooking = (id: number) => call<BookingView>("POST", `/api/bookings/${id}/complete`);
export const cancelBooking = (id: number) => call<BookingView>("POST", `/api/bookings/${id}/cancel`);
export const getKit = () => fetch("/api/kit").then((r) => r.json() as Promise<Kit>);
export const orderKit = (item_ids: string[]) => call<BookingView & { pay_in_4_usd: string }>("POST", "/api/kit/order", { item_ids });

// ---- intake + agent (Phase 6) ----
export interface IntakeResult { language: "en" | "hi"; profile: { percentile: number | null; budget_lakhs: number | null; region: string | null; stream: string | null;
  home_state: string | null; jee_advanced_rank: number | null; bitsat_score: number | null }; sources: Record<string, string>; missing: string[]; llm_used: boolean; unsupported_stream: boolean; salary_not_budget?: boolean }
export const intake = (text: string) => post<IntakeResult>("/api/intake", { text });
export interface ClaimResult { college?: string; needs_college: boolean; lines: string[]; label?: string; source_url?: string;
  verdicts?: { claim: string; status: "consistent" | "above_record" }[] }
export const checkClaim = (text: string, lang: string) => post<ClaimResult>("/api/claims/check", { text, lang });
export interface AgentReply { profile?: { last_college?: string }; reply: string; tool: string; tool_chosen_by: string; llm: string | null; language: string;
  pending_action?: { id: string; type: string; program_id: string; slot_start: string; amount_inr: number } }
const agentProfile = (p: Profile, last_college?: string) => ({ stream: p.stream, seat_type: p.seat_type, gender: p.gender,
  category_rank: p.category_rank ? Number(p.category_rank) : null, last_college: last_college || null, percentile: p.percentile, budget_lakhs: p.budget_lakhs, region: p.region, home_state: p.home_state || null,
  jee_advanced_rank: p.jee_advanced_rank ? Number(p.jee_advanced_rank) : null, bitsat_score: p.bitsat_score ? Number(p.bitsat_score) : null });
export const agentChat = (message: string, p: Profile, lang: string, last_college?: string) =>
  call<AgentReply>("POST", "/api/agent/chat", { message, profile: agentProfile(p, last_college), lang });
export const agentConfirm = (action_id: string) => call<{ booking: BookingView; note: string }>("POST", "/api/agent/confirm", { action_id });

// ---- accounts (PLAN_AUTH.md) ----
export type Role = "student" | "parent";
export interface Me {
  user: { id: number; role: Role; email: string; display_name: string; is_minor: boolean } | null;
  family?: { id: number; members: { id: number; role: Role; name: string; is_minor: boolean; you: boolean }[] } | null;
  guest_checkout: boolean;
  sign_in_available?: boolean;
}
export const getMe = () => call<Me>("GET", "/api/auth/me");
export const authStart = (b: { email: string; role: Role; over18: boolean; display_name: string }) =>
  call<{ ok: boolean; message: string; demo_code?: string }>("POST", "/api/auth/start", b);
export const authVerify = (email: string, code: string) => call<Me>("POST", "/api/auth/verify", { email, code });
export const authLogout = () => call<{ ok: boolean }>("POST", "/api/auth/logout");
export const createFamily = () => call<Me>("POST", "/api/family");
export const makeInvite = () => call<{ code: string; role_to_join: Role; expires_at: string }>("POST", "/api/family/invite");
export const joinFamily = (code: string) => call<Me>("POST", "/api/family/join", { code });
export const removeMember = (id: number) => call<Me>("DELETE", `/api/family/members/${id}`);

// ---- round-by-round coach (Phase 16) ----
export interface RoundSeat { institute: string; program: string; quota: string; inst_type?: string; closing_this_round?: number | null }
export interface RoundHistory {
  basis: "relative_move" | "absolute_rank"; years_reached: number; years_with_data: number; closing_now: number | null; short_by_pct: number | null;
  years: { year: number; available: boolean; closing_at_round?: number; highest_closing_from_round?: number; moved_pct?: number; reached?: boolean }[];
}
export interface RoundAdvice {
  year: number; round: number; total_rounds: number; mode: "replay" | "own_round"; held: number | null; history_years: number[];
  option: { action: "no_seat" | "freeze_only" | "last_round" | "float" | "slide"; rule_ids: string[] };
  choices: (RoundSeat & { position: number; rank_used: number | null; held: boolean; above_held: boolean; history?: RoundHistory | null })[];
  money: { status: "no_seat" | "seat_held"; seat_acceptance_fee_inr: number; withdrawal_charge_inr?: number; refund_on_withdrawal_inr?: number;
    withdrawal_open_this_round?: boolean; withdrawal_first_round?: number; withdrawal_last_round?: number };
  rules: { id: string; clause: string; page: number; quote: string }[]; rules_source: { document: string; url: string };
  source: string; source_url: string; needs_rank: string[];
}
export interface RoundCycles { replay_years: number[]; rounds: Record<string, number>; own_round: { year: number; total_rounds: number } }
export const roundCycles = () => call<RoundCycles>("GET", "/api/rounds/cycles");
export const roundSeats = (year: number, seat_type: string, gender: string) =>
  call<{ items: RoundSeat[] }>("GET", `/api/rounds/seats?year=${year}&seat_type=${encodeURIComponent(seat_type)}&gender=${encodeURIComponent(gender)}`);
export const roundAdvise = (b: Record<string, unknown>) => call<RoundAdvice>("POST", "/api/rounds/advise", b);
export interface RoundSeason { year: number; seat_fee_paid: boolean; institute_deposits: { count: number; total_inr: number };
  rounds: { round: number; held: RoundSeat | null; action_taken: string | null; fee_paid: boolean;
    request: { choices: RoundSeat[]; allotted: number | null; no_seat: boolean; main_rank: number | null; advanced_rank: number | null; seat_type: string; gender: string } }[] }
export const roundSeason = (year: number) => call<RoundSeason>("GET", `/api/rounds/season?year=${year}`);
export const saveRound = (b: Record<string, unknown>) => call<RoundSeason>("PUT", "/api/rounds/season", b);
export const deleteRound = (year: number, round: number) => call<RoundSeason>("DELETE", `/api/rounds/season/${year}/${round}`);
