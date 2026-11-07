import { useEffect, useMemo, useRef, useState } from "react";
import { Scheduler } from "@bryntum/gantt";
import "@bryntum/gantt/gantt.css";
import "@bryntum/gantt/stockholm-light.css";
import { slotsFor, type BookingView, type Program, type Slot } from "../api";

/* The Bryntum trial ships Scheduler inside the Gantt bundle, and two Bryntum bundles cannot share a page, so this uses the
   Scheduler class from @bryntum/gantt directly (no React wrapper).
   Bryntum Scheduler booking calendar (FR-10): one row per session programme. A slot is only bookable while seats are left;
   a booking changes colour as PayPal reports it (awaiting payment -> funds in escrow -> released), so payment state is
   visible on the schedule itself. Cancelled bookings drop off, which frees their slot. */
const COLOUR: Record<string, string> = { open: "green", full: "gray", pending: "orange", escrow_funded: "teal", paid: "teal", released: "blue", payout_failed: "red" };
const LABEL: Record<string, string> = { pending: "Awaiting payment", escrow_funded: "Paid · escrow", paid: "Paid", released: "Released", payout_failed: "Release failed" };
const DAY_MS = 86400000;

interface Props { programs: Program[]; bookings: BookingView[]; onPick: (programId: string, slot: Slot) => void }

export default function BookingScheduler({ programs, bookings, onPick }: Props) {
  const [slots, setSlots] = useState<Record<string, Slot[]>>({});
  const host = useRef<HTMLDivElement>(null);
  const sched = useRef<Scheduler | null>(null);
  const pick = useRef(onPick);
  pick.current = onPick;
  const key = bookings.map((b) => `${b.id}:${b.status}`).join(",");

  useEffect(() => {
    let dead = false;
    Promise.all(programs.map((p) => slotsFor(p.id).then((s) => [p.id, s] as const)))
      .then((all) => { if (!dead) setSlots(Object.fromEntries(all)); }).catch(() => undefined);
    return () => { dead = true; };
  }, [programs, key]);

  const { events, first } = useMemo(() => {
    const mine = new Map(bookings.filter((b) => b.status !== "cancelled" && b.slot_start).map((b) => [`${b.program}|${b.slot_start}`, b]));
    const ev: Record<string, unknown>[] = [];
    let lo = Infinity;
    for (const p of programs) {
      for (const s of slots[p.id] ?? []) {
        const start = new Date(s.start);
        lo = Math.min(lo, start.getTime());
        const b = mine.get(`${p.id}|${s.start}`);
        const state = b ? b.status : s.left > 0 ? "open" : "full";
        ev.push({
          id: `${p.id}|${s.start}`, resourceId: p.id, startDate: start, endDate: new Date(start.getTime() + p.minutes * 60000),
          name: b ? `Yours · ${LABEL[b.status] ?? b.status}` : s.left > 0 ? (p.kind === "cohort" ? `${s.left} seats` : "Open") : "Full",
          eventColor: COLOUR[state] ?? "gray", state, programId: p.id, slotStart: s.start, left: s.left,
        });
      }
    }
    return { events: ev, first: Number.isFinite(lo) ? new Date(lo) : new Date() };
  }, [programs, slots, bookings]);

  const [offset, setOffset] = useState(0);
  const day0 = new Date(first); day0.setHours(0, 0, 0, 0);
  const start = new Date(day0.getTime() + offset * DAY_MS + 8 * 3600000);
  const end = new Date(day0.getTime() + (offset + 3) * DAY_MS - 4 * 3600000);

  useEffect(() => {
    if (!host.current) return;
    const s = new Scheduler({
      appendTo: host.current, height: 40 + programs.length * 56, startDate: start, endDate: end,
      viewPreset: { base: "hourAndDay", tickWidth: 84, displayDateFormat: "ll HH:mm" } as never,
      rowHeight: 52, barMargin: 6, eventLayout: "stack", readOnly: true,
      columns: [{ text: "Programme", field: "title", width: 190 }],
      resources: programs.map((p) => ({ id: p.id, title: p.title })),
      events: [],
      features: { eventDrag: false, eventResize: false, eventEdit: false, eventMenu: false, scheduleMenu: false,
        eventTooltip: { template: ({ eventRecord }: { eventRecord: { name: string; startDate: Date } }) =>
          `${eventRecord.name} · ${eventRecord.startDate.toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })} IST` } } as never,
      listeners: {
        eventClick: ({ eventRecord }: { eventRecord: { data: { state: string; programId: string; slotStart: string; left: number } } }) => {
          const d = eventRecord.data;
          if (d.state === "open") pick.current(d.programId, { start: d.slotStart, left: d.left });
        },
      } as never,
    });
    sched.current = s;
    return () => { s.destroy(); sched.current = null; };
  }, [programs]);

  useEffect(() => { const s = sched.current; if (s) { s.events = events as never; s.setTimeSpan(start, end); } }, [events, offset]);

  return (
    <div className="card" style={{ marginTop: 16 }} aria-label="Booking calendar">
      <div className="row">
        <div className="label">Booking calendar · click an open slot to reserve it</div>
        <span style={{ display: "flex", gap: 8 }}>
          <button className="link" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 3))}>← Earlier</button>
          <button className="link" onClick={() => setOffset(offset + 3)}>Later →</button>
        </span>
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "6px 0 10px" }} className="note">
        <span>🟩 open</span><span>🟧 awaiting payment</span><span>🟦 paid, held in escrow</span><span>🔵 released</span><span>⬜ full</span>
      </div>
      <div ref={host} />
    </div>
  );
}
