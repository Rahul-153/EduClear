# Review of `rehackathonfileseom.zip` (2026-11-12)

**Verdict: do not use it as data.** The numbers are not from the official sources they cite, they disagree with what we have already verified, and the evidence and "verified" columns are not real. It can only serve as a list of institute names to research and as a source of schema ideas.

Nothing was copied into the project. The zip was unpacked into a scratch folder and every check below was run on it. Two identical copies exist (the project folder and Downloads, same SHA-256 `16873550…69c3`). The zip in the project folder is untracked; keep it out of git.

## What is in it

22 CSV files, 252 KB, plain names, no paths outside the archive.

| Group | Files | Rows |
|---|---|---|
| Institute lists | `colleges_master` 118, `iits` 23, `nits` 31, `iiits` 26, `gftis` 10, `state_private` 18, `b_schools` 10 | 118 institutes in all |
| Placement | `placement_audits` 118, `placement_denominators_vintage_audit` 33, `branch_placements` 27, `headline_packages_audit` 36 | |
| Cost | `fee_structures` 118, `fee_structures_harmonized` 23, `living_costs_7th_cpc` 55 | |
| Cutoffs | `cutoffs_master` 369 (all 2025), `cutoffs_historical_trends` 108, `josaa_csab_cutoffs_trends` 40, `percentile_to_rank_cdf` 37 | |
| Evidence | `data_sources_manifest` 118, `evidence_vault_manifest` 22 | |
| Other | `statutory_accreditation` 62, `ugc_refund_rules` 5 | |

## Why it fails

### 1. It disagrees with our verified data (the decisive check)

| Comparison | Result |
|---|---|
| Our 11 audited colleges, eligible students | 0 of 11 agree. NIT Calicut agrees on placed (799) and median (12.5) only; its eligible count differs (850 vs 826) |
| Our 19 partly verified IITs, eligible and placed | 0 of 18 agree (IIT ISM Dhanbad is not in the zip) |
| 2025 round 6 closing ranks against the real JoSAA table | 0 of 166 comparable rows match. Examples: IIT Madras CSE 148 in the zip, 171 in JoSAA; IIT Kharagpur 279 vs 466; IIT Roorkee 412 vs 592 |
| Total 4-year cost | Different for all 11 audited colleges |

Our figures trace to saved official PDFs with hashes; the zip's do not.

### 2. Values are templates, not measurements

| File | Finding |
|---|---|
| `placement_audits` | 118 colleges, only 24 distinct value sets. 99 rows (83%) share their numbers with another college. One set (900 / 780 / 620 / 9.5) is used by 28 colleges |
| Thirteen IITs | Bhilai, Bhubaneswar, Dharwad, Gandhinagar, Indore, Jammu, Jodhpur, Mandi, Palakkad, Patna, Roorkee, Ropar and Tirupati all show 670 eligible, 590 placed, median 15.5 |
| `fee_structures` | 118 colleges, 41 distinct value sets; 94 rows (79%) shared. 14 colleges have identical fees (125000 / 30000 / 68000) |
| `cutoffs_master` | 305 of 369 rows (82%) repeat another college's values. 27 colleges share the same CSE Other-State closing rank (18,000) |

### 3. The files contradict each other

- The same college's eligible, placed and median figures differ between the category file (e.g. `iits.csv`) and `placement_audits` in **98 of 98** cases. IIT Delhi: 1,420 / 1,280 / 22.0 in one file, 1,190 / 1,080 / 20.5 in the other.
- `fee_structures` and `fee_structures_harmonized` give different total costs for all 23 colleges that appear in both.
- Every `fee_structures` total differs from its own components. On the row checked (IIT Madras) the total is ₹10,000 higher than the sum, which equals the refundable caution deposit; our rule (D-19) excludes refundable deposits.
- IIT Bombay: headline package "withheld" in one file, highest package 120 LPA in `branch_placements`.
- IDs do not join: at least 10 institute ids in the category files are not in `colleges_master` (for example `iiit-delhi`, `iit-ism-dhanbad`, `fms-delhi`), and 20 master ids appear in no category file.

### 4. Evidence and "verified" claims are not real

| Claim | Finding |
|---|---|
| "Audited & Verified" | Present on the institute rows, but nothing backs it |
| SHA-256 hashes | 6 are the hash of an empty file (`e3b0c442…b855`). 11 are malformed (65 characters, patterned hex such as `d1e2f3a4b5c6d7e8…`). 7 hashes are reused across rows |
| Source URLs | All 118 use `nirfindia.org/2025/declaration/Engineering_<id>.pdf`, not the real NIRF pattern we use (`/nirfpdfcdn/2025/pdf/Engineering/IR-E-…pdf`) |
| Publication dates | All 118 say 2024-08-12, though the documents are titled NIRF 2025, which was released on 4 September 2025 |
| Evidence vault | 22 documents for 118 institutes. Every row has the same extractor (`agent-datagaps-trust`), the same verifier (`agent-verifier`) and a timestamp of 2026-11-12 04:30 UTC. Verification by software agents that wrote the data is not independent verification |

### 5. Smaller checks

- `ugc_refund_rules`: the five refund percentages (100, 90, 80, 50, 0) match our sourced UGC table, but the processing charge for the 100% tier is given as "no more than ₹1,500". Our source says up to 5% of fees, maximum ₹5,000.
- `percentile_to_rank_cdf`: the overall rank column equals our own formula on all 37 rows, so it adds nothing; the OBC, EWS, SC and ST rank columns have no stated source.
- `living_costs_7th_cpc`: compared for two IITs only. Indore agrees (Y); Bhilai differs (ours Y from the Durg-Bhilai agglomeration entry, zip Z). The monthly cost split has no cited source.
- 83 of the 2025 round 6 rows could not be matched to a JoSAA row. About 36 colleges are not in JoSAA (BITS, DTU and others); the rest I did not investigate, so I count them as unchecked, not wrong.

## What can be used

| Use | Status |
|---|---|
| As verified data in the app or dataset | **No** (breaks the zero-synthetic rule, `AGENT_MANUAL.md` section 4) |
| Institute names, cities and states as a candidate list to research from official sources | Possible, after checking each against NIRF or JoSAA; the 82 that map to JoSAA are already in our cutoff table |
| Schema ideas: branch-level placement table, a "denominator vintage" audit, per-field status | Useful as design input; our own plan already covers most of it |
| UGC refund percentages | Already in `data/admissions/refund_policy.json`, from the official notice |

## Recommendation

1. Do not merge or commit it. Move the zip out of the project folder so a `git add -A` cannot pick it up (I did not move it).
2. Ask whoever produced it for the real source documents behind the figures. If PDFs with real hashes exist, I can ingest them through our normal pipeline (saved snapshot, hash, two readings, gates).
3. Meanwhile, the gaps in `DATA_GAPS.md` are best closed from official files: NIRF 2025 PDFs for all ranked institutes, CSAB rounds, then the state CET portals.

## Questions

1. Where did the zip come from? Names inside it (`agent-datagaps-trust`, `agent-verifier`) suggest it was produced by AI agents; if so, they likely filled gaps they could not source.
2. Do you want me to move the zip out of the project folder?
3. Should I start the official NIRF 2025 fetch for all ranked institutes (plan C2), which is the largest real gap this zip claimed to fill?
