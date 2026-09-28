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

---

# Round 2 — the ATLAS reference file settles it

**The rejection rule is now known, stated by the supervisor**: BumpNet's
loader (`load_ATLAS`) hard-drops any histogram whose bin 1 content is
zero. This resolves Round 1's single biggest open question (Part 5's
"whether an empty bin 1, specifically, is what BumpNet's reader actually
checks"). What remained open going into this round: her reading (a
trimming bug, correlated with jet/b-jet-only categories) versus the
technical lead's reading (nothing removes leading bins; the puzzle is why
*any* histogram passes). Read-only investigation; her file was never
written to, moved, or copied into this repo — only derived summary
numbers, per this task's own instruction.

## Part 1 — the ATLAS reference file

Ran the existing `dump_histogram_structure.py` (unmodified) directly on
`/storage/agrp/marybo/DDP/data_directed_samples_141225/testing_BumpNet/data/atlas_btag_Leptotriggers_test_bumpnet.root`
in place. Full per-histogram detail: `evidence/dump_atlas_reference.json`
(823 entries). Pass/fail and category breakdown computed by the new
`analyze_atlas_reference.py`: `evidence/analysis_atlas_reference.json`.

**823 histograms total. 52 have bin 1 > 0 (would pass); 771 have bin 1 ==
0 (would be rejected)** — confirming her own report that some pass and
some don't, not all-or-nothing like our CMS file.

**All 823 — both the passing and the failing ones — are on the exact same
grid**: `n_bins=1000, fXmin=0.0, fXmax=10000.0`. This is the *only*
`(n_bins, fXmin, fXmax)` combination that appears anywhere in the file —
not 823 histograms split across several grids, one combination, one count
of 823. **This directly answers one of this part's own questions: the
passing histograms are not built on a different range with a
coincidentally-populated first bin — they are on the identical fixed grid
every other histogram in the file (and every one of our own CMS
histograms) uses.**

**The passing histograms have genuine content in the true first bin**:
for all 52, `first_nonempty_bin_index_1based == 1` (confirmed directly,
not inferred) — real mass entries in the 0–10 GeV bin of the shared fixed
grid, not an artifact of a shifted range.

**Does the pattern correlate with category, as the supervisor suggested?
Counts, not an assertion:**

| Object-content category | Pass (bin1>0) | Fail (bin1==0) | Total | Pass rate |
|---|---:|---:|---:|---:|
| lepton-only | 28 | 59 | 87 | **32.2%** |
| lepton+jet | 23 | 414 | 437 | 5.3% |
| b-jet-containing | 1 | 222 | 223 | 0.4% |
| jet-only | 0 | 76 | 76 | **0.0%** |

**This is the opposite correlation from the one proposed.** Jet-only
categories have a 0% pass rate (0 of 76) and b-jet-containing categories
pass almost never (1 of 223, 0.4%) — if anything, pure jet/b-jet
categories are the ones *most* likely to be rejected in this file, not
the ones that pass. Lepton-only categories pass far more often (32.2%)
than any other group. Sample names confirm this is not a labeling
artifact: passing histograms are things like
`ROI_mass_e0j0_cat_1ex_0mx_1jx_..._width_10.0` (electron+jet),
`ROI_mass_e0m0_cat_1ex_1mx_..._width_10.0` (electron+muon) — lepton or
lepton+jet combinations, not the pure-jet/b-jet ones the hypothesis named.

**Which reading does the evidence support?** The technical lead's. Not
because the supervisor's specific mechanism (jet/b-jet categories being
exempt from trimming) is correct — the category data directly contradicts
it — but because the *general* code-level claim holds up exactly: nothing
removes leading bins for anyone, ever; a histogram passes precisely when
`_find_rightmost_highest_peak` happens to land the detected peak inside
the first 10 GeV bin for that specific category's mass distribution, and
fails otherwise. Whether the peak lands there is a property of the
underlying physics/reconstruction for that specific final state (e.g.
opposite-flavor or single-lepton categories are never subject to the
`z_peak_cutoff` dilepton floor — `_dilepton_flavor`,
`services/pipelines/post_processing_pipeline.py:34-45`, only applies to a
same-flavor `ee`/`mumu` pair — so nothing structurally prevents their peak
from sitting near zero), not a bug in the pipeline that treats jet/b-jet
categories specially. **UNVERIFIED**: this explains *why a peak near zero
is possible* for lepton categories; it does not explain in detail why
this *specific* file's lepton categories happen to peak there 32.2%/5.3%
of the time while jet/b-jet ones essentially never do — that would need
the underlying (pre-histogram) mass arrays for this file, which are
outside this task's read-only, histogram-level scope.

## Part 2 — what the code can and cannot produce

**The "different grid" premise is empirically false** (Part 1: one grid,
823/823 histograms) — so the question "what produces that different
grid" does not arise; there is no different grid to explain.

