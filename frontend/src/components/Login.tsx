import { useState } from "react";
import { authStart, authVerify, type Me, type Role } from "../api";
import type { Strings } from "../i18n";

/** Email one-time code sign-in (PLAN_AUTH.md 6.3). No password field exists. */
export default function Login({ s, onSignedIn }: { s: Strings; onSignedIn: (m: Me) => void }) {
  const [role, setRole] = useState<Role>("parent");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [over18, setOver18] = useState(false);
  const [sent, setSent] = useState(false);
  const [demo, setDemo] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    setErr(null); setBusy(true);
    try { const r = await authStart({ email, role, over18, display_name: name }); setDemo(r.demo_code ?? null); setSent(true); }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  const verify = async () => {
    setErr(null); setBusy(true);
    try { const m = await authVerify(email, code); onSignedIn(m); location.hash = "find"; }
    catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <section className="card" aria-label={s.loginTitle} style={{ maxWidth: 520 }}>
      <h2 style={{ fontSize: 13, textTransform: "uppercase", marginBottom: 8 }}>{s.loginTitle}</h2>
      <p className="note">{s.noPassword}</p>
      {!sent ? (
        <form className="more" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <div className="capsule" role="group" aria-label={s.iAmA}>
            <button type="button" aria-pressed={role === "parent"} onClick={() => setRole("parent")}>{s.viewParent}</button>
            <button type="button" aria-pressed={role === "student"} onClick={() => setRole("student")}>{s.viewStudent}</button>
          </div>
          <div><label>{s.email} <input type="email" autoComplete="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: "min(320px, 100%)" }} /></label></div>
          <div><label>{s.name} <input maxLength={60} value={name} onChange={(e) => setName(e.target.value)} /></label></div>
          {role === "student" && <div><label><input type="checkbox" checked={over18} onChange={(e) => setOver18(e.target.checked)} /> {s.over18}</label></div>}
          <button className="capsule" disabled={busy} style={{ padding: "8px 16px", background: "var(--ink)", color: "#fff", border: 0 }}>{s.sendCode}</button>
        </form>
      ) : (
        <form className="more" onSubmit={(e) => { e.preventDefault(); verify(); }}>
          <p className="note" role="status">{s.codeSent}</p>
          {demo && <p className="note" role="status">{s.demoCode} <strong className="num">{demo}</strong></p>}
          <div><label>{s.codeLabel} <input inputMode="numeric" autoComplete="one-time-code" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} /></label></div>
          <button className="capsule" disabled={busy || code.length !== 6} style={{ padding: "8px 16px", background: "var(--ink)", color: "#fff", border: 0 }}>{s.verify}</button>
        </form>
      )}
      {err && <p role="alert" className="note" style={{ color: "var(--amber)" }}>{err}</p>}
    </section>
  );
}
