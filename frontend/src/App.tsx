import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { recommend, type Assumptions, type Profile, type Recommendation } from "./api";
import { t, type Lang } from "./i18n";
import Header from "./components/Header";
import SmartSentence from "./components/SmartSentence";
import BentoDeck from "./components/BentoDeck";
const TruthMatrix = lazy(() => import("./components/TruthMatrix")); // AG Grid / AG Charts load after first paint
const RoiPanel = lazy(() => import("./components/RoiPanel"));
import AlignmentSurvey from "./components/AlignmentSurvey";
import Boundary from "./components/Boundary";
import AdmissionsTimeline from "./components/AdmissionsTimeline";
import DepositTracker from "./components/DepositTracker";
import ChoiceSimulator from "./components/ChoiceSimulator";
import Sessions from "./components/Sessions";
import Copilot from "./components/Copilot";
import TechKit from "./components/TechKit";

const INITIAL: Profile = { stream: "Computer Science", percentile: 99.75, budget_lakhs: 18, region: "All", home_state: "", jee_advanced_rank: "", bitsat_score: "" };

export default function App() {
  const [lang, setLang] = useState<Lang>("en");
  const [truth, setTruth] = useState(true);
  const [p, setP] = useState<Profile>(INITIAL);
  const [a, setA] = useState<Assumptions>({ savings_rate: 0.4, salary_growth: 0.1 });
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const s = t(lang);

  useEffect(() => {
    let live = true;
    recommend(p, a).then((r) => { if (live) { setRec(r); setError(null); } }).catch((e) => live && setError(String(e)));
    return () => { live = false; };
  }, [p, a]);

  const rows = rec?.matches ?? [];
  const card = useMemo(() => rows.find((c) => c.id === selected) ?? rec?.deck.safe_anchor ?? rows[0], [rows, selected, rec]);

  return (
    <div className="wrap">
      <Header s={s} lang={lang} setLang={setLang} truth={truth} setTruth={setTruth} />
      <SmartSentence s={s} p={p} setP={setP} />
      {error && <div className="card" role="alert">Could not reach the API ({error}). Start the backend on port 8000.</div>}
      {rec && <BentoDeck s={s} deck={rec.deck} truth={truth} onRoi={setSelected} message={rec.supported ? undefined : rec.message} />}
      {rec?.needs_more_input.length ? <p className="note">{rec.needs_more_input.length} colleges need an extra input (JEE Advanced rank or BITSAT score) to be rated — open “More inputs”.</p> : null}
      <Boundary name="Placement Truth matrix"><Suspense fallback={<section className="card"><div className="empty">Loading matrix…</div></section>}><TruthMatrix s={s} rows={rows} truth={truth} onSelect={setSelected} /></Suspense></Boundary>
      <Boundary name="ROI panel"><Suspense fallback={<section className="card"><div className="empty">Loading ROI…</div></section>}><RoiPanel s={s} card={card} a={a} setA={setA} /></Suspense></Boundary>
      <Boundary name="Admissions timeline"><AdmissionsTimeline /></Boundary>
      <Boundary name="Counselling sessions"><Sessions /></Boundary>
      <Boundary name="Tech kit"><TechKit /></Boundary>
      <Boundary name="Choice-filling simulator"><ChoiceSimulator colleges={rows} profile={p} /></Boundary>
      <Boundary name="Deposit tracker"><DepositTracker colleges={rows} /></Boundary>
      <Boundary name="Alignment survey"><AlignmentSurvey s={s} /></Boundary>
      <Copilot profile={p} lang={lang} />
    </div>
  );
}
