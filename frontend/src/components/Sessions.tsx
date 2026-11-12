import { lazy, Suspense, useEffect, useState } from "react";
import { bookSlot, completeBooking, myBookings, payConfig, programs, slotsFor, type BookingView, type PayConfig, type Program, type Slot } from "../api";
import CheckoutPanel from "./CheckoutPanel";
import Boundary from "./Boundary";
import type { Strings } from "../i18n";

const BookingScheduler = lazy(() => import("./BookingScheduler"));

const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) + " IST";
const statusLabel = (x: Strings, st: string) => ({ pending: x.stPending, escrow_funded: x.stEscrow, paid: x.stPaid, payout_failed: x.stFailed, released: x.stReleased, cancelled: x.stCancelled } as Record<string, string>)[st] ?? st;

export default function Sessions({ s: str, access }: { s: Strings; access: "book" | "ask_parent" | "sign_in" }) {
  const canBook = access === "book";
  const [cfg, setCfg] = useState<PayConfig | null>(null);
  const [progs, setProgs] = useState<Program[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [rows, setRows] = useState<BookingView[]>([]);
  const [active, setActive] = useState<BookingView | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const reload = () => myBookings().then(setRows).catch(() => setRows([]));
  useEffect(() => { payConfig().then(setCfg); programs().then(setProgs); reload(); }, []);
  useEffect(() => { if (open) slotsFor(open).then(setSlots); }, [open]);
  // payment state changes outside this tab (PayPal webhook, expiry), so keep the calendar and list fresh
  useEffect(() => { const t = window.setInterval(reload, 15000); return () => window.clearInterval(t); }, []);

  const reserve = async (s: Slot, programId = open!) => {
    setErr(null);
    try { setActive(await bookSlot(programId, s.start)); setOpen(programId); reload(); } catch (e) { setErr((e as Error).message); }
  };
  const settle = (b: BookingView | null) => { setActive(b && b.status !== "pending" ? null : b); reload(); if (open) slotsFor(open).then(setSlots); };
  const release = async (id: number) => { setErr(null); try { await completeBooking(id); reload(); } catch (e) { setErr((e as Error).message); reload(); } };

  return (
    <section aria-label="Counselling sessions and career workshops">
      <h2 style={{ fontSize: 13, textTransform: "uppercase" }}>{str.sessionsTitle}</h2>
      <p className="note">{cfg?.counsellor} · {cfg?.escrow_note}</p>
      <div className="grid3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))" }}>
        {progs.map((p) => (
          <article key={p.id} className="card hover">
            <div className="row"><span className="label">{p.kind === "cohort" ? "Cohort" : "1:1"} · {p.minutes} min</span>
              <span className="badge">{p.escrow ? "Escrow" : "Direct"}</span></div>
            <h3 style={{ fontSize: 15, margin: "6px 0" }}>{p.title}</h3>
            <p className="note">{p.summary}</p>
            <div className="row"><span className="label">{p.kind === "cohort" ? "Per seat" : "Session fee"}</span>
              <span className="num value">₹{p.price_inr.toLocaleString("en-IN")} <span className="note">(${p.usd})</span></span></div>
            {canBook ? (
              <button className="capsule" style={{ width: "100%", padding: 8, border: "1px solid var(--hairline)", fontWeight: 600 }} onClick={() => { setOpen(open === p.id ? null : p.id); setActive(null); }}
                aria-expanded={open === p.id}>{open === p.id ? str.hideTimes : p.escrow ? str.chooseTime : str.reserveSeat}</button>
            ) : access === "sign_in" ? <p className="note"><a href="#login">{str.signInToBook}</a></p> : <p className="note">{str.askParent}</p>}
          </article>
        ))}
      </div>
      {canBook && progs.length > 0 && (
        <Boundary name="Booking calendar">
          <Suspense fallback={<div className="card empty" style={{ marginTop: 16 }}>Loading booking calendar…</div>}>
            <BookingScheduler s={str} programs={progs} bookings={rows} onPick={(pid, s) => reserve(s, pid)} />
          </Suspense>
        </Boundary>
      )}
      {canBook && open && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="label">{str.availableTimes}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {slots.map((s) => (
              <button key={s.start} disabled={s.left === 0} onClick={() => reserve(s)} className="capsule"
                style={{ padding: "6px 12px", border: "1px solid var(--hairline)", opacity: s.left === 0 ? 0.4 : 1 }}>
                {when(s.start)}{progs.find((p) => p.id === open)?.kind === "cohort" ? ` · ${s.left} seats` : ""}
              </button>
            ))}
          </div>
          {active && cfg && <CheckoutPanel booking={active} cfg={cfg} onChange={settle} />}
        </div>
      )}
      {err && <p role="alert" className="note" style={{ color: "var(--amber)" }}>{err}</p>}
      {rows.filter((b) => b.program !== "tech-kit").length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="label">{str.yourBookings}</div>
          {rows.filter((b) => b.program !== "tech-kit").map((b) => (
            <div key={b.id} className="row" style={{ borderTop: "1px solid var(--hairline)", paddingTop: 8 }}>
              <span><strong style={{ color: "var(--ink)" }}>{b.title}</strong><div className="note">{b.slot_start ? when(b.slot_start) : ""} · {statusLabel(str, b.status)}</div></span>
              <span>{["escrow_funded", "payout_failed"].includes(b.status) &&
                <button className="link" onClick={() => release(b.id)}>{str.releaseFunds}</button>}
                {b.status === "released" && <span className="note num">payout {b.payout_batch_id}</span>}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