**Checked for completeness anyway, per the task's own instruction**:
compared `services/pipelines/histograms_pipeline.py` and
`services/pipelines/post_processing_pipeline.py` between this fork's
`HEAD` (`8767f42`, before this round's own commits) and
`upstream/master` (`fe5a560`, fetched read-only, never pushed to). A
line-level diff restricted to binning/trim/peak-removal keywords
(`bin_width`, `FIXED_MASS`, `trim`, `peak`, `nbins`, `crop`) across both
files returns **zero differences** — the logic this round depends on is
byte-identical between the two. Every config file in the repository
(`config.yaml` and all ten `config.cms_*.yaml`/other variants) sets
`bin_width_gev: 10.0` and `peak_detection_bin_width_gev: 10.0` uniformly
— no config in this repository produces a different bin width, and
`FIXED_MASS_MIN_GEV`/`FIXED_MASS_MAX_GEV` are hardcoded constants
(`histograms_pipeline.py:22-23`), not config-driven at all, so no config
change could produce a different range either.

**No code path removes leading empty bins** — unchanged from Round 1's
Part 4 (quoted there with `file:line`): `trim_empty_tail` only changes
the axis *display* range (confirmed identical to real ROOT's own
behavior, Round 1 Part 2); `_apply_peak_removal_to_histogram` zeroes bin
*content* in place without changing `nbins`. Both findings hold for
upstream master too — this file has no differences from our fork in the
relevant regions.

**Conclusion: this is not "an older code version, a different config, a
different bin width, or a separate creation function."** The ATLAS
reference file's 52 passing histograms are produced by exactly the same
code, the same grid, and the same thresholds as its 771 failing ones and
as our own 316 CMS histograms — the only thing that differs is where each
category's own detected peak happens to fall.

## Part 3 — CMS alignment audit

Item-by-item, our standalone CMS post-processing/histogram code (never
a live import of the shared pipeline's ROOT-dependent modules, for the
environment reasons Round 1 documented) versus the shared pipeline itself:

| Item | CMS side (file:line) | Shared pipeline (file:line) | Same / different |
|---|---|---|---|
| z-peak cutoff value | `115.0`, `studies/cms_coverage/cluster/merge_and_count.py:64` (cites `config.yaml:155`) | `115.0`, `config.yaml:155` | **Same value** — and the CMS side calls the real `_apply_z_peak_cut` function directly (`merge_and_count.py:48-51` import, `:170` call) rather than reimplementing it |
| max-mass cutoff value | `10000.0`, `merge_and_count.py:65` (cites `config.yaml:156`) | `10000.0`, `config.yaml:156` | **Same value**, same real function usage pattern |
| peak removal | calls the real `_find_rightmost_highest_peak` unmodified, `merge_and_count.py:49` (import), `:174` (call) | `services/pipelines/post_processing_pipeline.py:324-352` | **Identical — the literal same function**, not a reimplementation |
| first-empty-bin outlier split | calls the real `_split_by_first_empty_bin` unmodified, `merge_and_count.py:50` (import), `:178` (call) | `post_processing_pipeline.py:355-388` | **Identical — the literal same function** |
| `min_events_per_fs` | `100`, `merge_and_count.py:66` (cites `config.yaml:142`) | `100`, `config.yaml:142` | **Same value**; CMS calls the real `prune_final_states_below_min_events` (`services/storage/sqlite_shards.py`) unmodified too |
| histogram grid | `FIXED_MASS_MIN_GEV=0.0`/`MAX_GEV=10000.0`, `BIN_WIDTH_GEV=10.0` — copied verbatim (not live-imported, documented reason: no PyROOT in the cluster env) into `studies/m0m1j0_cms/histograms.py:105-108`, citing `histograms_pipeline.py:22-23` as the source | `FIXED_MASS_MIN_GEV=0.0`/`MAX_GEV=10000.0`, `histograms_pipeline.py:22-23`; `bin_width_gev: 10.0`, `config.yaml:166` | **Same values**, confirmed independently in Round 1 Part 2 by a real-ROOT cross-check, not just a code read |
| naming — BumpNet category name | `_convert_to_bumpnet_name`, copied verbatim into `studies/m0m1j0_cms/histograms.py:125-140`, citing `histograms_pipeline.py:419-453` | `histograms_pipeline.py:419-453` | **Identical function**, same output strings |
| naming — ROI_ key suffix | `f"ROI_{name}_width_{int(BIN_WIDTH_GEV)}"` — `int()` truncates, giving **`_width_10`** (`studies/cms_coverage/deliver/build_bumpnet_root.py:160,175,285`; same pattern in `studies/m0m1j0_cms/cluster/merge_full_v2.py:240`) | `f"ROI_{signature}_width_{bin_width}"` where `bin_width` is the raw config float — giving **`_width_10.0`** (`histograms_pipeline.py:343`, confirmed directly: every one of the ATLAS reference file's 823 real histogram names ends `_width_10.0`) | **Different** — a real, previously-unremarked naming difference. Not shown by this investigation to cause rejection (the ATLAS file's own partial-rejection pattern shows the SAME `_width_10.0` names both passing and failing), but a genuine alignment gap worth closing regardless |
| minimum-bins requirement | our delivery produced two separate files, `>30` bins and `>25` bins (`studies/cms_coverage/deliver/build_bumpnet_root.py`, `BINS_THRESHOLD_A=30`/`BINS_THRESHOLD_B=25`) | BumpNet itself enforces `>=25` (supervisor's report); nothing in the shared pipeline code enforces a bins minimum at all — that check lives in BumpNet's own loader, not in `histograms_pipeline.py`/`post_processing_pipeline.py` | **Not applicable to the shared pipeline** — this is a BumpNet-side rule, not a pipeline post-processing step; our `>25` file already matches BumpNet's own stated floor, our `>30` file is stricter than required |

**What aligning the one real difference (naming) would mean**: changing
`int(BIN_WIDTH_GEV)` to just `BIN_WIDTH_GEV` (no truncation) in the three
CMS-side call sites above would make our `_width_10` become `_width_10.0`,
matching the shared pipeline's own convention exactly. This is a
one-line-per-call-site change in **new/study code only**
(`studies/cms_coverage/deliver/`, `studies/m0m1j0_cms/cluster/`) — it does
not touch `services/`, `config.yaml`, or anything shared, and is not
applied here (out of scope for this task; see `FIX_PROPOSAL.md`).
