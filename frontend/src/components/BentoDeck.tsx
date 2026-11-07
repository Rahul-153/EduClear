import type { Card } from "../api";
import type { Strings } from "../i18n";
import { lakhs, lpa } from "../lib/format";
import SourceBadge from "./SourceBadge";

interface Props { s: Strings; deck: Record<string, Card | null>; truth: boolean; onRoi: (id: string) => void; message?: string }

export default function BentoDeck({ s, deck, truth, onRoi, message }: Props) {
  const slots: [string, string][] = [["safe_anchor", s.safe], ["sweet_spot", s.target], ["dream_reach", s.reach]];
  return (
    <section aria-label={s.deck}>
      <h2 style={{ fontSize: 13, textTransform: "uppercase", marginBottom: 12 }}>{s.deck}</h2>
      {message && <div className="card empty">{message}</div>}
      <div className="grid3">
        {slots.map(([key, title]) => {
          const c = deck[key];
          return c ? (
            <article key={key} className="card hover">
              <div className="row"><span className="label">{title}</span><span className="mono note">NIRF #{c.nirf_rank}</span></div>
              <h3 style={{ fontSize: 17 }}>{c.short_name}</h3>
              <div className="note">{c.city_state}</div>
              <div className="clock"><span>⏱ {s.debtFree}</span><span className="num value">{c.payback.payback_months} mo</span></div>
              <div className="row"><span className="label">{s.costLabel}</span><span className="num value">{lakhs(c.four_year_cost_inr)}</span></div>
              <div className="row">
                <span className="label">{truth ? s.medianBase : s.brochureCtc}</span>
                <span className={`num value ${truth ? "emerald" : "struck"}`}>{truth ? lpa(c.median_base_lpa) : lpa(c.headline_ctc_lpa)}</span>
              </div>
              <div className="row">
                <span className="label">{s.placement}</span>
                <span className={`num value ${truth ? "" : "struck"}`}>{truth ? `${c.placed.toLocaleString("en-IN")} / ${c.eligible.toLocaleString("en-IN")}` : `${c.placement_rate}%`}</span>
              </div>
              <div className="row" style={{ marginTop: 8 }}>
                <SourceBadge id={c.id} label={s.sources} />
                <button className="link" onClick={() => onRoi(c.id)}>{s.viewRoi}</button>
              </div>
            </article>
          ) : (
            <article key={key} className="card"><div className="label">{title}</div><div className="empty">{s.noMatch}</div></article>
          );
        })}
      </div>
    </section>
  );
}
