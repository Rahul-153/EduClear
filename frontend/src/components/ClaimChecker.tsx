import { useState } from "react";
import { checkClaim, type ClaimResult } from "../api";
import type { Lang } from "../i18n";

const TXT = {
  en: { title: "Check a brochure claim", hint: "Paste a placement line from a brochure or advert, with the college name.", btn: "Check", ph: "e.g. IIT Delhi: 100% placement, highest package 45 LPA",
        record: "Record", above: "Higher than the record", ok: "Consistent with the record", src: "Source" },
  hi: { title: "ब्रोशर का दावा जाँचें", hint: "ब्रोशर या विज्ञापन की प्लेसमेंट वाली लाइन कॉलेज के नाम के साथ चिपकाएँ।", btn: "जाँचें", ph: "जैसे IIT Delhi: 100% प्लेसमेंट, सबसे ऊँचा पैकेज 45 LPA",
        record: "रिकॉर्ड", above: "रिकॉर्ड से ज़्यादा", ok: "रिकॉर्ड से मेल खाता है", src: "स्रोत" },
};

export default function ClaimChecker({ lang }: { lang: Lang }) {
  const x = TXT[lang];
  const [text, setText] = useState("");
  const [res, setRes] = useState<ClaimResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const run = async () => {
    if (!text.trim()) return;
    setBusy(true); setErr("");
    try { setRes(await checkClaim(text, lang)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <section className="card" aria-labelledby="claim-h">
      <h2 id="claim-h" className="label">{x.title}</h2>
      <p className="note">{x.hint}</p>
      <div className="row" style={{ gap: 8 }}>
        <input aria-label={x.title} value={text} maxLength={1500} placeholder={x.ph} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") run(); }} style={{ flex: 1, font: "inherit", padding: "8px 12px", borderRadius: 12, border: "1px solid var(--hairline)" }} />
        <button className="capsule" disabled={busy} onClick={run}>{busy ? "…" : x.btn}</button>
      </div>
      {err && <p role="alert" className="note">{err}</p>}
      {res && (
        <div aria-live="polite" style={{ marginTop: 10 }}>
          {res.lines.map((l, i) => <p key={i} style={{ margin: "4px 0" }}>{l}</p>)}
          {res.verdicts?.map((v) => <p key={v.claim} className="note">{v.claim}: {v.status === "above_record" ? x.above : x.ok}</p>)}
          {res.label && <p className="note">{res.label}{res.source_url && <> · <a href={res.source_url} target="_blank" rel="noreferrer">{x.src}</a></>}</p>}
        </div>
      )}
    </section>
  );
}
