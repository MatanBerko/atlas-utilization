# Why BumpNet rejects the CMS histograms — evidence, not guesses

**Read-only investigation.** Nothing was regenerated, cropped, or changed.
Every number below traces to a committed JSON file produced by a committed
script (`studies/cms_coverage/investigate_rejection/`), or a `file:line`
quote at commit `30c19a127cce7112cf59290acb0ac141ed97b52c` (the tip of
`deliver/doublemuon-bumpnet` this branch forked from), or is explicitly
marked **UNVERIFIED**.

## Part 1 — complete structural dump of our own histograms

Ran `dump_histogram_structure.py` (uproot-based) on both delivered files.
Full per-histogram detail: `evidence/dump_uncropped.json`,
`evidence/dump_cropped.json` (316 entries each; `evidence/*_min26.json` for
the looser-threshold pair, same pattern throughout).

### `doublemuon_bumpnet_min31bins.root` (uncropped, 316 histograms) — every field IDENTICAL across all 316

| Field | Value (all 316) |
|---|---|
| classname | `TH1F` |
| class_version (ROOT streamer version) | `3` |
| n_bins | `1000` |
| fXmin, fXmax | `0.0`, `10000.0` |
| axis fFirst | `1` |
| axis fLast | **varies, 40–217** (not uniform — see below) |
| axis kAxisRange bit | **set** (`true`) |
| fSumw2 present & non-empty | **`false`** (absent) |
| **bin 1 content** | **`0.0` — all 316** |
| fTsumwx, fTsumwx2 | **`0.0`, `0.0` — all 316** (confirmed separately, not in the table above; see Part 5) |
| fEntries vs. total bin content | **equal for all 316** (0 mismatches) |
| negative or NaN bin content | **none — 0 histograms** |
| underflow, overflow | `0.0`, `0.0` — all 316 |
| n_nonempty_bins | varies, 31–187 |

### `doublemuon_bumpnet_min31bins_cropped.root` (cropped, 316 histograms)

| Field | Value |
|---|---|
| classname, class_version | `TH1F`, `3` — same as uncropped |
| n_bins | **varies per histogram, 31–187** (105 distinct values) |
| fXmin, fXmax | **varies per histogram** (42 / 118 distinct values) |
| axis fFirst | `1` — all 316 |
| axis fLast | **equals n_bins, exactly, for all 316** (confirmed: 0 mismatches) |
| axis kAxisRange bit | **set (`true`) — all 316, same as uncropped** |
| fSumw2 present & non-empty | `false` — all 316, same as uncropped |
| **bin 1 content** | **> 0 for all 316** |
| underflow, overflow | `0.0`, `0.0` — all 316 |

**Two things worth flagging plainly, without speculating about
consequence** (this is what "anything unusual" turned up):

1. **The cropped file's kAxisRange bit is still SET**, even though
   `fFirst=1` and `fLast=n_bins` make the restriction cover the histogram's
   *entire* current range — i.e. structurally "restricted", numerically a
   no-op. A reader that checks the bit alone, without also comparing
   `fLast` to `GetNbinsX()`, cannot tell the cropped file's histograms
   apart from the uncropped file's on this field alone.
2. **`fTsumwx` and `fTsumwx2` are exactly `0.0` for every one of the 316
   uncropped histograms** (and, by inspection of the same field in
   `evidence/dump_cropped.json`, the cropped ones too) — regardless of
   what mass values were actually filled. This is a real, uniform,
   testable structural property, independent of the bin-1 question. See
   Part 4/5 for why, and what a genuine `ROOT.TH1F.Fill()`-built
   histogram looks like on this same field.

## Part 2 — does it survive ROOT itself?

