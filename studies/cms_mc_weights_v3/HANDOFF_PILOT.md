> **Note (14 Oct 2026):** this describes the pre-rebuild branch `feature/cms-mc-weights-v3` (based on the old master `db1bd32`). On the rebuilt master the work was ported to `feature/cms-mc-on-master-20261014`; there, upstream's `services/storage/sqlite_shards.py` is NOT edited: the D3 sibling-aware prune lives in `studies/cms_mc_weights_v3/deliver/cms_shard_pruning.py` and only the MC code calls it. Paths, commits and job IDs below refer to the old branch.

# HANDOFF — CMS MC weighting PILOT

**Read this first when re-pasting the pilot prompt.**

**Branch:** `feature/cms-mc-weights-v3`
**Work directory (reuse this, do not create a new one):**
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_pilot_20261011/`

**Session 1 ran the pilot TO THE END.** Production, both builds, the build
analysis and the data/MC comparison are all complete. Nothing is still
running. Every number below is **VERIFIED BY RUNNING** unless marked
otherwise.

---

## Status

| Stage | State |
|---|---|
| Part 1 — timings, projections, quota | **done** |
| Part 2 — production, 98 files | **done, 98/98 succeeded, 0 failures, 0 resubmits** |
| Part 3a — default build | **done** |
| Part 3b — unweighted-peak build + comparison | **done** |
| Part 3c — negative/empty-bin inventory | **done** |
| Part 3d — histogram and final-state counts | **done** |
| Part 4 — data vs MC, P1–P5 | **done** |

## Pinned commits

Jobs ran from a checkout pinned per stage; the checkout was **not** moved
while any job was running.

| Commit | Used by |
|---|---|
| `cbfb837` | the two timing jobs and all 98 production jobs |
| `9773b1c` | the production audit |
| `08bc459` | the three builds, the build analysis, the data/MC comparison |

## Jobs

| Job ID | What | Result |
|---|---|---|
| `5208385` | timing, 35669 file 30 (largest in the pilot) | exit 0, 257 s, 2.27 GB |
| `5208393` | timing, 67801 file 5 | exit 0, 979 s, 3.06 GB |
| `5208623[1-49]` | **67801 TTTo2L2Nu** production | 49/49 exit 0 |
| `5208624[1-41]` | **35669 DYJetsToLL_M-50 NLO** production | 41/41 exit 0 |
| `5208625[1-8]` | **37728 GluGluHToZZTo4L_M125** production | 8/8 exit 0 |
| `5208867` | build 3a (defaults) | exit 0, 31 min, 12.5 GB |
| `5208868` | build 3b (`--peak-on unweighted`) | exit 0, 31 min, 10.3 GB |
| `5208869` | build, unpruned (`--min-events-per-fs 1`), Part 4's input | exit 0, 49 min, 11.2 GB |
| `5208987` | Part 3b/3c analysis | exit 0, 9 min |
| `5208988` | Part 4 data vs MC | exit 0 |

Production requests: `mem=6gb`, `walltime=02:00:00`, `io=25`, queue `N`,
`#PBS -m n`, logs into `logs/<record>/` **created before submission**.
Builds: `mem=64gb` (32–96 GB for the analysis/comparison), `walltime=08:00:00`.
The builds were run as jobs, not interactively, because they hold every
pilot shard's masses and weights in memory at once.

---

## Part 1 — sizing

### The delivered DATA production, for reference
390 jobs, 645,377,261 events: median 182 s/file, max 1,184 s, median
7,204 ev/s, 28.8 CPU hours total.

### Two MC timing jobs

| | 35669 file 30 (DY) | 67801 file 5 (ttbar) |
|---|---:|---:|
| events read | 1,936,303 | 1,428,000 |
| stored | 698,326 (36.1%) | 825,785 (57.8%) |
| **events/second** | **7,607** | **1,463** |
| peak memory | 2.27 GB | 3.06 GB |
| output | 85 MB | 387 MB |
| rare4 final-state groups | 113 | 209 |

**ttbar is 5.2× slower per event than DY** and 4.5× larger on disk, because
it carries nearly twice the distinct final-state labels: the funnel's cost
tracks labels × signatures, not events. Sizing the pilot from the DY file
alone would have under-requested fivefold — measuring a second sample was
worth the six minutes.

Requests: walltime = 2 × the worst projection at the **slower** measured rate
(worst file ≈ 27 min) ⇒ **2 h**; memory = 1.5 × the 3.06 GB peak, rounded up
⇒ **6 GB**. No file was projected anywhere near the 48 h stop-and-ask
threshold.

