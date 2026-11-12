# Supplied dataset (not audited)

These 22 CSV files came from `rehackathonfileseom.zip` (SHA-256 `168735504558b14a5b3832df183d62893721c7b490e0b7064cf9bb64a9fe69c3`),
supplied by the project owner on 2026-11-12 and used as the app's data under decision D-57.

They are copied unchanged. They are **not** source-verified: the review in `DATA_ZIP_REVIEW.md` found placeholder values, unreal hashes
and URLs, and no agreement with the previously verified data. The app therefore labels every record "Supplied dataset, not audited".

`scripts/build_supplied_records.py` turns the category files (iits, nits, iiits, gftis, state_private) into `data/colleges/*.json`.
`b_schools.csv`, `branch_placements.csv`, the trend files and the other tables are kept here but not loaded yet.
