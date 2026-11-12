import "../agGridSetup";
import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { themeQuartz, type ColDef, type ICellRendererParams } from "ag-grid-community";
import type { Card } from "../api";
import type { Strings } from "../i18n";
import { inr } from "../lib/format";
import { levelLabel } from "./DataBadge";

const theme = themeQuartz.withParams({
  accentColor: "#0f172a", fontFamily: "Plus Jakarta Sans, sans-serif", borderColor: "rgba(0,0,0,0.07)",
  headerBackgroundColor: "#fafafa", backgroundColor: "#ffffff", foregroundColor: "#475569", headerTextColor: "#0f172a", fontSize: 13,
});

const Denominator = (p: ICellRendererParams<Card>) =>
  p.data ? <span className="num">{p.data.placed.toLocaleString("en-IN")} / {p.data.eligible.toLocaleString("en-IN")} <span className="note">({p.data.placement_rate}%)</span></span> : null;

interface Props { s: Strings; rows: Card[]; truth: boolean; setTruth: (v: boolean) => void; onSelect: (id: string) => void }

export default function TruthMatrix({ s, rows, truth, setTruth, onSelect }: Props) {
  const cols = useMemo<ColDef<Card>[]>(() => [
    { headerName: "NIRF", field: "nirf_rank", width: 90, type: "numericColumn", cellClass: "num" },
    { headerName: "College", field: "short_name", minWidth: 150, flex: 1, pinned: "left" },
    { headerName: s.dataLabel, width: 150, valueGetter: (p) => (p.data ? levelLabel(s, p.data.data_level) : "") },
    { headerName: "Fit", valueGetter: (p) => p.data?.fit.tier ?? "needs input", width: 120,
      cellRenderer: (p: ICellRendererParams<Card>) => <span className={`tier ${p.value}`}>{p.value}</span> },
    { headerName: s.costLabel, field: "four_year_cost_inr", width: 150, type: "numericColumn", valueFormatter: (p) => inr(p.value), cellClass: "num" },
    truth
      ? { headerName: s.medianBase + " (LPA)", field: "median_base_lpa", width: 150, type: "numericColumn", cellClass: "num emerald" }
      : { headerName: s.brochureCtc + " (LPA)", field: "headline_ctc_lpa", width: 150, type: "numericColumn", cellClass: "num struck" },
    { headerName: "Placed / Eligible", width: 190, cellRenderer: Denominator, hide: !truth, sortable: true,
      comparator: (_a, _b, na, nb) => (na.data?.placement_rate ?? 0) - (nb.data?.placement_rate ?? 0) },
    { headerName: "Disclosed %", field: "placement_rate", width: 130, type: "numericColumn", hide: truth, cellClass: "num struck" },
    { headerName: s.payback + " (mo)", valueGetter: (p) => p.data?.payback.payback_months, width: 130, type: "numericColumn", cellClass: "num" },
    { headerName: "Accreditation", field: "accreditation", width: 190, tooltipField: "accreditation" },
    { headerName: "Commission", width: 150, valueGetter: (p) => (p.data?.commercial_relationship.startsWith("None") ? "0% commission" : "Check"),
      cellRenderer: (p: ICellRendererParams<Card>) => <span className="badge green" title={p.data?.commercial_relationship}>{p.value}</span> },
    { headerName: "Link (as supplied)", width: 150, sortable: false, cellRenderer: (p: ICellRendererParams<Card>) =>
      p.data ? <a href={p.data.source_url} target="_blank" rel="noreferrer" title="Link given in the supplied dataset; not checked against the figures">Link ↗</a> : null },
  ], [s, truth]);

  return (
    <section className="card" aria-label={s.matrix}>
      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ fontSize: 13, textTransform: "uppercase" }}>{s.matrix}</h2>
        <div className="capsule" role="group" aria-label={s.matrix}>
          <button aria-pressed={!truth} onClick={() => setTruth(false)}>{s.brochure}</button>
          <button aria-pressed={truth} onClick={() => setTruth(true)}><span className="dot" />{s.truth}</button>
        </div>
      </div>
      <div className="note" style={{ marginBottom: 8 }}>Click a row for cost and payback • sort and filter any column</div>
      <div className="grid-wrap">
        <AgGridReact<Card> theme={theme} rowData={rows} columnDefs={cols} defaultColDef={{ sortable: true, filter: true, resizable: true }}
          getRowId={(p) => p.data.id} onRowClicked={(e) => e.data && onSelect(e.data.id)} animateRows />
      </div>
    </section>
  );
}
