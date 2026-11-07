import { lazy, Suspense, useEffect, useState } from "react";
import { myBookings, timeline, type BookingView, type Timeline, type TimelineEvent } from "../api";
import Boundary from "./Boundary";
import { inr } from "../lib/format";

const AdmissionsGantt = lazy(() => import("./AdmissionsGantt"));

const COLOR: Record<string, string> = { deposit_window: "#d97706", allotment: "#0f172a", reporting: "#475569", withdrawal: "#94a3b8", exam: "#059669" };
const day = (d: string) => new Date(d + "T00:00:00").getTime();
const fmt = (d: string) => new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

/* Simple-bars view of the same data: the default is the Bryntum Gantt, this stays as a lightweight fallback. */
function Lane({ title, events }: { title: string; events: TimelineEvent[] }) {
  if (!events.length) return null;
  const lo = Math.min(...events.map((e) => day(e.start)));
  const hi = Math.max(...events.map((e) => day(e.end ?? e.start))) + 86400000;
  return (
    <div style={{ marginTop: 16 }}>
      <div className="label" style={{ marginBottom: 6 }}>{title}</div>
      {events.map((e) => {
        const left = ((day(e.start) - lo) / (hi - lo)) * 100;
        const width = Math.max(1.2, (((day(e.end ?? e.start) + 86400000) - day(e.start)) / (hi - lo)) * 100);
        return (
          <div key={e.id} style={{ display: "grid", gridTemplateColumns: "minmax(140px, 36%) 1fr", gap: 10, alignItems: "center", padding: "3px 0" }}>
            <div style={{ fontSize: 12 }}>
              <span style={{ color: "var(--ink)", fontWeight: 500 }}>{e.label}</span>
              <div className="note num">{fmt(e.start)}{e.end && e.end !== e.start ? ` – ${fmt(e.end)}` : ""}
                {e.status === "upcoming" ? ` · in ${e.days_until_start} d` : e.status === "ongoing" ? " · now" : ""}</div>
            </div>
            <div style={{ position: "relative", height: 12, background: "#f1f5f9", borderRadius: 6 }} title={e.source.locator}>
              <div style={{ position: "absolute", left: `${left}%`, width: `${Math.min(width, 100 - left)}%`, height: "100%", borderRadius: 6,
                background: COLOR[e.kind] ?? "#475569", opacity: e.status === "past" ? 0.45 : 1 }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function AdmissionsTimeline() {
  const [t, setT] = useState<Timeline | null>(null);
  const [rows, setRows] = useState<BookingView[]>([]);
  const [view, setView] = useState<"gantt" | "bars">("gantt");
  useEffect(() => { timeline().then(setT).catch(() => setT(null)); }, []);
  useEffect(() => { const load = () => myBookings().then(setRows).catch(() => setRows([])); load(); const i = window.setInterval(load, 15000); return () => window.clearInterval(i); }, []);
  if (!t) return <section className="card"><div className="empty">Admissions timeline unavailable.</div></section>;
  const upcoming = t.events.filter((e) => e.kind === "exam");
  const cycle = t.events.filter((e) => e.kind !== "exam");
  return (
    <section className="card" aria-label="Admissions and deposit timeline">
      <div className="row"><div><h2 style={{ fontSize: 13, textTransform: "uppercase" }}>Admissions & deposit timeline</h2>
        <div className="note">{t.disclaimer}</div></div><span className="badge">Retrieved {t.retrieved_at}</span></div>
      <div className="split" style={{ marginTop: 12 }}>
        <div className="card" style={{ boxShadow: "none" }}>
          <div className="label">JoSAA seat acceptance fee ({t.cycle})</div>
          <div className="row"><span>General / OBC-NCL / EWS</span><span className="num value">{inr(t.seat_acceptance_fee.generalInr)}</span></div>
          <div className="row"><span>SC / ST / PwD categories</span><span className="num value">{inr(t.seat_acceptance_fee.reservedInr)}</span></div>
          <details className="note"><summary>Official rule text</summary>{t.seat_acceptance_fee.rule_text} <a href={t.seat_acceptance_fee.url} target="_blank" rel="noreferrer">JoSAA business rules ↗</a></details>
        </div>
        <div className="card" style={{ boxShadow: "none", background: "#fffbeb" }}>
          <div className="label" style={{ color: "var(--amber)" }}>Deposit deadlines (amber bars)</div>
          <p className="note" style={{ color: "var(--ink)" }}>Each round’s fee must be paid by 17:00 IST on the deadline date. Missing it rejects the seat. Dates below are the 2026 cycle; 2027 dates are not yet published.</p>
        </div>
      </div>
      <div className="row" style={{ marginTop: 16 }}>
        <div className="label">{view === "gantt" ? `Gantt · ${t.cycle} counselling cycle and JEE Main 2027 · linked rounds, today marked` : "Simple bars"}</div>
        <button className="link" onClick={() => setView(view === "gantt" ? "bars" : "gantt")}>{view === "gantt" ? "Show simple bars" : "Show Gantt"}</button>
      </div>
      {view === "gantt" ? (
        <Boundary name="Admissions Gantt">
          <Suspense fallback={<div className="empty">Loading Gantt…</div>}><AdmissionsGantt t={t} bookings={rows} /></Suspense>
        </Boundary>
      ) : (<>
        <Lane title="Coming up: JEE Main 2027 Session 1" events={upcoming} />
        <Lane title={`Latest published counselling cycle (${t.cycle}) — for planning the next one`} events={cycle} />
      </>)}
    </section>
  );
}
