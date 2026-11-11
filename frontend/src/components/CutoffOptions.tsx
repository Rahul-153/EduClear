import { useState } from "react";
import type { CutoffOption, Profile } from "../api";
import type { Strings } from "../i18n";
import DataBadge from "./DataBadge";
import { lpa } from "../lib/format";

const SHOWN = 25;

interface Props { s: Strings; data: { items: CutoffOption[]; iits_need_rank: boolean }; profile: Profile }

/** Institutes with an official closing rank but no audited cost or placement yet (D-49). Nothing here is estimated. */
export default function CutoffOptions({ s, data, profile }: Props) {
  const [all, setAll] = useState(false);
  const needCategory = profile.seat_type !== "OPEN" && !profile.category_rank;
  const rows = all ? data.items : data.items.slice(0, SHOWN);
  return (
    <section className="card" aria-label={s.cutoffTitle}>
      <h2 style={{ fontSize: 13, textTransform: "uppercase", marginBottom: 8 }}>{s.cutoffTitle} · <span className="num">{data.items.length}</span></h2>
      <p className="note">{s.cutoffNote}</p>
      {data.iits_need_rank && profile.seat_type === "OPEN" && <p className="note">{s.cutoffNeedRank}</p>}
      {needCategory && <p className="note" role="status">{s.cutoffNeedCategory}</p>}
      {data.items.length === 0 ? <div className="empty">{s.cutoffNone}</div> : (
        <div style={{ overflowX: "auto" }}>
          <table className="cutoffs">
            <thead><tr><th>{s.institute}</th><th>{s.fitLabel}</th><th>{s.programme}</th><th>{s.quotaLabel}</th><th>{s.closing}</th><th>{s.costLabel}</th><th>{s.placement}</th><th>{s.dataLabel}</th></tr></thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.institute}>
                  <td><a href={x.source_url} target="_blank" rel="noreferrer" title={x.source}>{x.institute}</a> <span className="note">{x.kind}</span></td>
                  <td><span className={`tier ${x.tier}`}>{x.tier}</span></td>
                  <td>{x.program.replace(/\s*\(4 Years.*$/, "")}</td>
                  <td>{x.quota}</td>
                  <td className="num">{x.closing_rank.toLocaleString("en-IN")}</td>
                  <td className="note">{s.notVerified}</td>
                  {x.placement ? (
                    <td>
                      <a href={x.placement.source_url} target="_blank" rel="noreferrer" className="num" title={`NIRF 2025, batch ${x.placement.batch}`}>
                        {x.placement.placed.toLocaleString("en-IN")} / {x.placement.eligible.toLocaleString("en-IN")}</a>
                      <div className="note">{lpa(x.placement.median_base_lpa)} · {x.placement.placement_rate}%</div>
                    </td>
                  ) : <td className="note">{s.notVerified}</td>}
                  <td><DataBadge s={s} level={x.data_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!all && data.items.length > SHOWN && <button className="link" onClick={() => setAll(true)}>{s.showAll} ({data.items.length})</button>}
    </section>
  );
}
