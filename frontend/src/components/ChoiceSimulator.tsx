import type { Strings } from "../i18n";
import { useEffect, useState } from "react";
import { choiceOrder, type Card, type ChoiceResult, type Profile } from "../api";

interface Props { s: Strings; colleges: Card[]; profile: Profile }

export default function ChoiceSimulator({ s, colleges, profile }: Props) {
  const [order, setOrder] = useState<string[]>([]);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const [res, setRes] = useState<ChoiceResult | null>(null);
  const name = (id: string) => colleges.find((c) => c.id === id)?.short_name ?? id;

  useEffect(() => { // keep the list in sync with available colleges
    setOrder((o) => { const keep = o.filter((id) => colleges.some((c) => c.id === id)); return keep.length ? keep : colleges.map((c) => c.id); });
  }, [colleges.map((c) => c.id).join(",")]);

  useEffect(() => {
    if (!order.length) return;
    choiceOrder(order, profile).then(setRes).catch(() => setRes(null));
  }, [order.join(","), profile.percentile, profile.jee_advanced_rank, profile.home_state]);

  const move = (from: number, to: number) => {
    if (to < 0 || to >= order.length || from === to) return;
    const next = [...order]; const [x] = next.splice(from, 1); next.splice(to, 0, x); setOrder(next);
  };
  const badge = (id: string) => res?.items.find((i) => i.id === id)?.fit;

  return (
    <section className="card" aria-label="Choice-filling simulator">
      <div className="row"><h2 style={{ fontSize: 13, textTransform: "uppercase" }}>{s.choiceTitle}</h2>
        <button className="link" onClick={() => res && setOrder(res.suggested_order)}>Apply suggested order</button></div>
      <p className="note">Drag rows (or use the arrows) to rank your preferences. Seats are allotted top-down, so an easier option above a harder one can lock you out of it.</p>
      <div className="split">
        <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {order.map((id, i) => (
            <li key={id} draggable onDragStart={() => setDragFrom(i)} onDragOver={(e) => e.preventDefault()}
                onDrop={() => { if (dragFrom !== null) move(dragFrom, i); setDragFrom(null); }}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", border: "1px solid var(--hairline)", borderRadius: 12, marginBottom: 6, background: "#fff", cursor: "grab" }}>
              <span className="mono note" style={{ width: 22 }}>{i + 1}</span>
              <span style={{ flex: 1, color: "var(--ink)", fontWeight: 600, fontSize: 14 }}>{name(id)}</span>
              {badge(id) && <span className={`tier ${badge(id)}`}>{badge(id)}</span>}
              <button className="link" aria-label={`Move ${name(id)} up`} onClick={() => move(i, i - 1)}>▲</button>
              <button className="link" aria-label={`Move ${name(id)} down`} onClick={() => move(i, i + 1)}>▼</button>
            </li>
          ))}
        </ol>
        <div aria-live="polite">
          {res?.alerts.length === 0 && <div className="clock"><span>No order inversions found</span><span>✓</span></div>}
          {res?.alerts.map((a, i) => (
            <div key={i} role="alert" style={{ padding: 10, borderRadius: 12, marginBottom: 8, fontSize: 13,
              background: a.severity === "high" ? "#fffbeb" : "#f8fafc", border: `1px solid ${a.severity === "high" ? "#fcd34d" : "var(--hairline)"}`, color: "var(--ink)" }}>
              <strong style={{ color: "var(--amber)" }}>{a.severity === "high" ? "Risky order" : "Check this order"}</strong><br />{a.message}
            </div>
          ))}
          {res?.notes.map((n) => <p className="note" key={n}>{n}</p>)}
        </div>
      </div>
    </section>
  );
}
