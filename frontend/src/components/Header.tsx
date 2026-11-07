import type { Lang, Strings } from "../i18n";

interface Props { s: Strings; lang: Lang; setLang: (l: Lang) => void; truth: boolean; setTruth: (v: boolean) => void }

export default function Header({ s, lang, setLang, truth, setTruth }: Props) {
  return (
    <header className="top">
      <div className="brand">
        <div className="logo">E</div>
        <div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <h1 style={{ fontSize: 16 }}>EduClear</h1><span className="badge">{s.independent}</span>
          </div>
          <div className="note">{s.tagline}</div>
        </div>
      </div>
      <div className="tools">
        <div className="capsule" role="group" aria-label="Language">
          <button aria-pressed={lang === "en"} onClick={() => setLang("en")}>English</button>
          <button aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>हिंदी</button>
        </div>
        <div className="capsule" role="group" aria-label="Truth Lens">
          <button aria-pressed={!truth} onClick={() => setTruth(false)}>{s.brochure}</button>
          <button aria-pressed={truth} onClick={() => setTruth(true)}><span className="dot" />{s.truth}</button>
        </div>
      </div>
    </header>
  );
}
