import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { recommend, type Assumptions, type Profile, type Recommendation } from "./api";
import { t, type Lang } from "./i18n";
import Header from "./components/Header";
import { loadView, pageFromHash, saveView, type Page, type View } from "./lib/nav";
import SmartSentence from "./components/SmartSentence";
import BentoDeck from "./components/BentoDeck";
const TruthMatrix = lazy(() => import("./components/TruthMatrix")); // AG Grid / AG Charts load after first paint
const RoiPanel = lazy(() => import("./components/RoiPanel"));
import AlignmentSurvey from "./components/AlignmentSurvey";
import Boundary from "./components/Boundary";
import CutoffOptions from "./components/CutoffOptions";
import AdmissionsTimeline from "./components/AdmissionsTimeline";
import DepositTracker from "./components/DepositTracker";
import ChoiceSimulator from "./components/ChoiceSimulator";
import Sessions from "./components/Sessions";
import Copilot from "./components/Copilot";
import TechKit from "./components/TechKit";

const INITIAL: Profile = { stream: "Computer Science", percentile: 99.75, budget_lakhs: 18, region: "All", home_state: "", jee_advanced_rank: "", bitsat_score: "", seat_type: "OPEN", gender: "Any", category_rank: "" };

export default function App() {
  const [lang, setLang] = useState<Lang>("en");
  const [truth, setTruth] = useState(true);
  const [p, setP] = useState<Profile>(INITIAL);
  const [a, setA] = useState<Assumptions>({ savings_rate: 0.4, salary_growth: 0.1 });
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [page, setPage] = useState<Page>(pageFromHash());
  const [view, setViewState] = useState<View>(loadView());
  const s = t(lang);
  const setView = (v: View) => { setViewState(v); saveView(v); };
  const openRoi = (id: string) => { setSelected(id); location.hash = "cost"; };

  useEffect(() => {
    const onHash = () => { setPage(pageFromHash()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    let live = true;
    recommend(p, a).then((r) => { if (live) { setRec(r); setError(null); } }).catch((e) => live && setError(String(e)));
    return () => { live = false; };
  }, [p, a]);

  const rows = rec?.matches ?? [];
  const card = useMemo(() => rows.find((c) => c.id === selected) ?? rec?.deck.safe_anchor ?? rows[0], [rows, selected, rec]);

  return (
    <div className="wrap">
      <Header s={s} lang={lang} setLang={setLang} page={page} view={view} setView={setView} />
      {error && <div className="card" role="alert">Could not reach the API ({error}). Start the backend on port 8000.</div>}
      {page === "find" && (
        <>
          <SmartSentence s={s} p={p} setP={setP} />
          {rec && <BentoDeck s={s} deck={rec.deck} truth={truth} onRoi={openRoi} message={rec.message} view={view} />}
          {rec?.needs_more_input.length ? <p className="note">{rec.needs_more_input.length} colleges need an extra input (JEE Advanced rank or BITSAT score) to be rated — open “More inputs”.</p> : null}
          {rows.length > 0 && <Boundary name="Placement Truth matrix"><Suspense fallback={<section className="card"><div className="empty">Loading matrix…</div></section>}><TruthMatrix s={s} rows={rows} truth={truth} setTruth={setTruth} onSelect={openRoi} /></Suspense></Boundary>}
          {rec?.cutoff_only && <CutoffOptions s={s} data={rec.cutoff_only} profile={p} />}
        </>
      )}
      {page === "cost" && (
        <>
          <Boundary name="ROI panel"><Suspense fallback={<section className="card"><div className="empty">Loading ROI…</div></section>}><RoiPanel s={s} card={card} a={a} setA={setA} /></Suspense></Boundary>
          <Boundary name="Tech kit"><TechKit s={s} /></Boundary>
          <Boundary name="Deposit tracker"><DepositTracker s={s} colleges={rows} /></Boundary>
        </>
      )}
      {page === "apply" && (
        <>
          <Boundary name="Choice-filling simulator"><ChoiceSimulator s={s} colleges={rows} profile={p} /></Boundary>
          <Boundary name="Admissions timeline"><AdmissionsTimeline s={s} /></Boundary>
        </>
      )}
      {page === "help" && (
        <>
          <Boundary name="Alignment survey"><AlignmentSurvey s={s} view={view} /></Boundary>
          <Boundary name="Counselling sessions"><Sessions s={s} view={view} /></Boundary>
        </>
      )}
      <Copilot profile={p} lang={lang} view={view} />
    </div>
  );
}
