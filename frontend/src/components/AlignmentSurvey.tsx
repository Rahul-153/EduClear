import { useEffect, useState } from "react";
import { alignment } from "../api";
import type { Strings } from "../i18n";

const DIMS: [string, string][] = [["brand_prestige", "Brand prestige"], ["branch_passion", "Branch passion"], ["location_safety", "Location & safety"], ["budget_strictness", "Budget strictness"]];
const init = () => Object.fromEntries(DIMS.map(([k]) => [k, 3])) as Record<string, number>;
type Result = Awaited<ReturnType<typeof alignment>>;

export default function AlignmentSurvey({ s }: { s: Strings }) {
  const [st, setSt] = useState(init());
  const [pa, setPa] = useState(init());
  const [res, setRes] = useState<Result | null>(null);
  useEffect(() => { alignment(st, pa).then(setRes).catch(() => setRes(null)); }, [st, pa]);
  return (
    <section className="card" aria-label={s.alignment}>
      <h2 style={{ fontSize: 13, textTransform: "uppercase", marginBottom: 12 }}>{s.alignment}</h2>
      <div className="split">
        {([[s.student, st, setSt], [s.parent, pa, setPa]] as const).map(([who, val, set]) => (
          <div key={who}>
            <div className="label">{who} — rate 1 (low) to 5 (high)</div>
            {DIMS.map(([k, label]) => (
              <div className="slider" key={k}><label htmlFor={`${who}-${k}`}>{label}</label><span className="num">{val[k]}</span>
                <input id={`${who}-${k}`} type="range" min={1} max={5} value={val[k]} onChange={(e) => set({ ...val, [k]: Number(e.target.value) })} /></div>
            ))}
          </div>
        ))}
      </div>
      {res && (
        <div>
          <div className="clock"><span>{s.score}</span><span className="num value">{res.alignment_score}% — {res.verdict}</span></div>
          {res.discussion_guide.length === 0 ? <p className="note">No large gaps. Compare options together using the matrix above.</p> :
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
              {res.discussion_guide.map((g) => <li key={g.dimension}><strong>{g.dimension}</strong> (gap {g.gap}, {g.higher_priority} rates higher): {g.prompt}</li>)}
            </ul>}
        </div>
      )}
    </section>
  );
}
