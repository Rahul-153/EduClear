import { useEffect, useState } from "react";
import { deleteRound, roundAdvise, roundCycles, roundSeason, roundSeats, saveRound, type Profile, type RoundAdvice, type RoundCycles, type RoundSeason, type RoundSeat } from "../api";
import type { Lang } from "../i18n";
import type { View } from "../lib/nav";
import { inr } from "../lib/format";

const FEMALE = "Female-only (including Supernumerary)";
const CSE = "Computer Science and Engineering (4 Years, Bachelor of Technology)";
// Example shown on first load so the screen is not empty; the family replaces it with their own list.
const EXAMPLE: RoundSeat[] = [
  { institute: "National Institute of Technology Calicut", program: CSE, quota: "OS" },
  { institute: "National Institute of Technology Patna", program: CSE, quota: "OS" },
];

const TXT = {
  en: {
    title: "Round-by-round coach", replay: "Replay JoSAA", own: "My own round",
    intro: "After each round: the seat you hold, which option keeps your higher choices open, how those seats moved in past years, and the money at risk. History and official rules only, not a forecast.",
    example: "An example is loaded. Change the rank and the list to your own.",
    mainRank: "JEE Main rank (for this seat type)", advRank: "JEE Advanced rank (for IITs)", seatType: "Seat type", female: "Female-only seats",
    round: "Round", list: "Your choices, best first", add: "Add a seat", addPh: "Type an institute or branch", up: "Move up", down: "Move down", remove: "Remove",
    allotted: "Allotted", noSeat: "No seat allotted", pick: "Mark the choice you were allotted, or No seat allotted.", closingPh: "Closing rank this round",
    holdReplay: "By the published closing ranks you hold", holdOwn: "You hold", replayNote: "Read from that year's published closing ranks, assuming you chose float in every round.",
    a_no_seat: "No seat at this rank yet", a_no_seat_d: "Nothing is held. A fee paid in advance is refunded in full if no seat is allotted (JoSAA fee rule).",
    a_freeze_only: "This is your first choice: freeze is the only option", a_freeze_only_d: "There is nothing higher on your list to wait for.",
    a_last_round: "Last round: float and slide are not offered", a_last_round_d: "The seat you hold is the result of this process.",
    a_float: "Float keeps every higher choice on your list open", a_slide: "Slide keeps your higher choices open (all are in the same institute)",
    caveat1: "If a higher choice opens, it replaces this seat automatically. Take off the list anything you would not really accept.",
    caveat2: "Freeze cannot be changed later. Float can be changed to slide or freeze in a later round.",
    ruleText: "Official rule text", page: "p.",
    higher: "Higher choices: how the closing rank moved after this round", choice: "Choice", closing: "Closing rank this round", shortBy: "You are short by",
    reached: "Moved enough", absolute: "Past closing rank reached your rank", of: "of", years: "years", noData: "no row", needMain: "Enter a JEE Main rank", needAdv: "Enter a JEE Advanced rank",
    absNote: "Add this round's closing rank for a closer reading: without it, past ranks are compared with your rank directly, which the test below shows is much weaker.",
    testNote: "How far to trust this: tested on JoSAA 2025 using 2020-2024. When the closing rank had moved enough in every past year, the seat was reached in 84-92% of cases; when in no past year, in 7-14%. A count of years is not a probability.",
    fee: "Seat acceptance fee", back: "Back if you withdraw", charge: "charge", wd: "Withdrawal this round", open: "open", closed: "not open", rounds: "rounds",
    feeNote: "Paid once, in the round a seat is first allotted. Institute fees and their refund dates are in the deposit tracker on the Cost page.",
    source: "Source",
    saved: "Saved rounds", save: "Save this round", took: "Option taken", none: "Not decided", freeze: "Freeze", float: "Float", slide: "Slide", withdrew: "Withdrew",
    feePaid: "Seat fee paid", feeParent: "Only a parent can record a payment.", load: "Open", noSeatShort: "No seat", deposits: "Institute deposits in your tracker",
    savedNote: "Saved for your family: parent and student see the same record.",
  },
  hi: {
    title: "राउंड-दर-राउंड सहायक", replay: "JoSAA दोबारा चलाएँ", own: "मेरा अपना राउंड",
    intro: "हर राउंड के बाद: आपके पास कौन-सी सीट है, कौन-सा विकल्प ऊपर की पसंद खुली रखता है, पिछले वर्षों में वे सीटें कितनी खिसकीं, और कितना पैसा दाँव पर है। केवल पिछला रिकॉर्ड और आधिकारिक नियम, कोई पूर्वानुमान नहीं।",
    example: "एक उदाहरण भरा हुआ है। रैंक और सूची अपनी डालें।",
    mainRank: "JEE Main रैंक (इस सीट श्रेणी की)", advRank: "JEE Advanced रैंक (IIT के लिए)", seatType: "सीट श्रेणी", female: "केवल महिला सीटें",
    round: "राउंड", list: "आपकी पसंद, सबसे अच्छी पहले", add: "सीट जोड़ें", addPh: "संस्थान या शाखा लिखें", up: "ऊपर करें", down: "नीचे करें", remove: "हटाएँ",
    allotted: "आवंटित", noSeat: "कोई सीट नहीं मिली", pick: "जो पसंद आवंटित हुई उसे चुनें, या 'कोई सीट नहीं मिली'।", closingPh: "इस राउंड की क्लोज़िंग रैंक",
    holdReplay: "प्रकाशित क्लोज़िंग रैंक के अनुसार आपके पास है", holdOwn: "आपके पास है", replayNote: "उस वर्ष की प्रकाशित क्लोज़िंग रैंक से, यह मानकर कि आपने हर राउंड में फ़्लोट चुना।",
    a_no_seat: "इस रैंक पर अभी कोई सीट नहीं", a_no_seat_d: "कोई सीट नहीं है। पहले से जमा शुल्क, सीट न मिलने पर पूरा लौटता है (JoSAA शुल्क नियम)।",
    a_freeze_only: "यह आपकी पहली पसंद है: केवल फ़्रीज़ का विकल्प है", a_freeze_only_d: "आपकी सूची में इससे ऊपर कुछ नहीं है।",
    a_last_round: "अंतिम राउंड: फ़्लोट और स्लाइड नहीं मिलते", a_last_round_d: "जो सीट आपके पास है वही इस प्रक्रिया का परिणाम है।",
    a_float: "फ़्लोट आपकी सूची की हर ऊपर की पसंद खुली रखता है", a_slide: "स्लाइड आपकी ऊपर की पसंद खुली रखता है (सब एक ही संस्थान में हैं)",
    caveat1: "ऊपर की पसंद खुलते ही वह इस सीट की जगह अपने-आप ले लेती है। जो सीट आप सच में नहीं लेंगे, उसे सूची से हटा दें।",
    caveat2: "फ़्रीज़ बाद में बदला नहीं जा सकता। फ़्लोट को अगले राउंड में स्लाइड या फ़्रीज़ में बदला जा सकता है।",
    ruleText: "आधिकारिक नियम", page: "पृ.",
    higher: "ऊपर की पसंद: इस राउंड के बाद क्लोज़िंग रैंक कितनी खिसकी", choice: "पसंद", closing: "इस राउंड की क्लोज़िंग रैंक", shortBy: "आप इतने पीछे हैं",
    reached: "पर्याप्त खिसकी", absolute: "पिछली क्लोज़िंग रैंक आपकी रैंक तक पहुँची", of: "/", years: "वर्ष", noData: "रिकॉर्ड नहीं", needMain: "JEE Main रैंक डालें", needAdv: "JEE Advanced रैंक डालें",
    absNote: "बेहतर तुलना के लिए इस राउंड की क्लोज़िंग रैंक डालें: उसके बिना पिछली रैंकों की तुलना सीधे आपकी रैंक से होती है, जो नीचे की जाँच के अनुसार काफ़ी कमज़ोर है।",
    testNote: "इस पर कितना भरोसा करें: JoSAA 2025 पर 2020-2024 के रिकॉर्ड से जाँचा गया। जब हर पिछले वर्ष क्लोज़िंग रैंक पर्याप्त खिसकी थी, 84-92% मामलों में सीट मिली; जब किसी वर्ष नहीं, 7-14% में। वर्षों की गिनती संभावना नहीं है।",
    fee: "सीट स्वीकृति शुल्क", back: "सीट छोड़ने पर वापसी", charge: "कटौती", wd: "इस राउंड में सीट छोड़ना", open: "खुला", closed: "बंद", rounds: "राउंड",
    feeNote: "एक ही बार, जिस राउंड में पहली बार सीट मिले। संस्थान की फ़ीस और रिफ़ंड की तारीखें Cost पेज के जमा-राशि ट्रैकर में हैं।",
    source: "स्रोत",
    saved: "सहेजे गए राउंड", save: "यह राउंड सहेजें", took: "चुना गया विकल्प", none: "तय नहीं", freeze: "फ़्रीज़", float: "फ़्लोट", slide: "स्लाइड", withdrew: "सीट छोड़ी",
    feePaid: "सीट शुल्क जमा हुआ", feeParent: "भुगतान केवल अभिभावक दर्ज कर सकते हैं।", load: "खोलें", noSeatShort: "सीट नहीं", deposits: "आपके ट्रैकर में संस्थान की जमा-राशि",
    savedNote: "आपके परिवार के लिए सहेजा गया: अभिभावक और छात्र एक ही रिकॉर्ड देखते हैं।",
  },
};

