# m0m1j0 design-check scripts

Phase 0 (design only) read-only data checks. None of these scripts are
imported by, or modify, any shared pipeline file, config, or test.

## Data access

The group's usual CMS Open Data access path (XRootD, `root://eospublic.cern.ch/...`,
via `services/metadata/fetcher.py`) needs the `XRootD` Python package,
which has no prebuilt wheel for Windows and fails to build from source
here (`pip install xrootd` → `RuntimeError: Cannot find CMake executable`).
The Weizmann cluster (`wipp-home` / `wipp-campus`) was also unreachable
from this machine (`ssh`: `Could not resolve hostname` / `Network is
unreachable`).

Instead, these scripts read the **same EOS-hosted files over HTTPS**,
using the EOS/XRootD gateway's own HTTP(S) interface (confirmed live:
`Server: XrootD/5.9.5`, `Accept-Ranges: bytes` — genuine byte-range
streaming). The gateway's TLS certificate chain includes a self-signed
certificate in this environment, so **TLS verification is disabled for
this read-only access to public, non-sensitive CMS Open Data only**
(see `common.py`'s module docstring). This is a design-check
convenience, not a shared-pipeline change, and should not be copied
into `services/` without a separate decision.

No ROOT file, or any other data file, was kept locally at any point;
only metadata (JSON) and PNG plots were written to disk.

## Exact commands, in order

```
python 00_file_inventory.py       # full portal file list + event counts, both records
python 01_load_and_analyze.py     # branch inventory, rawFactor, cutflow, mass plots,
                                   # overlap+outliers, binning comparison
python 07_bins_after_peak.py      # corrected "bins after the peak" check (imports
                                   # 01_load_and_analyze.py by file path to reuse its
                                   # selection functions; does not re-run it)
```

Both were run from this directory (`studies/m0m1j0_cms/design_checks/`)
with the repository's own Python 3.13 environment (already had `uproot`
5.6.2, `awkward` 2.13.0, `matplotlib`, `numpy`; no new packages were
installed into the tracked environment — a throwaway venv was used only
to test, and fail, the `xrootd` package install, and was discarded).

## Exact inputs used

- **Record 30522 (DoubleMuon Run2016G)**, file index 0 of 29 (portal
  order, unmodified): `05DD095C-F6C3-9A4F-9FB3-348A5A6403D5.root`,
  2,155,974,646 bytes, 2,315,223 total events in the file. First
  500,000 events read.
- **Record 30555 (DoubleMuon Run2016H)**, file index 0 of 28:
  `127C2975-1B1C-A046-AABF-62B77E757A86.root`, 2,016,828,178 bytes,
  2,147,195 total events in the file. First 500,000 events read.
- Full file lists, sizes, and per-file event counts for **every** file
  in both records: `00_file_inventory.json` (used for Section I job
  sizing, not for the other checks).
- Golden JSON: `data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`
  (already in the repo, unmodified), loaded via
  `services.parsing.validated_runs.ValidatedRunsFilter` — imported
  read-only, not edited. SHA-256 of the loaded file (printed by the
  script): `a7dd83fd22738364c1b0028629319409f0b37af2da32b7b9fabfdf73704117c9`.

## Output files (all committed)

| File | What it is |
|---|---|
| `00_file_inventory.json` | Every file in both records: URI, HTTP size, event count |
| `01_branch_inventory.json` | Verbatim branch titles + presence, both files; HLT firing fractions |
| `02_rawfactor_summary.json` | `Jet_rawFactor` distribution, both files |
| `03_cutflow.json` | Proposed-selection cutflow, both files |
| `04_mass_plots_summary.json` | Dimuon sanity check + turn-on-feature summary numbers |
| `05_overlap_and_outliers.json` | Muon-jet overlap stats (geometric + `Jet_muonIdx` corroboration) + top-mass outlier table |
| `06_binning_comparison.json` | Fixed vs. paper-style variable binning bin counts |
| `07_bins_after_peak.json` | Corrected "bins after the histogram's peak" check (fixed 10 GeV/0-10 TeV grid, same peak convention as `_apply_peak_removal_to_histogram`), 4 selection variants |
| `plots/*.png` | Every plot referenced in `DESIGN.md`, including `bins_after_peak_{i,ii,iii,iv}_*.png` |

## Reproducing

Re-running will hit the portal and the EOS gateway again; file index 0
of each record's list is used deterministically (not randomly sampled),
so results should reproduce unless the portal's file order changes
(see `impl_checks/signal_sumw_notes.md:75` in `studies/hgg_cms/` for
this project's own documented experience of that actually happening
once, for a different record — ttH, record 67611, a same-day 15-vs-16
file-count discrepancy) or the files themselves are updated.
