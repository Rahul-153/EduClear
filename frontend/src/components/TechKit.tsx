import type { Strings } from "../i18n";
import { useEffect, useState } from "react";
import { getKit, orderKit, payConfig, type BookingView, type Kit, type PayConfig } from "../api";
import { inr } from "../lib/format";
import CheckoutPanel from "./CheckoutPanel";

export default function TechKit({ s }: { s: Strings }) {
  const [kit, setKit] = useState<Kit | null>(null);
  const [cfg, setCfg] = useState<PayConfig | null>(null);
  const [order, setOrder] = useState<(BookingView & { pay_in_4_usd: string }) | null>(null);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { getKit().then(setKit); payConfig().then(setCfg); }, []);
  if (!kit?.supported) return null;
  const start = async () => { setErr(null); setDone(false); try { setOrder(await orderKit(kit.items.map((i) => i.id))); } catch (e) { setErr((e as Error).message); } };
  return (
    <section className="card" aria-label="Student tech kit">
      <div className="row"><h2 style={{ fontSize: 13, textTransform: "uppercase" }}>{s.kitTitle}</h2>
        <span className={`badge ${kit.sample_data ? "" : "green"}`}>{kit.sample_data ? "Sample listings" : "Live Channel3 prices"}</span></div>
      {kit.items.map((i) => (
        <div className="row" key={i.id} style={{ borderTop: "1px solid var(--hairline)", paddingTop: 8 }}>
          <span><strong style={{ color: "var(--ink)" }}>{i.title}</strong><div className="note">{i.requirement} · source: {i.source}{i.currency_note ? ` · ${i.currency_note}` : ""}</div></span>
          <span className="num value">{inr(i.price_inr)}</span>
        </div>
      ))}
      <div className="row" style={{ marginTop: 8 }}><span className="label">Kit total</span><span className="num value">{inr(kit.total_inr)}</span></div>
      <p className="note">{kit.note} Pay Later (4 interest-free instalments) is offered by PayPal only when you are eligible; at checkout it would be about {inr(kit.pay_in_4_inr)} per instalment.</p>
      {!order && !done && <button className="capsule" style={{ padding: "8px 16px", background: "#FFC439", border: 0, fontWeight: 600 }} onClick={start}>Checkout with PayPal / Pay Later</button>}
      {order && cfg && !done && <CheckoutPanel booking={order} cfg={cfg} payLaterHint={`In 4 payments of $${order.pay_in_4_usd} if eligible.`} onChange={(b) => { if (!b || b.status !== "pending") { setOrder(null); setDone(!!b); } }} />}
      {done && <div className="clock"><span>Kit order paid in the PayPal sandbox</span><span>✓</span></div>}
      {err && <p role="alert" className="note" style={{ color: "var(--amber)" }}>{err}</p>}
    </section>
  );
}
