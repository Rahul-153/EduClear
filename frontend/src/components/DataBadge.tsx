import type { DataLevel } from "../api";
import type { Strings } from "../i18n";

export const levelLabel = (s: Strings, level: DataLevel) =>
  ({ audited: s.levelAudited, partly_verified: s.levelPartly, cutoffs_only: s.levelCutoffs })[level];

/** How much of a college's data is verified (D-49): every card and row carries one of three labels. */
export default function DataBadge({ s, level }: { s: Strings; level: DataLevel }) {
  return <span className={`badge ${level === "audited" ? "green" : ""}`}>{levelLabel(s, level)}</span>;
}
