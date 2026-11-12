import { useState } from "react";
import { sources, type Sources } from "../api";

export default function SourceBadge({ id, label }: { id: string; label: string }) {
  const [data, setData] = useState<Sources | null>(null);
  const [open, setOpen] = useState(false);
  const toggle = async () => {
    if (!data) setData(await sources(id));
    setOpen(!open);
  };
  return (
    <span style={{ position: "relative" }}>
      <button className="link" onClick={toggle} aria-expanded={open}>{label} ↗</button>
      {open && data && (
        <div className="pop" role="dialog" aria-label="Source evidence">
          <div className="label">{data.verification}</div>
          {Object.keys(data.provenance).length === 0 && <p className="note">No source documents are on file for this record. The figures come from a dataset supplied to the project and have not been checked against official filings.</p>}
          {Object.entries(data.provenance).map(([k, v]) => (
            <div key={k} style={{ margin: "6px 0" }}>
              <strong>{k}</strong>: <a href={v.url} target="_blank" rel="noreferrer">source</a>
              <div className="note">{v.locator}</div>
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