### Inputs, re-checked against the portal before anything was submitted
49 / 41 / 8 files and 43,546,000 / 71,839,442 / 1,000,000 events, each
matching the portal exactly; every file's Runs `genEventCount` equals its
`num_entries` (`evidence/pilot_inputs.json`).

### Quota — **needs attention**
Space is a non-issue: 90 GB used of 4 TB before the pilot, 134 GB after.

**File count is not.** The account held 148,066 files against a soft quota of
150,000 and a hard limit of 200,000. The two timing jobs took it to 150,002,
starting a 7-day grace period; the pilot brought it to about 152,200. Nothing
failed and the hard limit is ~48,000 away, but the account now sits above its
soft quota and old output will need clearing. **Nothing was deleted here** —
every existing output directory is read-only by instruction.

---

## Part 2 — production

| record | sample | expected | ok | failed | events read | stored | stored only via Ele27 | CPU h | capped |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 67801 | TTTo2L2Nu | 49 | **49** | 0 | 43,546,000 | 25,165,391 (57.8%) | 8,019,016 | 15.21 | 0 |
| 35669 | DYJetsToLL_M-50 NLO | 41 | **41** | 0 | 71,839,442 | 25,888,737 (36.0%) | 7,169,097 | 4.35 | 0 |
| 37728 | GluGluHToZZTo4L_M125 | 8 | **8** | 0 | 1,000,000 | 522,702 (52.3%) | 135,042 | 0.60 | 0 |
| | **total** | **98** | **98** | **0** | **116,385,442** | **51,576,830** | **15,323,155** | **20.16** | **0** |

* Every per-file Σw self-check passed; no file was excluded, so **no resubmit
  was needed** and the Σw accounting uses all 98 files.
* **Coverage cap never triggered** — 0 capped signatures across the pilot, so
  the maximum scale factor is not applicable.
* **15,323,155 stored events (29.7%) exist only because of the Ele27
  condition** — nearly a third of the sample would have been lost without it.
  They are excluded again from the comparison, to match the data.
* Σw per sample: 3.140127e+09 (67801), 1.220935e+12 (35669), 2.886964e+07
  (37728) — each equal to the header sweep, confirming all files are in.
* Slowest file: 67801 file 30 at 3,022 s (50 min), well inside the 2 h request.

## Part 3 — builds

### 3a / 3d — counts

| | histograms | 
|---|---:|
| 67801 TTTo2L2Nu | 3,283 |
| 35669 DYJetsToLL_M-50 | 2,498 |
| 37728 GluGluHToZZTo4L_M125 | 2,459 |
| **summed SM** | **3,289** |
| total across the three per-sample files | 8,240 |

All read-back assertions passed on every file (TH1D, `fSumw2` of length
nbins + 2, bin error = sqrt(Σw²)). 63 final states survived the
≥100-raw-entries rule applied once over all three samples' combined shards.

### 3b — weighted vs unweighted peak finding

**The choice is NOT neutral, and the evidence favours keeping the default.**

| | |
|---|---:|
| histograms in both builds | 8,240 |
| peak cut lands at the SAME mass | 5,609 |
| peak cut lands at a DIFFERENT mass | **2,631 (31.9%)** |
| median difference (weighted − unweighted) | **−70 GeV** |
| median absolute difference | 90 GeV |
| range | −2,210 to +1,050 GeV |

The sign is consistent and the mechanism is clear. Every one of the ten
largest differences is a **DY** histogram in a high-jet-multiplicity
category, and in every case the weighted peak is far **lower**:

| histogram | weighted | unweighted | difference |
|---|---:|---:|---:|
| `mass_j0b0_cat_0ex_1mx_7jx_1bx` | 290 | 2,500 | −2,210 |
| `mass_m0j0b0_cat_0ex_1mx_7jx_1bx` | 430 | 2,600 | −2,170 |
| `mass_m0j0j1b0_cat_0ex_1mx_7jx_1bx` | 780 | 2,950 | −2,170 |
| `mass_j0j1j2b0_cat_0ex_1mx_7jx_1bx` | 900 | 3,020 | −2,120 |
| `mass_j0j1j2j3_cat_0ex_1mx_9jx_0bx` | 370 | 2,440 | −2,070 |
| `mass_m0j0j1j2_cat_0ex_1mx_9jx_0bx` | 370 | 2,430 | −2,060 |
| `mass_j0j1j2_cat_0ex_1mx_9jx_0bx` | 290 | 2,320 | −2,030 |
| `mass_m0j0j1_cat_0ex_2mx_7jx_1bx` | 480 | 2,240 | −1,760 |
| `mass_e0m0j0b0_cat_1ex_2mx_1jx_1bx` | 180 | 1,870 | −1,690 |
| `mass_m0m1j0j1_cat_0ex_2mx_7jx_1bx` | 630 | 2,310 | −1,680 |

