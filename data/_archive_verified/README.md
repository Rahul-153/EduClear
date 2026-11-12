# Archived: the previously collected, source-verified data

Moved here on 2026-11-12 when the project switched to the dataset supplied in `rehackathonfileseom.zip` (see `DATA_ZIP_REVIEW.md`
and decision D-57). Nothing was deleted; the app no longer loads these files.

- `colleges/`: 11 audited records (NIRF 2025, institute fee circulars, JoSAA 2025 round 6) with URLs and SHA-256 hashes
- `partial/`: 19 partly verified IIT records (NIRF 2025 placement row)
- `cutoffs_2025.sqlite`: JoSAA 2025 round 6, 11,944 rows, 128 institutes. Restored to `data/cutoffs_2025.sqlite` on 2026-11-12 (D-59) so branches other than Computer Science show cutoff-only options again
- `VERIFICATION_REPORT.md`: field-by-field evidence report for the 11 audited records

To return to this data: `git mv` the folders back to `data/` and `git revert` the commit that moved them (or merge `main`).
