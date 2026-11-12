import { useEffect, useState } from "react";
import { alignment } from "../api";
import type { Lang } from "../i18n";
import type { Strings } from "../i18n";
import type { View } from "../lib/nav";

const DIMS: [string, string][] = [["brand_prestige", "Brand prestige"], ["branch_passion", "Branch passion"], ["location_safety", "Location & safety"], ["budget_strictness", "Budget strictness"]];
const init = () => Object.fromEntries(DIMS.map(([k]) => [k, 3])) as Record<string, number>;
type Result = Awaited<ReturnType<typeof alignment>>;
type Answers = Record<string, number>;

// Each side's saved answers stay in this browser only; the score needs both.
const load = (view: View): Answers | null => {
  try { const v = localStorage.getItem(`educlear.align.${view}`); return v ? (JSON.parse(v) as Answers) : null; } catch { return null; }
};
const store = (view: View, a: Answers) => { try { localStorage.setItem(`educlear.align.${view}`, JSON.stringify(a)); } catch { /* storage blocked: answers last for this visit only */ } };

export default function AlignmentSurvey({ s, lang, view, collegeIds }: { s: Strings; lang: Lang; view: View; collegeIds: string[] }) {
  const [saved, setSaved] = useState<Record<View, Answers | null>>({ student: load("student"), parent: load("parent") });
  const [draft, setDraft] = useState<Answers>(saved[view] ?? init());
  const [res, setRes] = useState<Result | null>(null);
  useEffect(() => { setDraft(saved[view] ?? init()); }, [view]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (saved.student && saved.parent) alignment(saved.student, saved.parent, collegeIds).then(setRes).catch(() => setRes(null));
    else setRes(null);
  }, [saved, collegeIds.join(",")]);
  const save = () => { store(view, draft); setSaved({ ...saved, [view]: draft }); };
  const who = view === "student" ? s.student : s.parent;
  const other = view === "student" ? saved.parent : saved.student;
  return (
    <section className="card" aria-label={s.alignment}>
      <h2 style={{ fontSize: 13, textTransform: "uppercase", marginBottom: 12 }}>{s.alignment}</h2>
      <div className="label">{who} — rate 1 (low) to 5 (high)</div>
      {DIMS.map(([k, label]) => (
        <div className="slider" key={k}><label htmlFor={`${view}-${k}`}>{label}</label><span className="num">{draft[k]}</span>
          <input id={`${view}-${k}`} type="range" min={1} max={5} value={draft[k]} onChange={(e) => setDraft({ ...draft, [k]: Number(e.target.value) })} /></div>
      ))}
      <div className="row" style={{ justifyContent: "flex-start", gap: 12 }}>
        <button className="capsule" style={{ padding: "8px 14px", background: "var(--ink)", color: "#fff", border: 0 }} onClick={save}>{s.saveAnswers}</button>
        {saved[view] && <span className="note">{s.saved}</span>}
      </div>
      {!other && <p className="note">{s.switchView}</p>}
      {res && (
        <div>
          <div className="clock"><span>{s.score}</span><span className="num value">{res.alignment_score}% — {res.verdict}</span></div>
          {res.discussion_guide.length === 0 ? <p className="note">No large gaps. Compare options together using the matrix above.</p> :
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
              {res.discussion_guide.map((g) => <li key={g.dimension}><strong>{g.dimension}</strong> (gap {g.gap}, {g.higher_priority} rates higher): {g.prompt}</li>)}
            </ul>}
          {res.brief.length > 0 && (
            <div>
              <div className="label" style={{ marginTop: 10 }}>{lang === "hi" ? "परिवार की बातचीत के लिए बिंदु" : "Points for your family talk"}</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>{res.brief.map((b) => <li key={b.dimension}>{b[lang]}</li>)}</ul>
              <p className="note">{lang === "hi" ? "साथ बैठकर बात करने में मदद चाहिए? नीचे ‘Family consensus’ सेशन देखें।" : "Want help talking it through? See the Family consensus session below."}</p>
            </div>)}
        </div>
      )}
    </section>
  );
}
