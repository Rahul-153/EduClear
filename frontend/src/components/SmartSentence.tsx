import { useState } from "react";
import { intake, type IntakeResult, type Profile } from "../api";
import type { Strings } from "../i18n";

const PCTS = [99.9, 99.75, 99.5, 99.0, 98.0, 96.0, 94.2];
const BUDGETS = [12, 15, 18, 25, 35];
const REGIONS = ["All", "North", "South", "East", "West"];

const withCurrent = (list: number[], v: number) => (list.includes(v) ? list : [...list, v].sort((a, b) => b - a));
interface Props { s: Strings; p: Profile; setP: (p: Profile) => void }

export default function SmartSentence({ s, p, setP }: Props) {
  const [more, setMore] = useState(false);
  const [text, setText] = useState("");
  const [heard, setHeard] = useState<IntakeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const understand = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const r = await intake(text); setHeard(r);
      const f = r.profile;
      setP({ ...p, percentile: f.percentile ?? p.percentile, budget_lakhs: f.budget_lakhs ?? p.budget_lakhs, region: f.region ?? p.region,
        home_state: f.home_state ?? p.home_state, jee_advanced_rank: f.jee_advanced_rank ? String(f.jee_advanced_rank) : p.jee_advanced_rank,
        bitsat_score: f.bitsat_score ? String(f.bitsat_score) : p.bitsat_score });
    } finally { setBusy(false); }
  };
  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => setP({ ...p, [k]: v });
  const regionLabel: Record<string, string> = { All: s.all, North: s.north, South: s.south, East: s.east, West: s.west };
  return (
    <section className="card" aria-label="Smart Sentence">
      <div className="sentence">
        {s.iAmLooking}
        <select aria-label="Stream" value={p.stream} onChange={(e) => set("stream", e.target.value)}>
          <option>Computer Science</option><option disabled>Electronics & ECE (data pending)</option><option disabled>MBA (data pending)</option>
        </select>
        {s.forStudent}
        <select aria-label="JEE Main percentile" value={p.percentile} onChange={(e) => set("percentile", Number(e.target.value))}>
          {withCurrent(PCTS, p.percentile).map((v) => <option key={v} value={v}>{v} percentile (JEE Main)</option>)}
        </select>
        {s.budgetOf}
        <select aria-label="Budget" value={p.budget_lakhs} onChange={(e) => set("budget_lakhs", Number(e.target.value))}>
          {withCurrent(BUDGETS, p.budget_lakhs).map((v) => <option key={v} value={v}>Under ₹{v} Lakhs</option>)}
        </select>
        {s.inRegion}
        <select aria-label="Region" value={p.region} onChange={(e) => set("region", e.target.value)}>
          {REGIONS.map((v) => <option key={v} value={v}>{regionLabel[v]}</option>)}
        </select>
      </div>
      <form className="more" onSubmit={(e) => { e.preventDefault(); understand(); }} style={{ marginBottom: 6 }}>
        <input aria-label="Describe your situation" style={{ width: "min(560px, 100%)" }} maxLength={600} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Or just tell us: “99.3 percentile, 20 lakh budget, South” / “१८ लाख बजट, दक्षिण भारत”" />
        <button className="link" disabled={busy}>{busy ? "Reading…" : "Fill from text"}</button>
      </form>
      {heard && (
        <p className="note" role="status">Understood{heard.llm_used ? " (rules + local model)" : " (rules)"}: {Object.entries(heard.profile).filter(([, v]) => v !== null).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(", ") || "nothing"}
          {heard.missing.length ? ` · not found: ${heard.missing.join(", ").replace(/_/g, " ")}` : ""}{heard.unsupported_stream ? " · only Computer Science data is available yet" : ""}</p>)}
      <button className="link" onClick={() => setMore(!more)} aria-expanded={more}>{more ? "Hide" : "More inputs"} (JEE Advanced rank, BITSAT, home state, category)</button>
      {more && (
        <div className="more">
          JEE Advanced rank <input aria-label="JEE Advanced rank" inputMode="numeric" value={p.jee_advanced_rank} onChange={(e) => set("jee_advanced_rank", e.target.value.replace(/\D/g, ""))} />
          BITSAT score <input aria-label="BITSAT score" inputMode="numeric" value={p.bitsat_score} onChange={(e) => set("bitsat_score", e.target.value.replace(/\D/g, ""))} />
          Home state <input aria-label="Home state" value={p.home_state} onChange={(e) => set("home_state", e.target.value)} />
          Seat type <select aria-label="Seat type" value={p.seat_type} onChange={(e) => set("seat_type", e.target.value)}>
            {["OPEN", "EWS", "OBC-NCL", "SC", "ST"].map((v) => <option key={v}>{v}</option>)}</select>
          Gender <select aria-label="Gender" value={p.gender} onChange={(e) => set("gender", e.target.value)}>
            <option value="Any">Any</option><option value="Female">Female</option></select>
          Category rank <input aria-label="Category rank" inputMode="numeric" value={p.category_rank} onChange={(e) => set("category_rank", e.target.value.replace(/\D/g, ""))} />
        </div>
      )}
    </section>
  );
}
