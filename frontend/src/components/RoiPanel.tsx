import "../agChartsSetup";
import { useEffect, useState } from "react";
import { AgCharts } from "ag-charts-react";
import { roi, type Assumptions, type Card, type Roi } from "../api";
import type { Strings } from "../i18n";
import { inr } from "../lib/format";

interface Props { s: Strings; card: Card | undefined; a: Assumptions; setA: (a: Assumptions) => void }

export default function RoiPanel({ s, card, a, setA }: Props) {
  const [data, setData] = useState<Roi | null>(null);
  useEffect(() => {
    if (!card) return;
    let live = true;
    roi(card.id, a).then((r) => live && setData(r)).catch(() => live && setData(null));
    return () => { live = false; };
  }, [card?.id, a.savings_rate, a.salary_growth]);

  if (!card) return <section className="card"><div className="empty">Select a college to see its ROI.</div></section>;
  const p = data?.payback;
  return (
    <section className="card" aria-label={s.roi}>
      <div className="row"><h2 style={{ fontSize: 13, textTransform: "uppercase" }}>{s.roi} — {card.short_name}</h2></div>
      <div className="split">
        <div>
          {p && (
            <>
              <div className="clock"><span>⏱ {s.debtFree}</span><span className="num value">{p.payback_months} months</span></div>
              <div className="row"><span className="label">Gross-pay payback (marketing view)</span><span className="num value struck">{p.payback_months_gross_pay} mo</span></div>
              <div className="row"><span className="label">In-hand pay / month</span><span className="num value">{inr(p.in_hand_monthly_inr)}</span></div>
              <div className="row"><span className="label">Available to repay / month</span><span className="num value">{inr(p.disposable_monthly_inr)}</span></div>
            </>
          )}
          <div className="slider"><label htmlFor="sr">Share of in-hand pay used to repay</label><span className="num">{Math.round(a.savings_rate * 100)}%</span>
            <input id="sr" type="range" min={10} max={80} value={Math.round(a.savings_rate * 100)} onChange={(e) => setA({ ...a, savings_rate: Number(e.target.value) / 100 })} /></div>
          <div className="slider"><label htmlFor="sg">Yearly salary growth (illustrative)</label><span className="num">{Math.round(a.salary_growth * 100)}%</span>
            <input id="sg" type="range" min={0} max={20} value={Math.round(a.salary_growth * 100)} onChange={(e) => setA({ ...a, salary_growth: Number(e.target.value) / 100 })} /></div>
          <p className="note">Model assumptions, not audited data. Year 0 is the audited NIRF median; later years apply your growth setting. Tax: new regime FY2025-26.</p>
        </div>
        <div style={{ minHeight: 260 }}>
          {data && (
            <AgCharts options={{
              data: data.trajectory.points, height: 260,
              title: { text: "Illustrative salary trajectory (LPA)", fontSize: 12 },
              series: [{ type: "area", xKey: "year", yKey: "salary_lpa", yName: "Salary (LPA)", fill: "#059669", fillOpacity: 0.18, stroke: "#059669" }],
              axes: { x: { type: "number", position: "bottom", title: { text: "Years after graduation" } }, y: { type: "number", position: "left" } },
              legend: { enabled: false },
            }} />
          )}
        </div>
      </div>
    </section>
  );
}