**A real ROOT (6.40.02, with working PyROOT) was found and used, without
touching the shared cluster environment.** PyROOT is confirmed absent
from the shared `atlas-pipeline` conda env (unchanged finding, already
documented in `studies/m0m1j0_cms/histograms.py`'s own module docstring).
Searched instead: no `module` command, no system `root`/`root-config`, no
usable local install anywhere under this account's own storage. Found
`/cvmfs/sft.cern.ch/lcg/views/LCG_110/x86_64-el9-gcc13-opt/setup.sh` — a
read-only, pre-built LCG software stack mounted via CVMFS (a standard,
network-mounted HEP software distribution, not a package installed by
this task) matching this cluster's own platform (AlmaLinux 9.4, x86_64).
Sourcing its `setup.sh` and running `root --version` / `import ROOT`
worked immediately, in a completely separate environment from
`atlas-pipeline` — nothing under `/storage/agrp/berkom/atlas-utilization/envs/`
was touched.

**Result, opening `doublemuon_bumpnet_min31bins.root` with real PyROOT**
(`root_probe.py`, full detail in `evidence/root_probe_uncropped.json`):

- **The file opens without any error or warning**; all 316 keys are
  present and every one loads as a real object (0 load failures).
- `GetBinContent(1)` is `0.0` for **all 316** histograms — the same
  finding as Part 1, now confirmed with real ROOT, not just uproot.
- `GetSumw2N()` is `0` for **all 316** — no Sumw2 array, confirmed by
  ROOT's own C++ code, not just uproot's interpretation of the bytes.
- Repeating both checks on `doublemuon_bumpnet_min31bins_cropped.root`
  (`evidence/root_probe_cropped.json`): file also opens cleanly, 0 load
  failures, and `GetBinContent(1) > 0` for **all 316**.

**A real ROOT being reachable also let this task settle three previously-
open questions with a direct test** (`root_fingerprint_test.py` run with
real ROOT, `root_fingerprint_readback.py` run with uproot on the exact
same two files it wrote — `evidence/fingerprint_realroot.json`,
`evidence/fingerprint_uproot_readback.json`):

1. **A genuine `ROOT.TH1F` filled via real `.Fill()` calls has non-zero,
   data-derived `fTsumwx`/`fTsumwx2`** — filling `[150, 155, 160, 160,
   170]` gives `fTsumwx=795.0` (`=` the sum) and `fTsumwx2=126625.0`
   (`=` the sum of squares), read back identically by both real ROOT and
   uproot. **Our files' `fTsumwx=fTsumwx2=0.0` is therefore not what a
   `hist.Fill()`-built histogram normally looks like** — it is a direct
   consequence of how our files were written (see Part 4).
2. **A fresh `ROOT.TH1F` that never had `.Sumw2()` called on it has an
   empty `fSumw2` array by ROOT's own default** (`GetSumw2N()==0` on the
   real-ROOT side, `fSumw2` length `0` on the uproot-readback side) —
   identical to what our files show. This is **not** evidence of a
   problem with our files; it is ROOT's own ordinary behavior for a
   histogram nobody ever called `.Sumw2()` on.