const short = (c: RoundSeat) => `${c.institute.replace("National Institute of Technology", "NIT").replace("Indian Institute of Technology", "IIT").replace("Indian Institute of Information Technology", "IIIT")} · ${c.program.replace(/\s*\(4 Years.*$/, "")} (${c.quota})`;
const label = (c: RoundSeat) => `${c.institute} | ${c.program.replace(/\s*\(4 Years.*$/, "")} | ${c.quota}`;
const num = (n: number | null | undefined) => (n == null ? "—" : n.toLocaleString("en-IN"));
const field = { font: "inherit", fontSize: 13, padding: "6px 10px", borderRadius: 10, border: "1px solid var(--hairline)", background: "#fff" } as const;

export default function RoundCoach({ lang, profile, view, feeLocked }: { lang: Lang; profile: Profile; view: View; feeLocked: boolean }) {
  const x = TXT[lang];
  const [cycles, setCycles] = useState<RoundCycles | null>(null);
  const [own, setOwn] = useState(false);
  const [round, setRound] = useState(1);
  const [mainRank, setMainRank] = useState(profile.category_rank || "5000");
  const [advRank, setAdvRank] = useState(profile.jee_advanced_rank || "");
  const [seatType, setSeatType] = useState(profile.seat_type || "OPEN");
  const [female, setFemale] = useState(profile.gender === "Female");
  const [choices, setChoices] = useState<RoundSeat[]>(EXAMPLE);
  const [allotted, setAllotted] = useState<number | null>(null); // own round: position, or -1 for no seat
  const [seats, setSeats] = useState<RoundSeat[]>([]);
  const [draft, setDraft] = useState("");
  const [res, setRes] = useState<RoundAdvice | null>(null);
  const [err, setErr] = useState("");
  const [season, setSeason] = useState<RoundSeason | null>(null);
  const [took, setTook] = useState("");
  const [feePaid, setFeePaid] = useState(false);

  useEffect(() => { roundCycles().then(setCycles).catch((e) => setErr((e as Error).message)); }, []);
  const replayYear = cycles?.replay_years[0];
  const year = own ? cycles?.own_round.year : replayYear;
  const total = own ? cycles?.own_round.total_rounds ?? 5 : (replayYear ? cycles!.rounds[String(replayYear)] : 6);
  const gender = female ? FEMALE : "Gender-Neutral";
  const ownYear = cycles?.own_round.year;
  useEffect(() => { if (ownYear) roundSeason(ownYear).then((r) => { setSeason(r); setFeePaid(r.seat_fee_paid); }).catch(() => setSeason(null)); }, [ownYear]);

  useEffect(() => { if (replayYear) roundSeats(replayYear, seatType, gender).then((r) => setSeats(r.items)).catch(() => setSeats([])); }, [replayYear, seatType, gender]);
  useEffect(() => { if (round > total) setRound(total); }, [total]);

  const body = JSON.stringify({
    year, round: Math.min(round, total), seat_type: seatType, gender, choices,
    main_rank: Number(mainRank) || null, advanced_rank: Number(advRank) || null,
    ...(own ? (allotted === -1 ? { no_seat: true } : { allotted }) : {}),
  });
  useEffect(() => {
    if (!year || !choices.length || (own && allotted === null)) { setRes(null); return; }
    let live = true;
    roundAdvise(JSON.parse(body)).then((r) => { if (live) { setRes(r); setErr(""); } }).catch((e) => { if (live) { setRes(null); setErr((e as Error).message); } });
    return () => { live = false; };
  }, [body]);

  const move = (i: number, to: number) => {
    if (to < 0 || to >= choices.length) return;
    const next = [...choices]; const [c] = next.splice(i, 1); next.splice(to, 0, c); setChoices(next); setAllotted(null);
  };
  const addDraft = (v: string) => {
    setDraft(v);
    const hit = seats.find((s) => label(s) === v);
    if (hit && !choices.some((c) => label(c) === v)) { setChoices([...choices, { institute: hit.institute, program: hit.program, quota: hit.quota }]); setDraft(""); }
  };
  const setClosing = (i: number, v: string) => setChoices(choices.map((c, j) => (j === i ? { ...c, closing_this_round: Number(v) || null } : c)));

  const save = () => saveRound({ ...JSON.parse(body), action_taken: took || null, ...(feeLocked ? {} : { fee_paid: feePaid }) })
    .then((r) => { setSeason(r); setErr(""); }).catch((e) => setErr((e as Error).message));
  const open = (r: RoundSeason["rounds"][number]) => {
    const q = r.request;
    setChoices(q.choices); setRound(r.round); setAllotted(q.no_seat ? -1 : q.allotted); setMainRank(q.main_rank ? String(q.main_rank) : "");
    setAdvRank(q.advanced_rank ? String(q.advanced_rank) : ""); setSeatType(q.seat_type); setFemale(q.gender === FEMALE); setTook(r.action_taken ?? ""); setFeePaid(r.fee_paid);
  };
  const actions = ["freeze", "float", "slide", "withdrew"] as const;
  const held = res && res.held !== null ? res.choices[res.held] : null;
  const act = res?.option.action;
  const higher = res?.choices.filter((c) => c.above_held) ?? [];
  const m = res?.money;
  const money = m && m.status === "seat_held" && (
    <div className="clock" style={{ flexWrap: "wrap", gap: 12, background: "#f8fafc", color: "var(--ink)" }}>
      <span>{x.fee} <strong className="num">{inr(m.seat_acceptance_fee_inr)}</strong></span>
      <>
        <span>{x.back} <strong className="num">{inr(m.refund_on_withdrawal_inr!)}</strong> <span className="note">({inr(m.withdrawal_charge_inr!)} {x.charge})</span></span>
        <span>{x.wd}: <strong>{m.withdrawal_open_this_round ? x.open : x.closed}</strong> <span className="note">({x.rounds} {m.withdrawal_first_round}-{m.withdrawal_last_round})</span></span>
      </>
    </div>
  );
  const option = res && act && (
    <div style={{ padding: 12, borderRadius: 12, border: "1px solid var(--hairline)", background: "#fff", margin: "12px 0" }}>
      <strong style={{ color: "var(--ink)", fontSize: 15 }}>{x[`a_${act}` as const]}</strong>
      {act === "float" || act === "slide"
        ? <ul className="note" style={{ margin: "6px 0 0", paddingLeft: 18 }}><li>{x.caveat1}</li><li>{x.caveat2}</li></ul>
        : <p className="note" style={{ margin: "6px 0 0" }}>{x[`a_${act}_d` as const]}</p>}
      {res.rules.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary className="note" style={{ cursor: "pointer" }}>{x.ruleText} · <a href={res.rules_source.url} target="_blank" rel="noreferrer">{res.rules_source.document}</a></summary>
          {res.rules.map((r) => <p className="note" key={r.id} style={{ margin: "6px 0" }}>“{r.quote}” <span className="mono">{r.clause}, {x.page} {r.page}</span></p>)}
        </details>
      )}
    </div>
  );

  return (
    <section className="card" aria-labelledby="round-h">
      <div className="row"><h2 id="round-h" style={{ fontSize: 13, textTransform: "uppercase" }}>{x.title}</h2>
        <div className="capsule" role="group" aria-label={x.title}>
          <button aria-pressed={!own} onClick={() => { setOwn(false); }}>{x.replay} {replayYear ?? ""}</button>
          <button aria-pressed={own} onClick={() => { setOwn(true); }}>{x.own}</button>
        </div></div>
      <p className="note">{x.intro} {choices === EXAMPLE && x.example}</p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "end", margin: "10px 0" }}>
        <label className="note">{x.mainRank}<br /><input style={{ ...field, width: 130 }} inputMode="numeric" value={mainRank} onChange={(e) => setMainRank(e.target.value.replace(/\D/g, ""))} /></label>
        <label className="note">{x.advRank}<br /><input style={{ ...field, width: 130 }} inputMode="numeric" value={advRank} onChange={(e) => setAdvRank(e.target.value.replace(/\D/g, ""))} /></label>
        <label className="note">{x.seatType}<br /><select style={field} value={seatType} onChange={(e) => setSeatType(e.target.value)}>{["OPEN", "EWS", "OBC-NCL", "SC", "ST"].map((s) => <option key={s}>{s}</option>)}</select></label>
        <label className="note" style={{ display: "flex", gap: 6, alignItems: "center", paddingBottom: 8 }}><input type="checkbox" checked={female} onChange={(e) => setFemale(e.target.checked)} />{x.female}</label>
        <div className="note">{x.round}<br />
          <div className="capsule" role="group" aria-label={x.round}>
            {Array.from({ length: total }, (_, i) => i + 1).map((r) => <button key={r} aria-pressed={r === round} onClick={() => setRound(r)}>{r}</button>)}
          </div></div>
      </div>

      <div className="split">
        <div>
          <div className="label" style={{ marginBottom: 6 }}>{x.list}</div>
          <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {choices.map((c, i) => (
              <li key={label(c)} style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8, padding: "8px 10px", border: `1px solid ${res?.held === i ? "var(--emerald)" : "var(--hairline)"}`, borderRadius: 12, marginBottom: 6, background: "#fff" }}>
                <span className="mono note" style={{ width: 18 }}>{i + 1}</span>
                <span style={{ flex: 1, minWidth: 160, color: "var(--ink)", fontWeight: 600, fontSize: 13 }}>{short(c)}</span>
                {own && <label className="note"><input type="radio" name="allotted" checked={allotted === i} onChange={() => setAllotted(i)} /> {x.allotted}</label>}
                {own && (allotted === -1 || (allotted !== null && i < allotted)) &&
                  <input style={{ ...field, width: 150 }} inputMode="numeric" aria-label={`${x.closingPh}: ${short(c)}`} placeholder={x.closingPh} value={c.closing_this_round ?? ""} onChange={(e) => setClosing(i, e.target.value.replace(/\D/g, ""))} />}
                <button className="link" aria-label={`${x.up}: ${short(c)}`} onClick={() => move(i, i - 1)}>▲</button>
                <button className="link" aria-label={`${x.down}: ${short(c)}`} onClick={() => move(i, i + 1)}>▼</button>
                <button className="link" aria-label={`${x.remove}: ${short(c)}`} onClick={() => { setChoices(choices.filter((_, j) => j !== i)); setAllotted(null); }}>✕</button>
              </li>
            ))}
          </ol>
          {own && <label className="note" style={{ display: "block", margin: "4px 0 8px" }}><input type="radio" name="allotted" checked={allotted === -1} onChange={() => setAllotted(-1)} /> {x.noSeat}</label>}
          <input style={{ ...field, width: "100%" }} list="round-seats" aria-label={x.add} placeholder={`${x.add}: ${x.addPh}`} value={draft} onChange={(e) => addDraft(e.target.value)} />
          <datalist id="round-seats">{seats.map((s) => <option key={label(s)} value={label(s)} />)}</datalist>
        </div>

        <div aria-live="polite">
          {err && <p className="note" role="alert">{err}</p>}
          {own && allotted === null && <div className="empty">{x.pick}</div>}
          {own && season && season.rounds.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div className="label" style={{ marginBottom: 4 }}>{x.saved}</div>
              {season.rounds.map((r) => (
                <div className="row" key={r.round}>
                  <span><span className="mono">{x.round} {r.round}</span> · {r.held ? short(r.held) : x.noSeatShort}{r.action_taken ? ` · ${x[r.action_taken as (typeof actions)[number]]}` : ""}{r.fee_paid ? ` · ${x.feePaid}` : ""}</span>
                  <span style={{ display: "flex", gap: 10 }}><button className="link" onClick={() => open(r)}>{x.load}</button>
                    <button className="link" aria-label={`${x.remove}: ${x.round} ${r.round}`} onClick={() => deleteRound(season.year, r.round).then(setSeason).catch((e) => setErr((e as Error).message))}>✕</button></span>
                </div>
              ))}
              <p className="note">{x.savedNote}</p>
            </div>
          )}
          {res && (
            <>
              {held && <div className="clock"><span>{res.mode === "replay" ? x.holdReplay : x.holdOwn}: <strong>{short(held)}</strong></span><span>{x.round} {res.round}/{res.total_rounds}</span></div>}
              {res.mode === "replay" && <p className="note">{x.replayNote}</p>}
              {view === "parent" ? <>{money}{option}</> : <>{option}{money}</>}
              {m?.status === "seat_held" && <p className="note">{x.feeNote}</p>}
              {season && season.institute_deposits.count > 0 && <p className="note">{x.deposits}: <strong className="num">{inr(season.institute_deposits.total_inr)}</strong></p>}
              {own && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginTop: 8 }}>
                  <label className="note">{x.took} <select style={field} value={took} onChange={(e) => setTook(e.target.value)}>
                    <option value="">{x.none}</option>{actions.map((k) => <option key={k} value={k}>{x[k]}</option>)}</select></label>
                  <label className="note" title={feeLocked ? x.feeParent : undefined} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <input type="checkbox" checked={feePaid} disabled={feeLocked} onChange={(e) => setFeePaid(e.target.checked)} />{x.feePaid}</label>
                  <button className="capsule" style={{ padding: "6px 14px" }} onClick={save}>{x.save}</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {res && higher.length > 0 && act !== "freeze_only" && (
        <>
          <div className="label" style={{ margin: "16px 0 6px" }}>{x.higher}</div>
          <div style={{ overflowX: "auto" }}>
            <table className="cutoffs">
              <thead><tr><th>{x.choice}</th><th>{x.closing}</th><th>{x.shortBy}</th>{res.history_years.map((y) => <th key={y} className="num">{y}</th>)}<th>{x.reached}</th></tr></thead>
              <tbody>
                {higher.map((c) => (
                  <tr key={c.position}>
                    <td>{short(c)}</td>
                    <td className="num">{num(c.closing_this_round)}</td>
                    {!c.history ? <td colSpan={res.history_years.length + 2} className="note">{c.inst_type === "IIT" ? x.needAdv : x.needMain}</td> : (
                      <>
                        <td className="num">{c.history.short_by_pct == null ? "—" : `${c.history.short_by_pct}%`}</td>
                        {c.history.years.map((y) => (
                          <td key={y.year} className="num" title={y.available ? `${num(y.closing_at_round)} → ${num(y.highest_closing_from_round)}` : x.noData}
                              style={{ color: y.available ? (y.reached ? "var(--emerald)" : "var(--body)") : "var(--meta)" }}>
                            {y.available ? `+${y.moved_pct}%${y.reached ? " ✓" : ""}` : "—"}
                          </td>
                        ))}
                        <td><strong className="num">{c.history.years_reached} {x.of} {c.history.years_with_data}</strong> <span className="note">{x.years}{c.history.basis === "absolute_rank" ? ` · ${x.absolute}` : ""}</span></td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {higher.some((c) => c.history?.basis === "absolute_rank") && <p className="note">{x.absNote}</p>}
          <p className="note">{x.testNote} {x.source}: <a href={res.source_url} target="_blank" rel="noreferrer">{res.source}</a></p>
        </>
      )}
    </section>
  );
}