Peak removal keeps masses **at or above** the peak. In a sparse tail the
unweighted rule has many bins tied at the maximum count (often 1), and
"rightmost highest" then picks the furthest one — cutting away nearly the
whole histogram. The weights break those ties, so the weighted peak lands on
the real maximum. **Following PR #35 is not merely harmless here; it avoids a
pathology of the unweighted rule on sparse spectra.** The default is
unchanged, as instructed.

### 3c — negative / empty bins

Non-positive bins inside each histogram's filled range, split by cause:

| file | histograms | affected | bins ≤ 0 | of which EMPTY (no entries) | of which CANCELLING (filled, still ≤ 0) |
|---|---:|---:|---:|---:|---:|
| summed SM | 3,289 | 2,024 (62%) | 47,279 | 44,146 (93%) | **3,133** (3,123 strictly < 0) |
| 35669 DY | 2,498 | 1,950 | 52,690 | 45,849 | **6,841** |
| 67801 ttbar | 3,283 | 341 | 9,470 | 9,256 | 214 |
| 37728 ggH | 2,459 | 776 | 31,568 | 31,561 | 7 |

* **93% of the problem is empty bins, not negative weights** — a statistics
  problem, whose remedies (more MC, wider bins) differ entirely from the
  negative-weight one.
* The cancelling bins are overwhelmingly **DY**'s, exactly as the design
  round predicted from its 16.3% negative-weight fraction. ttbar and ggH,
  both at ~0.4%, contribute almost none.
* Summing the samples *reduces* cancelling bins (6,841 + 214 + 7 = 7,062 per
  sample, but 3,133 in the summed file): other samples fill the bins DY drove
  negative.
* `plots/pilot/P3c_negative_bins.png` shows the shape of it: the negative
  bins sit in the sparse high-mass tails, never in the populated core.

## Part 4 — data vs simulation

Read from the stored events of both sides, **before** the Z cut, peak removal
and the outlier split. Data is the delivered four-dataset de-duplicated set
(390 shards, read-only); MC is the union of the four acceptance flags with
Ele27-only events excluded (1,480,897 entries dropped on that rule).
Absolute normalisation at L = 16.393 fb⁻¹; nothing rescaled.

### Integral ratios

| plot | data | MC | data/MC | ± stat |
|---|---:|---:|---:|---:|
| P1 Z peak, μμ | 10,020,867 | 9,693,847 | **1.0337** | 0.0003 |
| P2 Z peak, ee | 5,003,572 | 5,247,950 | **0.9534** | 0.0004 |
| P3 μμ, Z window | — | — | 1.0342 | 0.0003 |
| P3 ee, Z window | — | — | 0.9534 | 0.0004 |
| P4 e-μ | 170,555 | 137,046 | **1.2445** | 0.0030 |

### The pre-stated expectations

1. **Z peaks within ±10% — HELD.** μμ is 3.4% above, ee 4.7% below; both
   inside ±5%, far inside the ±15% flag. Nothing to flag. Lepton ID/trigger
   scale factors and pileup reweighting are still not applied, and the
   luminosity carries 1.2%; the 8% μμ-vs-ee spread is the size one would
   expect from the missing lepton scale factors, which differ by flavour.
2. **The ≥3-jet data excess — PERSISTS, and grows.** Per-bin data/MC for
   Z-window events:

   | light jets | 0 | 1 | 2 | 3 | 4 | 5+ |
   |---|---:|---:|---:|---:|---:|---:|
   | μμ | 1.035 | 1.018 | 1.032 | **1.279** | **1.573** | **2.030** |
   | ee | 0.954 | 0.938 | 0.944 | **1.174** | **1.518** | **2.108** |

   The previous muon-only study reported ~29% at ≥3 jets; this reproduces it
   almost exactly at 3 jets (27.9% in μμ) and shows it is not a plateau — it
   doubles by 5+ jets, in both channels. **b-jet** multiplicity is flat by
   contrast (μμ 1.03 / 1.11 / 1.06, ee 0.95 / 1.03 / 0.91), so the excess is
   specific to light jets.
3. **e-μ, MC below data — HELD, by 24.4%.** The data/MC ratio is **flat**
   across the whole 0–500 GeV range at ≈1.25, which is what a missing
   *normalisation* looks like rather than a shape problem: single top,
   dibosons, W+jets and fakes are simply not in the pilot. Reported, not
   explained away.
