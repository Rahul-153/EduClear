import { useMemo } from "react";
import { BryntumGantt } from "@bryntum/gantt-react";
import "@bryntum/gantt/gantt.css";
import "@bryntum/gantt/stockholm-light.css";
import type { BookingView, Timeline, TimelineEvent } from "../api";

/* Bryntum Gantt for the counselling cycle (FR-07). Official JoSAA / CSAB / JEE Main dates are grouped per round and linked:
   a round's allotment starts its reporting window and its seat-fee deadline closes it, so a missed deposit visibly
   ends that path. The user's own paid and unpaid counselling sessions sit in a last group, coloured by PayPal state. */
const COLOUR: Record<string, string> = { deposit_window: "orange", allotment: "blue", reporting: "indigo", withdrawal: "gray", exam: "green" };
const BOOKING_COLOUR: Record<string, string> = { pending: "orange", escrow_funded: "teal", paid: "teal", released: "blue", payout_failed: "red" };
const BOOKING_LABEL: Record<string, string> = { pending: "awaiting payment", escrow_funded: "paid · escrow", paid: "paid", released: "released", payout_failed: "release failed" };
const DAY = 86400000;
const SS = 0, FS = 2; // Bryntum dependency types: start-to-start, finish-to-start

const at = (d: string) => new Date(d + "T00:00:00");
const leaf = (e: TimelineEvent, name = e.label) => ({
  id: e.id, name, startDate: at(e.start), endDate: new Date(at(e.end ?? e.start).getTime() + DAY),
  manuallyScheduled: true, eventColor: COLOUR[e.kind] ?? "gray", cls: e.status === "past" ? "edu-past" : "",
});

function build(t: Timeline, bookings: BookingView[]) {
  const byId = new Map(t.events.map((e) => [e.id, e]));
  const groups: Record<string, unknown>[] = [];
  const deps: Record<string, unknown>[] = [];
  const link = (from: string, to: string, type: number) => { if (byId.has(from) && byId.has(to)) deps.push({ id: `${from}>${to}`, fromTask: from, toTask: to, type }); };

  const pre = byId.get("josaa-prepay");
  if (pre) groups.push(leaf(pre, "Seat-fee pre-payment & document upload"));

  for (let r = 1; r <= 5; r++) {
    const kids = t.events.filter((e) => e.id.startsWith(`josaa-r${r}-`) && !e.id.endsWith("paf"));
    if (!kids.length) continue;
    groups.push({ id: `grp-josaa-r${r}`, name: `JoSAA Round ${r}`, expanded: r <= 2, children: kids.map((e) => leaf(e, e.label.replace(`JoSAA Round ${r} `, ""))) });
    link(`josaa-r${r}-allotment`, `josaa-r${r}-reporting`, SS);
    link(`josaa-r${r}-reporting`, `josaa-r${r}-deposit-deadline`, SS);
    if (r > 1) link(`josaa-r${r - 1}-deposit-deadline`, `josaa-r${r}-allotment`, FS);
  }
  const paf = byId.get("josaa-r5-nitplus-paf");
  if (paf) groups.push(leaf(paf, "NIT+ Partial Admission Fee"));

  const csab = t.events.filter((e) => e.id.startsWith("csab-"));
  if (csab.length) groups.push({ id: "grp-csab", name: "CSAB Special Rounds", expanded: true, children: csab.map((e) => leaf(e)) });
  link("csab-special-r1-allotment", "csab-special-r1-reporting", SS);
  link("csab-special-r2-allotment", "csab-special-r2-reporting", SS);

  const jee = t.events.filter((e) => e.kind === "exam");
  if (jee.length) groups.push({ id: "grp-jee", name: "JEE Main 2027 — Session 1", expanded: true, children: jee.map((e) => leaf(e, e.label.replace("JEE (Main) 2027 Session 1 ", ""))) });

  const mine = bookings.filter((b) => b.program !== "tech-kit" && b.slot_start && b.status !== "cancelled");
  if (mine.length) groups.push({
    id: "grp-mine", name: "Your counselling sessions", expanded: true,
    children: mine.map((b) => ({ id: `b${b.id}`, name: `${b.title} · ${BOOKING_LABEL[b.status] ?? b.status}`, startDate: new Date(b.slot_start!),
      endDate: new Date(new Date(b.slot_start!).getTime() + 3600000), manuallyScheduled: true, eventColor: BOOKING_COLOUR[b.status] ?? "gray" })),
  });
  return { tasks: groups, dependencies: deps };
}

export default function AdmissionsGantt({ t, bookings }: { t: Timeline; bookings: BookingView[] }) {
  const { tasks, dependencies } = useMemo(() => build(t, bookings), [t, bookings]);
  return (
    <BryntumGantt
      height={520}
      tasks={tasks as never} dependencies={dependencies as never}
      viewPreset="weekAndMonth" rowHeight={34} barMargin={6}
      columns={[{ type: "name", text: "Step", width: 290 }, { type: "startdate", text: "Start", width: 120 }, { type: "enddate", text: "End", width: 100, hidden: true }]}
      readOnly
      taskDragFeature={false} taskResizeFeature={false} taskEditFeature={false} taskMenuFeature={false} cellMenuFeature={false}
      dependenciesFeature={{ allowCreate: false }} projectLinesFeature={false}
      timeRangesFeature={{ showCurrentTimeLine: true }}
    />
  );
}
