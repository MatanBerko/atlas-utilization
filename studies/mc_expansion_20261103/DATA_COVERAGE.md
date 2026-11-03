# Data coverage check (A2 step 2, 3 Nov 2026) — READ-ONLY

**Result: the 25 Oct data production used EVERY published file of all 10 data records. No data file was missed.**
Nothing in the data code or outputs was changed. All numbers VERIFIED BY RUNNING (`data_coverage.py`, live portal, 3 Nov
2026; raw: `evidence/data_coverage.json`).

Why this was checked: the production driver gets its file list from the portal file page 1
(`fetch_file_list`). That page shows at most 5 index files, which cut short 6 of the new MC samples (P1). The data
driver still uses this page-1 list (unchanged; the complete list is used for MC only).

| record | dataset (Run2016G/H) | files used on 25 Oct | page 1 now | complete index | portal number_files | missing |
|---|---|---:|---:|---:|---:|---:|
| 30521 | DoubleEG G | 47 | 47 | 47 | 47 | 0 |
| 30554 | DoubleEG H | 86 | 86 | 86 | 86 | 0 |
| 30522 | DoubleMuon G | 29 | 29 | 29 | 29 | 0 |
| 30555 | DoubleMuon H | 28 | 28 | 28 | 28 | 0 |
| 30528 | MuonEG G | 29 | 29 | 29 | 29 | 0 |
| 30561 | MuonEG H | 19 | 19 | 19 | 19 | 0 |
| 30529 | SingleElectron G | 71 | 71 | 71 | 71 | 0 |
| 30562 | SingleElectron H | 80 | 80 | 80 | 80 | 0 |
| 30530 | SingleMuon G | 70 | 70 | 70 | 70 | 0 |
| 30563 | SingleMuon H | 82 | 82 | 82 | 82 | 0 |
| **total** | | **541** | | | | **0** |

Inputs and checks:
- The 25 Oct file lists come from `studies/fullrun_20261025/evidence/mappings_data/<Dataset>_mapping.txt`, which are
  byte-identical to `work/fullrun_20261025/mappings_data/` (checked with `cmp`, 3 Nov).
- The URL list the 25 Oct mapping generator wrote, `full_files.json`, is copied to `evidence/data_full_files_25oct.json`.
  For every record the 25 Oct URLs equal today's page-1 list file by file, and the file indices used are
  0 … n−1 with none skipped.
- Every data record has fewer than 5 index files, so page 1 shows them all.
