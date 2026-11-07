// DEV-ONLY harness (not part of the production build): measures AG Grid sort/filter time on synthetic rows for NFR-01.
// The synthetic rows exist only here and are never shown to users or mixed with the verified dataset.
import "./agGridSetup";
import { createRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, GridApi } from "ag-grid-community";

const N = 2000;
const rows = Array.from({ length: N }, (_, i) => ({ id: i, name: `Row ${i}`, cost: 800000 + ((i * 7919) % 3000000), median: 8 + ((i * 31) % 150) / 10, rate: 60 + ((i * 17) % 400) / 10 }));
const cols: ColDef[] = [{ field: "name", filter: true }, { field: "cost", filter: "agNumberColumnFilter" }, { field: "median", filter: "agNumberColumnFilter" }, { field: "rate", filter: "agNumberColumnFilter" }];

function Perf() {
  const api = useRef<GridApi>(null);
  const [out, setOut] = useState("running…");
  useEffect(() => {
    const t = setTimeout(async () => {
      const g = api.current!;
      const time = async (fn: () => void) => { const s = performance.now(); fn(); await new Promise((r) => setTimeout(r, 0)); return +(performance.now() - s).toFixed(1); };
      const res: number[][] = [[], []];
      for (let k = 0; k < 5; k++) {
        res[0].push(await time(() => g.applyColumnState({ state: [{ colId: "cost", sort: k % 2 ? "asc" : "desc" }], defaultState: { sort: null } })));
        res[1].push(await time(() => { g.setFilterModel({ rate: { filterType: "number", type: "greaterThan", filter: 60 + k * 5 } }); }));
      }
      const med = (a: number[]) => a.slice().sort((x, y) => x - y)[Math.floor(a.length / 2)];
      setOut(JSON.stringify({ rows: N, sortMsRuns: res[0], sortMsMedian: med(res[0]), filterMsRuns: res[1], filterMsMedian: med(res[1]) }));
    }, 800);
    return () => clearTimeout(t);
  }, []);
  return <div><pre id="result">{out}</pre><div style={{ height: 300 }}><AgGridReact rowData={rows} columnDefs={cols} onGridReady={(e) => { (api as { current: GridApi }).current = e.api; }} /></div></div>;
}
createRoot(document.getElementById("root")!).render(<Perf />);
