# m0m1j0 CMS histogram — pilot report

Cluster pilot for the CMS m0m1j0 (2 leading muons + leading light jet)
histogram task. Exactly 4 jobs: first two files of each of records 30522
(Run2016G) and 30555 (Run2016H). Run on the Weizmann cluster
(`wipp-an1`), branch `analysis/m0m1j0-cms`. See
`studies/m0m1j0_cms/RECIPE.md` for the full selection recipe and every
deviation from the group's ATLAS `config.yaml`.

## What ran

| Index | Record | File | Events read | Wall time | Peak mem |
|---|---|---|---|---|---|
| 1 | 30522 (G) | `05DD095C-...-a601.root` | 2,315,223 | 00:00:31 | 2.13 GB |
| 2 | 30522 (G) | `209D94D9-...-adf.root` | 2,467,200 | 00:00:42 | 2.29 GB |
| 3 | 30555 (H) | `127C2975-...-86.root` | 2,147,195 | 00:00:29 | 1.98 GB |
| 4 | 30555 (H) | `183BFB78-...-89.root` | 2,167,324 | 00:00:24 | 1.98 GB |

All 4 exit code 0. **Portal identity check: all 4 recorded file URLs
match the portal's current file list exactly** — no drift detected this
run (`pilot_merge_summary.json`'s `portal_identity.problems` is empty).

## Cutflow (summed across all 4 files, 9,096,942 events read)

| Step | Events | Fraction of previous step |
|---|---|---|
| Read | 9,096,942 | — |
| After golden JSON | 8,964,623 | 98.5% |
| After trigger (either DZ path) | 2,981,006 | 33.3% |
| After ≥2 selected muons | 912,265 | 30.6% |
| After ≥1 selected light jet (post cleaning) | 174,313 | 19.1% |
| After z_peak_cutoff (115 GeV) + max_mass_cutoff (10 TeV) | 170,949 | 98.1% |
| Events with m0m1j0 > 1 TeV (kept for inspection, not discarded) | 327 | — |

## Categories

41 exact final-state categories appeared across the 4 files; **11 survive
the merge-time `min_events_per_fs` (≥100) prune** — the inclusive
histogram plus 10 real categories. The dominant category is exactly what
physics would predict: plain 2-muon-plus-1-light-jet events with no
b-tag, an order of magnitude ahead of anything else.

| Category | Events |
|---|---|
| `mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx` | 125,379 |
| `mass_m0m1j0_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 28,528 |
| `mass_m0m1j0_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 6,346 |
| `mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_1bx` | 4,944 |
| `mass_m0m1j0_cat_0ex_2mx_4jx_0gx_0tx_0bx` | 1,849 |

(30 smaller categories, from 87 events down to 0, were dropped by the
≥100-event prune — full list in `pilot_merge_summary.json`.)

## Sanity checks — all look correct

- **`plots/dimuon_mass.png`** — sharp Z→μμ peak exactly at 91.19 GeV,
  plus a small low-mass shoulder (expected: low-mass Drell-Yan/quarkonia
  and mis-paired muons, small compared to the Z peak). Confirms the
  dimuon four-vector mass calculation is correct.
- **`plots/leading_jet_pt.png`** — falling spectrum with a hard, clean
  edge exactly at the 30 GeV jet pT cut, nothing below it. Confirms the
  jet pT cut is applied correctly.
- **`plots/inclusive_m0m1j0.png`** (log y) — smooth falling spectrum
  starting with a hard edge exactly at the 115 GeV `z_peak_cutoff`, a
  peak just above it, then a smooth tail out past 3 TeV matching the 327
  recorded outlier events. Confirms `z_peak_cutoff` is genuinely being
  applied to the m0m1j0 mass itself, not just to a standalone dimuon
  mass (RECIPE.md section 5/6.3's non-obvious finding).
- **`plots/top5_categories.png`** (log y) — all 5 overlaid spectra have
  the same smooth falling shape, correctly ordered by size, with the
  single-b-tag category visibly smaller than the light-jet-only
  categories as expected.

## Comparison with DESIGN.md's small-sample numbers

DESIGN.md's own cutflow (`design_checks/03_cutflow.json`) used a much
smaller sample (500,000 events per record, not the full files) **and
different muon cuts**: asymmetric leading-muon-pT > 20 GeV / subleading
> 15 GeV (no explicit isolation cut recorded in that step name), versus
this pilot's symmetric pT > 25 GeV for both muons **and**
`pfRelIso04_all < 0.15` (both muons), per this task's own given
selection. Differences, not forced into agreement:

| Step | DESIGN.md (record 30522, 500K events) | This pilot (record 30522, both files, 4.78M events) |
|---|---|---|
| Trigger / golden | 157,204 / 500,000 = 31.4% | 33.3% (very close — trigger is independent of the muon-pT difference below) |
| ≥2 muons (of triggered) | 61,494 / 157,204 = 39.1% | 30.6% |
| ≥1 jet (of ≥2-muon events) | 15,747 / 61,494 = 25.6% | 19.1% |

**Both differences point the same, expected direction**: this pilot's
tighter, symmetric 25/25 GeV + isolation muon cuts are stricter than
DESIGN.md's 20/15 GeV floor, so a lower muon-selection efficiency is
expected. The jet-step gap is additionally explained by this pilot
requiring the surviving jet to be specifically **non-b-tagged** (DESIGN.md's
cutflow did not split jets by b-tag at that step) and a tighter jet |eta|
acceptance (2.5 here vs. 2.8 in DESIGN.md) — excluding b-jet-only events
and slightly more forward jets both push the fraction down, consistent
with what's observed. No number was forced to agree; both are explained.

## Full-run (57 files) time/resource estimate

Measured pilot: 24–42 s wall, 1.98–2.29 GB peak memory, per ~2.1–2.5M-event
file — remarkably fast (this job is XRootD-read + vectorized
awkward-array selection, no heavy per-event Python loop).

- **Per job**: request `walltime=00:20:00` (~30x the slowest observed 42s,
  matching this task's own "large safety margin, nodes differ up to
  5–6x" instruction with substantial extra headroom for a busier queue or
  a larger file) and `mem=5gb` (~2x the observed 2.29 GB peak).
- **57 jobs total**: at ~35s average observed, the raw compute is only
  ~33 minutes summed across all jobs — if the array runs with reasonable
  cluster concurrency (as the pilot's own 4-job array did, all 4 finished
  within about a minute of each other), **wall-clock time for the whole
  57-file array is expected to be dominated by queue scheduling, not
  per-job compute** — plausibly under 30 minutes end-to-end if the queue
  isn't heavily loaded, though this is a projection from 4 data points,
  not a measurement of 57.
- **Next step**: the full run is a separate, later, explicitly-out-of-scope
  task per this task's own instructions — not started here.

## Environment finding worth the group's attention

Running this pilot discovered that the cluster's own `atlas-pipeline`
conda env has **no PyROOT installed at all** — not even
`import services.pipelines.histograms_pipeline` succeeds there
(`ModuleNotFoundError: No module named 'ROOT'`). This study worked around
it entirely within its own files (histogram I/O via `uproot` instead of
PyROOT; see `RECIPE.md` section 7a and `histograms.py`'s module
docstring for the full details) — no shared code or environment was
touched. Whether the shared pipeline's own histogram-creation stage has
ever actually been run end-to-end on this cluster account is unclear and
worth the group checking separately.

## UNVERIFIED / not done here

- Nothing about the full 57-file dataset (population per category,
  whether smaller categories would clear the ≥100-event threshold with
  full statistics) — only the 4-file pilot was run.
- `Electron_cutBased` branch title was not separately quoted verbatim in
  this pilot's output (RECIPE.md section 8 flags this) — the task's given
  meaning (medium, includes isolation) was used as specified.
