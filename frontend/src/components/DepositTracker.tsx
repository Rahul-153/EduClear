import type { Strings } from "../i18n";
import { useEffect, useState } from "react";
import { addDeposit, deleteDeposit, listDeposits, refundLetter, type Card, type DepositView } from "../api";
import { inr } from "../lib/format";

const today = () => new Date().toISOString().slice(0, 10);

export default function DepositTracker({ s, colleges }: { s: Strings; colleges: Card[] }) {
  const [rows, setRows] = useState<DepositView[]>([]);
  const [f, setF] = useState({ college_id: "", amount_inr: "30000", paid_on: today(), closure_date: "" });
  const [err, setErr] = useState<string | null>(null);
  const [letterFor, setLetterFor] = useState<DepositView | null>(null);
  const [L, setL] = useState({ student: "", guardian: "", notice: today() });
  const [letter, setLetter] = useState<string | null>(null);
  const reload = () => listDeposits().then(setRows).catch(() => setRows([]));
  useEffect(() => { reload(); }, []);
  const name = (id: string) => colleges.find((c) => c.id === id)?.short_name ?? id;

  const add = async () => {
    setErr(null);
    if (!f.college_id || !f.closure_date) return setErr("Choose a college and the institution’s last date of admission.");
    try { await addDeposit({ ...f, amount_inr: Number(f.amount_inr) }); setF({ ...f, closure_date: "" }); reload(); }
    catch { setErr("Could not save the deposit."); }
  };
  const makeLetter = async () => {
    if (!letterFor || !L.student) return;
    const r = await refundLetter({ student_name: L.student, guardian_name: L.guardian || null, college_name: name(letterFor.college_id) + " (full name as on your offer letter)",
      amount_inr: letterFor.amount_inr, paid_on: letterFor.paid_on, closure_date: letterFor.closure_date, notice_date: L.notice });
    setLetter(r.letter + "\n\n— " + r.disclaimer);
  };

  return (
    <section className="card" aria-label="Seat deposit and refund tracker">
      <h2 style={{ fontSize: 13, textTransform: "uppercase" }}>{s.depositTitle}</h2>
      <p className="note">Saved only against an anonymous ID in this browser. Under UGC rules the refund share drops on fixed dates around your institution’s last date of admission.</p>
      <div className="more" style={{ marginTop: 0 }}>
        <select aria-label="College" value={f.college_id} onChange={(e) => setF({ ...f, college_id: e.target.value })}>
          <option value="">College…</option>{colleges.map((c) => <option key={c.id} value={c.id}>{c.short_name}</option>)}</select>
        Amount ₹ <input aria-label="Amount" inputMode="numeric" value={f.amount_inr} onChange={(e) => setF({ ...f, amount_inr: e.target.value.replace(/\D/g, "") })} />
        Paid on <input aria-label="Paid on" type="date" value={f.paid_on} onChange={(e) => setF({ ...f, paid_on: e.target.value })} />
        Last date of admission <input aria-label="Last date of admission" type="date" value={f.closure_date} onChange={(e) => setF({ ...f, closure_date: e.target.value })} />
        <button className="capsule" style={{ padding: "6px 14px", border: "1px solid var(--hairline)" }} onClick={add}>Track deposit</button>
      </div>
      {err && <p role="alert" className="note" style={{ color: "var(--amber)" }}>{err}</p>}
      {rows.length === 0 ? <div className="empty">No deposits tracked yet.</div> : rows.map((d) => (
        <div key={d.id} className="card" style={{ boxShadow: "none", marginTop: 10, borderColor: d.alert ? "#fcd34d" : undefined, background: d.alert ? "#fffbeb" : undefined }}>
          <div className="row"><strong style={{ color: "var(--ink)" }}>{name(d.college_id)} · {inr(d.amount_inr)}</strong>
            <span>
              <button className="link" onClick={() => { setLetterFor(d); setLetter(null); }}>Refund letter</button>{" · "}
              <button className="link" aria-label={`Remove ${name(d.college_id)} deposit`} onClick={() => deleteDeposit(d.id).then(reload)}>Remove</button>
            </span></div>
          <div className="row"><span className="label">If you withdraw today</span>
            <span className="num value">{d.refund_if_withdrawn_today.refund_percent}% · min {inr(d.refund_if_withdrawn_today.minimum_net_refund_inr)}</span></div>
          {d.next_cutoff
            ? <div className="row"><span className="label">Next drop</span><span className={`num value ${d.alert ? "" : "emerald"}`} style={d.alert ? { color: "var(--amber)" } : undefined}>
                {d.next_cutoff.days_left} d left (until {d.next_cutoff.last_day}, then below {d.next_cutoff.refund_percent}%)</span></div>
            : <div className="row"><span className="label">Next drop</span><span className="num value">refund window closed</span></div>}
        </div>
      ))}
      {letterFor && (
        <div className="card" style={{ boxShadow: "none", marginTop: 12 }}>
          <div className="label">Refund request letter — {name(letterFor.college_id)}</div>
          <div className="more">Student name <input aria-label="Student name" value={L.student} onChange={(e) => setL({ ...L, student: e.target.value })} />
            Parent/guardian <input aria-label="Guardian name" value={L.guardian} onChange={(e) => setL({ ...L, guardian: e.target.value })} />
            Notice date <input aria-label="Notice date" type="date" value={L.notice} onChange={(e) => setL({ ...L, notice: e.target.value })} />
            <button className="link" onClick={makeLetter}>Generate</button></div>
          {letter && <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, background: "#f8fafc", padding: 12, borderRadius: 12 }}>{letter}</pre>}
        </div>
      )}
    </section>
  );
}
