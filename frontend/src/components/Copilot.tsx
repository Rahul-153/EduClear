import { useEffect, useRef, useState } from "react";
import { agentChat, agentConfirm, payConfig, type AgentReply, type BookingView, type PayConfig, type Profile } from "../api";
import type { Lang } from "../i18n";
import CheckoutPanel from "./CheckoutPanel";

interface Msg { who: "you" | "bot"; text: string; meta?: AgentReply }
const SUGGESTED = ["Can I afford NIT Calicut with 8 lakh savings?", "Is MNIT Jaipur worth it?", "Suggest colleges for me", "NIT Calicut के बारे में बताओ"];

export default function Copilot({ profile, lang }: { profile: Profile; lang: Lang }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([{ who: "bot", text: "I answer from the verified college data and exact calculators. I can suggest colleges, check affordability and EMI, estimate payback and book a sandbox counselling session — only after you confirm." }]);
  const [busy, setBusy] = useState(false);
  const [cfg, setCfg] = useState<PayConfig | null>(null);
  const [booking, setBooking] = useState<BookingView | null>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { payConfig().then(setCfg); }, []);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [msgs, booking, open]);

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    setMsgs((m) => [...m, { who: "you", text }]); setInput(""); setBusy(true);
    try { const r = await agentChat(text, profile, lang); setMsgs((m) => [...m, { who: "bot", text: r.reply, meta: r }]); }
    catch (e) { setMsgs((m) => [...m, { who: "bot", text: `Sorry, that failed (${(e as Error).message}).` }]); }
    finally { setBusy(false); }
  };
  const confirm = async (id: string) => {
    setBusy(true);
    try { const r = await agentConfirm(id); setBooking(r.booking); setMsgs((m) => [...m, { who: "bot", text: r.note }]); }
    catch (e) { setMsgs((m) => [...m, { who: "bot", text: (e as Error).message }]); }
    finally { setBusy(false); }
  };

  return (
    <>
      <button onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="copilot"
        style={{ position: "fixed", right: 20, bottom: 20, zIndex: 20, background: "var(--ink)", color: "#fff", border: 0, borderRadius: 999, padding: "10px 16px", fontSize: 13, fontWeight: 500, display: "flex", gap: 8, alignItems: "center", boxShadow: "var(--shadow)" }}>
        <span className="dot" style={{ background: "#34d399" }} />Ask Copilot</button>
      {open && (
        <aside id="copilot" aria-label="EduClear Copilot" style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "min(400px, 100vw)", background: "#fff", borderLeft: "1px solid var(--hairline)", zIndex: 30, display: "flex", flexDirection: "column", boxShadow: "-12px 0 32px -12px rgba(0,0,0,0.12)" }}>
          <div className="row" style={{ padding: 16, borderBottom: "1px solid var(--hairline)" }}>
            <div><div className="label">EduClear Copilot</div><strong style={{ color: "var(--ink)" }}>Financial & admissions advisor</strong></div>
            <button className="link" onClick={() => setOpen(false)} aria-label="Close Copilot">✕</button>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "grid", gap: 10, alignContent: "start" }} aria-live="polite">
            {msgs.map((m, i) => (
              <div key={i} style={{ justifySelf: m.who === "you" ? "end" : "start", maxWidth: "90%", whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.5, padding: "8px 12px", borderRadius: 12,
                background: m.who === "you" ? "var(--ink)" : "#f1f5f9", color: m.who === "you" ? "#fff" : "var(--ink)" }}>
                {m.text}
                {m.meta?.pending_action && !booking && (
                  <div style={{ marginTop: 8 }}><button disabled={busy} onClick={() => confirm(m.meta!.pending_action!.id)} className="capsule"
                    style={{ padding: "6px 12px", background: "#FFC439", border: 0, fontWeight: 600 }}>Confirm and create sandbox order</button></div>)}
                {m.meta && <div className="note" style={{ marginTop: 4 }}>{m.meta.tool}{m.meta.llm ? ` · routed by ${m.meta.tool_chosen_by}` : ""}</div>}
              </div>
            ))}
            {booking && cfg && <CheckoutPanel booking={booking} cfg={cfg} onChange={(b) => { if (!b || b.status !== "pending") { setBooking(null); setMsgs((m) => [...m, { who: "bot", text: b ? "Payment captured in the sandbox. Funds are held in the escrow ledger." : "Booking cancelled." }]); } }} />}
            {msgs.length < 3 && SUGGESTED.map((s) => <button key={s} className="link" style={{ textAlign: "left", padding: 8, border: "1px solid var(--hairline)", borderRadius: 12, textDecoration: "none", fontSize: 12 }} onClick={() => send(s)}>{s}</button>)}
            <div ref={end} />
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(input); }} style={{ padding: 12, borderTop: "1px solid var(--hairline)", display: "flex", gap: 8 }}>
            <input aria-label="Message" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask in English or हिंदी…" maxLength={500}
              style={{ flex: 1, font: "inherit", fontSize: 13, padding: "8px 12px", borderRadius: 12, border: "1px solid var(--hairline)" }} />
            <button disabled={busy} className="capsule" style={{ padding: "8px 14px", background: "var(--ink)", color: "#fff", border: 0 }}>{busy ? "…" : "Send"}</button>
          </form>
        </aside>
      )}
    </>
  );
}
