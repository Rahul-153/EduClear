import { useEffect, useState } from "react";
import { getMe } from "../api";
import { createFamily, joinFamily, makeInvite, removeMember, type Me } from "../api";
import type { Strings } from "../i18n";

/** Family linking (PLAN_AUTH.md 6.4): invite codes are shown once; a parent can remove a student; anyone can leave. */
export default function FamilyPanel({ s, me, setMe }: { s: Strings; me: Me; setMe: (m: Me) => void }) {
  const [code, setCode] = useState<string | null>(null);
  const [join, setJoin] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const u = me.user!;
  useEffect(() => { getMe().then(setMe).catch(() => undefined); }, []); // fresh on open: the other side may have joined
  const run = async (fn: () => Promise<Me | { code: string }>) => {
    setErr(null);
    try { const r = await fn(); if ("code" in r) setCode(r.code); else { setMe(r); setCode(null); } } catch (e) { setErr((e as Error).message); }
  };
  const members = me.family?.members ?? [];
  const other = u.role === "parent" ? "student" : "parent";
  const canInvite = !u.is_minor && !members.some((m) => m.role === other);
  return (
    <section className="card" aria-label={s.familyTitle}>
      <h2 style={{ fontSize: 13, textTransform: "uppercase", marginBottom: 8 }}>{s.familyTitle}</h2>
      <p className="note">{s.familyNote}</p>
      {u.role === "student" && <p className="note">{s.roleReadOnly}</p>}
      {members.map((m) => (
        <div className="row" key={m.id} style={{ borderTop: "1px solid var(--hairline)", paddingTop: 8 }}>
          <span><strong style={{ color: "var(--ink)" }}>{m.name}</strong> <span className="badge">{m.role === "parent" ? s.viewParent : s.viewStudent}</span>
            {m.you && <span className="note"> · {s.you}</span>}</span>
          {(m.you || (u.role === "parent" && m.role === "student")) && (
            <button className="link" onClick={() => run(() => removeMember(m.id))}>{m.you ? s.leave : s.remove}</button>)}
        </div>
      ))}
      {!me.family && (
        <>
          {u.is_minor ? <p className="note" role="status">{s.waitingMinor}</p>
            : <button className="capsule" style={{ padding: "6px 14px", border: "1px solid var(--hairline)" }} onClick={() => run(createFamily)}>{s.createFamily}</button>}
        </>
      )}
      {me.family && canInvite && (
        <div style={{ marginTop: 12 }}>
          <button className="capsule" style={{ padding: "6px 14px", border: "1px solid var(--hairline)" }} onClick={() => run(makeInvite)}>{s.createInvite}</button>
          {code && <p className="note" role="status">{s.inviteShown} <strong className="num" style={{ fontSize: 16, letterSpacing: "0.1em" }}>{code}</strong></p>}
        </div>
      )}
      {(!me.family || members.length === 1) && (
        <form className="more" onSubmit={(e) => { e.preventDefault(); run(() => joinFamily(join)); }}>
          <label>{s.joinTitle} <input aria-label={s.joinTitle} maxLength={8} value={join} onChange={(e) => setJoin(e.target.value.toUpperCase())} style={{ width: 120, textTransform: "uppercase" }} /></label>
          <button className="capsule" disabled={join.length !== 8} style={{ padding: "6px 14px", border: "1px solid var(--hairline)" }}>{s.join}</button>
        </form>
      )}
      {err && <p role="alert" className="note" style={{ color: "var(--amber)" }}>{err}</p>}
    </section>
  );
}