3. **Real ROOT's own `trim_empty_tail` (the exact function copied
   verbatim from `services/pipelines/histograms_pipeline.py:26-41`,
   run here with real ROOT) produces the identical on-disk encoding**
   our uproot-based workaround does: `fFirst=1`, `fLast=<last filled
   bin>`, `kAxisRange` bit set — byte-for-byte the same pattern, read
   back the same way by both real ROOT and uproot. This resolves an item
   `studies/m0m1j0_cms/histograms.py`'s own docstring explicitly flagged
   **UNVERIFIED** ("no ROOT installation... was found anywhere in this
   repository or on the cluster to compare against byte-for-byte") —
   it is now verified, and it checks out.

## Part 3 — comparison against an ATLAS file that passes

**No ATLAS-produced, shared-pipeline BumpNet histogram file was found** by
a reasonable search of directories this account can already read.
Searched: every `.root` file under this account's own
`/storage/agrp/berkom/` (all CMS — `hgg_zee`, `m0m1j0_cms`,
`cms_coverage`, etc.; one file, `output/reports/m0m1j0_smoketest/...`,
*looked* ATLAS-shaped by its directory name alone, but its own
`m0m1j0_stats.json` records `run_dir: cms_m0m1j0_smoketest_...` and
`records_used: ["30522", "30555"]` — the same CMS DoubleMuon records, not
ATLAS data, despite the name); the shared group area under
`/storage/agrp/` (world-readable for every top-level user directory
checked, per standard Unix permissions — `id` confirms this account is in
group `watlas`, and every directory listed is `drwxr-xr-x` or group-open),
targeted at three plausible-looking directories found via an earlier
filesystem search (`gald` — a `RootCore`-named legacy ATLAS build area;
`hepg1`; `ohadam`) turned up only unrelated old physics analyses (a dark
matter experiment's raw data, GEANT4 shielding simulation output, an old
MSSM Higgs→ττ limit-setting exercise) — none of them CMS/ATLAS Open Data
BumpNet-pipeline output. `config.yaml`'s own `base_output_dir: "/data"`
is a generic template default, not a real convention pointing anywhere.
An exhaustive crawl of the other ~40 group members' private storage areas
was not attempted — disproportionate to what this task's evidence rule
calls for, and not the kind of search "likely under /storage/agrp/" was
meant to invite.

**The exact request to send your supervisor** (this is this part's actual
deliverable, per the task's own instruction): *the full cluster path of
the ROOT file(s) she used to make her comparison plot — the one where the
ATLAS post-processed histogram also shows zero content below ~110 GeV —
including which host/account it lives under, since it does not appear to
be under this account's own `/storage/agrp/berkom/`.*

## Part 4 — what the pipeline's own code says an ATLAS histogram would look like

Quoted directly from `services/pipelines/histograms_pipeline.py` and
`services/pipelines/post_processing_pipeline.py` at the stated commit —
this is the **same, dataset-agnostic code** for ATLAS and CMS (neither
file branches on which experiment produced the input arrays; both operate
purely on generic final-state/combination signature strings and raw mass
arrays).

**Every histogram this code ever creates is built on the full fixed
range**, regardless of what data will be filled into it:

```python
# services/pipelines/histograms_pipeline.py:22-23
FIXED_MASS_MIN_GEV = 0.0
FIXED_MASS_MAX_GEV = 10000.0
```
```python
# services/pipelines/histograms_pipeline.py:648-654 (_create_histogram_single_array;
# the same ROOT.TH1F(..., FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV) constructor call
# appears, unchanged, in every one of this file's four histogram-creation
# functions: _create_histograms_for_signature:344,
# _create_merged_histograms_from_sqlite_signatures:382,
# _create_merged_histograms_streaming:529-532)
nbins = max(1, math.ceil((FIXED_MASS_MAX_GEV - FIXED_MASS_MIN_GEV) / bin_width))
hist_name = f"ROI_{im_array_filename}_width_{bin_width}"
hist = ROOT.TH1F(
    hist_name, hist_name, nbins,
    FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV,
)
```

**The array fed into that histogram has already had everything below the
per-category peak mass removed**, by the time it reaches histogram
creation, whenever the SQLite post-processing path is used (the same path
`studies/cms_coverage/`'s own coverage run used):

```python
# services/pipelines/post_processing_pipeline.py:240-247 (_process_im_sqlite)
peak_mass = _find_rightmost_highest_peak(arr, bin_width, logger)
filtered = arr if peak_mass is None else arr[arr >= peak_mass]
if len(filtered) == 0:
    continue

main_array, outliers_array = _split_by_first_empty_bin(filtered, bin_width, logger)
if len(main_array) > 0:
    writer.append_array(f"{fs_im_key}_main", main_array)
```
```python
# services/pipelines/post_processing_pipeline.py:381 (_split_by_first_empty_bin)
main_array = im_array[im_array < split_mass]
```

`main_array`'s own minimum value is therefore always `>= peak_mass` — the
array handed to histogram-filling never contains anything below the
detected peak for that category.

**Nothing in either file ever resizes a histogram or removes a bin.**
The only two operations that touch already-built bin content are:

```python
# services/pipelines/histograms_pipeline.py:26-41 (trim_empty_tail)
def trim_empty_tail(hist: ROOT.TH1F) -> None:
    last_filled = 0
    for b in range(hist.GetNbinsX(), 0, -1):
        if hist.GetBinContent(b) > 0:
            last_filled = b
            break
    if last_filled > 0:
        hist.GetXaxis().SetRangeUser(
            hist.GetXaxis().GetXmin(),
            hist.GetBinLowEdge(last_filled + 1)
        )
```
— a **display-range-only** change (Part 2's real-ROOT test confirms this
exactly), and:
```python
# services/pipelines/histograms_pipeline.py:625-645 (_apply_peak_removal_to_histogram)
def _apply_peak_removal_to_histogram(hist: ROOT.TH1F) -> None:
    """Zero all bins strictly before the rightmost highest bin."""
    ...
    for bin_idx in range(1, peak_bin_idx):
        hist.SetBinContent(bin_idx, 0.0)
        hist.SetBinError(bin_idx, 0.0)
```
— an alternative, histogram-level peak removal (`SetBinContent(...,
0.0)`, **zeroing in place, never changing `nbins`**), gated behind
`apply_peak_removal_at_histogram_level` (default `False`,
`histograms_pipeline.py:89`) and redundant with the array-level removal
above unless a caller skips post-processing and sets this flag directly.
Either way the histogram keeps its full `nbins` — this code path zeroes
bin 1's *content*, never removes bin 1 itself.

**Conclusion, stated plainly**: for any category whose peak mass is
meaningfully above 10 GeV — true of essentially every real search
channel, and true of the dilepton `z_peak_cutoff` floor (115 GeV) for any
channel this cutoff applies to — **an ATLAS histogram built by this exact
code would also have bin 1 (0–10 GeV) at content `0.0`**, for the
identical structural reason ours does: the histogram is always built on
the full 0–10,000 GeV grid, and the array filled into it never contains
anything below the peak. Nothing in this code treats ATLAS and CMS
differently. This is **not** a measurement of what any real ATLAS
histogram actually contains (Part 3 found none to check) — it is what
the shared code, read directly, would produce if used the same way.

## Part 5 — the rejection criterion: every property a reader could check

No BumpNet reader code is available to this task. Listed below: every
property Parts 1/2/4 make testable, whether our 316 uncropped histograms
satisfy it (from real, measured evidence), and — where untestable without
BumpNet's own code — exactly what would settle it.

| # | Property a reader could check | Our 316 uncropped files | Evidence |
|---|---|---|---|
| 1 | Bin 1 content > 0 | **NO — fails for all 316** | Part 1 + Part 2 (uproot AND real ROOT agree) |
| 2 | `TestBit(kAxisRange)` unset (no display restriction at all) | **NO — set for all 316** | Part 1 (`axis_kAxisRange_set: true`, unique) |
| 3 | `fLast == GetNbinsX()` (the restricted range, if any, covers the whole histogram) | **NO — fails for all 316** (fLast 40–217 vs n_bins 1000) | Part 1 (`axis_fLast_range` vs `n_bins`) |
| 4 | `fSumw2` present/non-empty | NO — fails for all 316, **but this is not a CMS-specific anomaly**: Part 2's real-ROOT test shows a fresh, never-`.Sumw2()`'d histogram has this too, by ROOT's own default, and `histograms_pipeline.py` never calls `.Sumw2()` anywhere | Part 1 + Part 2 (direct test) |
| 5 | `fTsumwx`/`fTsumwx2` non-zero (data-derived, as a real `.Fill()`-built histogram has) | **NO — exactly `0.0` for all 316**, while Part 2's real-ROOT test shows a genuinely `.Fill()`-built histogram has real, non-zero values here | Part 1 + Part 2 (direct test) — **a second, independent uniform anomaly, unrelated to bin 1** |
| 6 | Exactly `nbins=1000` / range `[0, 10000]` fixed across every histogram in the file | **YES — uniform for all 316** (this is what a batch/matrix loader stacking histograms into one array would need) | Part 1 |
| 7 | `classname == TH1F` (not TH1D or other) | YES — matches for all 316 | Part 1 + Part 2 |
| 8 | ROOT streamer `class_version` matches what real ROOT itself writes | YES — `3`, identical to a real-ROOT-written TH1F of the same class | Part 2 (direct test) |
| 9 | Negative or NaN bin content | NO issue — none found, 0/316 | Part 1 |
| 10 | Non-zero underflow/overflow required | Unknown plausibility, but moot as a discriminator: `0.0`/`0.0` uniform for **both** the uncropped and cropped files, so it cannot be what tells them apart if only one is rejected | Part 1 |
| 11 | `fEntries` equals the sum of bin contents | YES — consistent for all 316 | Part 1 (0 mismatches) |
| 12 | File opens without ROOT error/warning; every object loads | YES — 0 load failures, real ROOT | Part 2 |
| 13 | Some minimum/maximum on `n_nonempty_bins` beyond the already-known `>30` | Untestable without BumpNet's own code — our own cut already guarantees `>30`; whether BumpNet imposes a **different** floor/ceiling is unknown | Would need BumpNet's reader code, or a rejection message/log from a real run |
| 14 | Naming convention (`ROI_..._width_10` prefix/suffix) not matching what BumpNet expects | Untestable without BumpNet's own code | Would need BumpNet's reader code or documentation |

**Properties 1, 2, 3 and 5 each independently satisfy "fails for all 316
at once."** Properties 1–3 all trace to the same underlying cause
(post-processing removes everything before the peak; the histogram keeps
the full fixed grid; `trim_empty_tail` only hides this cosmetically) and
would all be fixed together by the cropping already delivered separately
on this branch. **Property 5 (`fTsumwx`/`fTsumwx2`) is a genuinely
separate, independently-uniform anomaly** that cropping does **not**
address — confirmed directly from `evidence/dump_cropped.json`: all 316
cropped histograms also show `fTsumwx=fTsumwx2=0.0`, exactly the same as
the uncropped file, since `to_writable_th1f` writes every histogram in
both files via the identical hardcoded values. Flagged here as a second
candidate, evidenced independently of the bin-1 question, that a
sufficiently strict reader could also be checking.

**Property 6 is the important counter-consideration**: our **uncropped**
files satisfy "identical fixed grid across every histogram in the file" —
our **cropped** files do not (property 6 is what cropping trades away to
fix properties 1–3). If BumpNet's reader assumes every histogram in a
file shares one grid (a common convention for stacking histograms into a
single batch/tensor for a neural network), cropping would fix bin 1 but
could introduce a *different* rejection. This was not testable here (no
BumpNet code, and the cropped files' own pass/fail status with the real
BumpNet feed has not yet been reported by the supervisor).

## What we know / what we do not know

**Proven, with direct evidence, both by reading the raw bytes (uproot)
and by an independent real-ROOT check:**
- Bin 1 is `0.0` in all 316 uncropped histograms, and `>0` in all 316
  cropped ones (Parts 1, 2).
- The file itself is not corrupt or ROOT-incompatible: it opens cleanly
  in real ROOT 6.40.02, every object loads, and its `class_version`
  matches what real ROOT itself assigns (Part 2).
- `fSumw2` being empty is normal ROOT behavior for a never-`.Sumw2()`'d
  histogram, not a defect (Part 2, direct test).
- Our uproot-based `trim_empty_tail`-equivalent write produces the
  byte-identical on-disk encoding real ROOT's own `SetRangeUser` does —
  a previously-`UNVERIFIED` item, now settled (Part 2).
- The shared pipeline's own code, read directly, would produce the same
  empty-bin-1 structure for an ATLAS histogram under the same conditions
  (any category with peak mass above 10 GeV) — this is what the code
  says, not a measurement of a real ATLAS file (Part 4).
- `fTsumwx`/`fTsumwx2` are hardcoded to `0.0` in every one of our 316
  histograms, which is not what a genuinely `.Fill()`-built ROOT
  histogram looks like on this field (Parts 1, 2) — a second, independent
  structural anomaly.

**Not established — genuinely open:**
- **Whether an empty bin 1, specifically, is what BumpNet's reader
  actually checks.** No BumpNet code was available to this task. Properties
  2, 3, and 5 above are equally uniform across all 316 and equally
  unproven/undisproven as the actual cause.
- **Whether a real, passing ATLAS histogram exists anywhere on this
  cluster with a *non-empty* bin 1**, or whether the technical lead's own
  observation (the ATLAS comparison plot also shows zero content below
  ~110 GeV) means the *real* ATLAS file has the identical structural
  signature ours does. Part 3 could not locate that file to check
  directly — this is the single most important open question, and it is
  answerable only with the exact file the supervisor's/technical lead's
  comparison plot came from.
- **Whether the cropped files (already delivered on this branch) actually
  pass BumpNet.** Not tested here — no BumpNet access, per this task's
  own scope.

**The logical next step, both parts of it evidence-driven**: get the exact
cluster path (or a copy) of the ATLAS ROOT file used in the comparison
plot (Part 3's request), and get either BumpNet's reader code or its exact
rejection error message from a real run — either one would convert several
of Part 5's "unknown"s into a settled fact.