4. **Peak shape — no mass-scale or width problem.** Gaussian-core fits
   (plain Gaussian least squares on ln(counts), 85–97 GeV; stated as such,
   not a Breit-Wigner):

   | | data peak | MC peak | shift | data σ | MC σ | width ratio |
   |---|---:|---:|---:|---:|---:|---:|
   | μμ | 90.723 | 90.773 | **−0.050 GeV** | 2.944 | 2.929 | 1.005 |
   | ee | 90.498 | 90.530 | **−0.032 GeV** | 3.144 | 3.137 | 1.002 |

   Mass scale agrees to better than 0.06 GeV and resolution to 0.5%.

### P5 — the 4-lepton mass (70–200 GeV)

| channel | data events | MC weighted |
|---|---:|---:|
| 4μ | 12 | 4.08 ± 2.67 |
| 4e | 6 | 0.057 ± 0.004 |
| 2e2μ | 19 | 2.16 ± 1.92 |

Very few events, as expected with 25 GeV lepton thresholds. Data exceeds MC
because the ZZ continuum — the dominant 4-lepton background — is not in the
pilot. The large MC errors come from a handful of high-weight DY events.

### Plots

`studies/cms_mc_weights_v3/plots/pilot/`: `P1_zpeak_mumu.png`,
`P2_zpeak_ee.png`, `P3_jet_multiplicity_zwindow.png`, `P4_emu_mass.png`,
`P5_fourlepton_mass.png`, `P3c_negative_bins.png`.

---

## One fix was needed, and why

Build 3a failed with `sqlite3.OperationalError: unable to open database
file`. Diagnosed by running, not guessed: the shared
`iter_arrays_for_signature` / `list_signatures` open a **new** sqlite
connection per call and close it only when the garbage collector gets round
to it (`with sqlite3.connect(...)` commits but does not close). Measured on a
real shard, open file descriptors climb and fall irregularly; with 28,788
signatures in a ttbar shard and `ulimit -n` = 1024 on the analysis node, the
count spikes past the limit.

The fix is **confined to this study**: `read_shard_arrays()` reads a whole
shard in one pass through one read-only connection, and the builder and the
comparison script use it instead of per-signature calls. It is also much
faster. `services/` was deliberately **not** changed — those functions are on
the delivered data path — so no data-unchanged re-check was required, and
`run_dataset_on_file.py` was not touched at all. Both self-check suites still
pass, 66 of 66. The root cause is recorded here for whoever next has licence
to fix `services/`.

## Work directory layout

```
work/cms_mc_v3_pilot_20261011/
    repo/                pinned checkout
    mappings/            PBS mapping files
    runs/                production output, one directory per file (98)
    runs_timing/         the two Part 1b timing jobs
    build_default/       3a: per-sample + summed ROOT, build report
    build_unweighted/    3b
    build_unpruned/      Part 4's input (nothing pruned, shards carry _mcw)
    scratch_*/           the builders' scratch copies (kept)
    analysis/            3b/3c report and PNG
    plots/               P1-P5 and the comparison JSON
    evidence/            pilot_inputs.json, pilot_production_audit.json
    logs/{timing,67801,35669,37728,build}/
```

Read-only and untouched throughout: `output/` (including the delivered data
shards), `work/cms_mc_v2/`, `work/cms_mc_v3_design_*`, `work/cms_mc_v3_impl_*`.
`/storage/agrp/marybo/` was never accessed; no ACL was changed; nothing was
shared with anyone. Jobs wrote nothing to the real `$HOME`.

## Unchanged, by instruction

No selection, object definition, threshold, binning, Z cut, histogram name,
registry value or builder default was touched. No sample beyond the three
pilot records was run. Nothing was delivered to anyone.

## The logical next step

1. **Put the ≥3-jet excess to Maryna and Yuval.** It is now measured in two
   channels with the full pilot and it grows with jet multiplicity, while
   b-jet multiplicity stays flat. Candidate causes that this round did not
   test: pileup jets (the design round found a generator-independent pileup
   mismatch and `Pileup_nTrueInt` is already stored, so a pileup reweighting
   can be applied at build time without re-running), jet energy resolution,
   and DY+jets matrix-element merging above the generated multiplicity.
2. **Answer the negative/empty-bin question with these numbers in hand** —
   93% empty vs 7% cancelling changes which remedy is appropriate.
3. The 3b evidence argues for keeping the weighted peak default; it is worth
   putting to Yuval as a closed question rather than an open one.
4. Only then consider a wider MC production. Nothing here is ready to deliver.
