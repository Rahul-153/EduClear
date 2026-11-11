import type { Lang, Strings } from "../i18n";
import { pagesFor, type Page, type View } from "../lib/nav";

interface Props { s: Strings; lang: Lang; setLang: (l: Lang) => void; page: Page; view: View; setView: (v: View) => void }

export default function Header({ s, lang, setLang, page, view, setView }: Props) {
  const label: Record<Page, string> = { find: s.navFind, cost: s.navCost, apply: s.navApply, help: s.navHelp };
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
        <div className="capsule" role="group" aria-label={s.viewLabel}>
          <button aria-pressed={view === "student"} onClick={() => setView("student")}>{s.viewStudent}</button>
          <button aria-pressed={view === "parent"} onClick={() => setView("parent")}>{s.viewParent}</button>
        </div>
        <div className="capsule" role="group" aria-label="Language">
          <button aria-pressed={lang === "en"} onClick={() => setLang("en")}>English</button>
          <button aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>हिंदी</button>
        </div>
      </div>
      <nav className="pages" aria-label="Pages">
        {pagesFor(view).map((p) => <a key={p} href={`#${p}`} aria-current={p === page ? "page" : undefined}>{label[p]}</a>)}
      </nav>
    </header>
  );
}
