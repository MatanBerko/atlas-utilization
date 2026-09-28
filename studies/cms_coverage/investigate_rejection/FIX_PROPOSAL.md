# Fix proposal for the BumpNet bin-1-empty rejection

**This is a proposal for discussion, not a change.** Nothing under
`services/`, `domain/`, `orchestration/`, `config.yaml`, or any other
shared file has been modified. The candidate diff below is quoted text in
this document, not applied to the working tree — confirmed by `git
status` at the end of this task.

## Recap of what Round 1 + Round 2 established

- BumpNet's loader hard-drops any histogram whose bin 1 is `0.0`
  (supervisor, stated fact — not code we have access to).
- The shared pipeline always builds every histogram on the fixed
  `FIXED_MASS_MIN_GEV..FIXED_MASS_MAX_GEV` (0–10,000 GeV) grid, and
  post-processing always removes everything below the detected peak
  before the histogram is filled (`REJECTION_REPORT.md` Part 4 / Round 2
  Part 2, with `file:line` quotes). A histogram's bin 1 is populated
  **only when that category's own peak happens to fall in the first 10
  GeV** — true for 52 of 823 histograms in the real ATLAS reference file
  checked in Round 2, and true for 0 of 316 in our CMS file.
- Nothing in this code path is CMS-specific or ATLAS-specific. The same
  code produces both outcomes, for both experiments.

## Option A — crop leading empty bins in the shared pipeline (producer-side fix)

**Where**: `services/pipelines/histograms_pipeline.py`. `trim_empty_tail`
(lines 26–41) already finds the last filled bin and adjusts the display
range; a new sibling function, `crop_leading_empty_bins`, would find the
**first** filled bin and build a genuinely smaller `TH1F` spanning
`[first_filled_low_edge, last_bin_high_edge]` — exactly the same
construction this task's own `studies/cms_coverage/deliver/crop_bumpnet_root.py`
already implements and verified (316/316 and 340/340 histograms,
bin-for-bin identical content, non-empty bin 1 confirmed by reading the
written files back), just written for real `ROOT.TH1F` objects instead of
via `uproot`.

This function would need to be called everywhere `trim_empty_tail`
currently is — **8 call sites** across
`_create_histograms_from_sqlite` (4 sites, lines 253–255, 265–267,
283–285, 295–297), `_process_im_arrays_bumpnet` (2 sites, lines 482–484,
501–503), and `_process_im_arrays_standard` (2 sites, lines 589–591,
605–607) — because a ROOT histogram cannot be resized in place; each call
site's `for hist in hists: trim_empty_tail(hist)` would need to become a
reassignment (`hists = [crop_leading_empty_bins(h) for h in hists]`),
since the cropped result is a **new** object, not a mutation of the old
one.

**Candidate diff** (illustrative — shows the new function and one of the
eight call sites; the other seven follow the identical pattern):

```diff
--- a/services/pipelines/histograms_pipeline.py
+++ b/services/pipelines/histograms_pipeline.py
@@ -23,6 +23,33 @@ FIXED_MASS_MIN_GEV = 0.0
 FIXED_MASS_MAX_GEV = 10000.0
 
 
+def crop_leading_empty_bins(hist: ROOT.TH1F) -> ROOT.TH1F:
+    """Return a NEW, genuinely smaller TH1F spanning the first filled bin
+    through the last filled bin, inclusive -- unlike trim_empty_tail,
+    this removes bin content, not just the display range, because
+    BumpNet's own loader (load_ATLAS) hard-drops any histogram whose bin
+    1 is zero (project convention as of 2026-09-28; not itself part of
+    this shared pipeline). A histogram with no filled bins at all is
+    returned unchanged (nothing to crop, and BumpNet would reject it
+    either way for being empty).
+    """
+    nbins = hist.GetNbinsX()
+    first_filled = next((b for b in range(1, nbins + 1) if hist.GetBinContent(b) > 0), None)
+    last_filled = next((b for b in range(nbins, 0, -1) if hist.GetBinContent(b) > 0), None)
+    if first_filled is None:
+        return hist
+    new_nbins = last_filled - first_filled + 1
+    xlow = hist.GetXaxis().GetBinLowEdge(first_filled)
+    xhigh = hist.GetXaxis().GetBinUpEdge(last_filled)
+    cropped = ROOT.TH1F(hist.GetName(), hist.GetTitle(), new_nbins, xlow, xhigh)
+    for i, b in enumerate(range(first_filled, last_filled + 1), start=1):
+        cropped.SetBinContent(i, hist.GetBinContent(b))
+        cropped.SetBinError(i, hist.GetBinError(b))
+    return cropped
+
+
 def trim_empty_tail(hist: ROOT.TH1F) -> None:
     """Trim trailing empty bins by adjusting the display range.
 
@@ -249,8 +276,7 @@ def _create_histograms_from_sqlite(
                     group_sigs, db_paths, bumpnet_name, bin_widths_gev, logger,
                 )
                 if hists:
                     if trim_before_write:
-                        for hist in hists:
-                            trim_empty_tail(hist)
+                        hists = [crop_leading_empty_bins(h) for h in hists]
                     _write_hists_to_shared_file(hists, root_filepath, logger)
                     hist_count += len(hists)
```

**What this changes for ATLAS outputs**: every future ATLAS histogram
would become variable-length (Round 2's own reference file's *failing*
771 would range roughly as wide as our own cropped CMS files did, 26–893
bins observed there vs. our 26–217) instead of the uniform 1000-bin grid
every histogram shares today. The 52 already-passing ones would also
change shape slightly (their trailing empty region would now be removed
too, not just display-hidden) — same bin-1-onward content, fewer total
bins.

**What this risks — stated plainly, per this task's own instruction**:
today, **every histogram in an output file shares one identical grid**
(`n_bins=1000`, `[0, 10000]` — confirmed for both our own 316/340 CMS
histograms and Round 2's 823 ATLAS ones). This is exactly the kind of
invariant a batch/matrix loader stacking histograms into a single tensor
for a neural network would rely on. We do **not** know whether BumpNet's
own training code (or any other consumer of these files besides
`load_ATLAS`'s rejection check) assumes this. If it does, Option A trades
one rejection for a different failure downstream, one file at a time
instead of instantly and can be far harder to notice.

**How to test**: (1) a regression identical in kind to what
`crop_bumpnet_root.py` already ran for our own delivery — re-crop a
committed ATLAS output (e.g. a copy of the 52-passing histograms from
Round 2's reference file, read-only, never copied into this repo per this
task's own restriction — this would need to be done on `marybo`'s own
account or with her explicit copy, not by us) and confirm bin-for-bin
identity in the surviving window, non-empty bin 1, for all of them; (2)
confirmly separately, with BumpNet's own team, whether its loader or any
training code assumes a fixed histogram length — this is not testable
from this repo alone.

## Option B — change BumpNet's loader instead (consumer-side fix)

Have `load_ATLAS` find the first non-empty bin itself at load time and
treat *that* as the effective bin 1 (i.e. do exactly what
`crop_leading_empty_bins` above does, but in BumpNet's own code, on an
in-memory copy, never touching the stored ROOT file). 

**What it fixes**: the rejection, without changing anything this repo
produces, delivers, or has already delivered — the two existing ROOT
files on the cluster would not need to change at all, and neither would
any past or future ATLAS output.

**What it risks**: none that touches this repo or its outputs. The
risk is entirely on BumpNet's side and is **hers to judge, not ours**:
whether her training code can accept a per-histogram crop happening at
load time rather than a fixed shape read straight off disk (if BumpNet
already re-bins/normalizes every histogram to a canonical shape before
training — plausible for a neural network, but **UNVERIFIED**, we do not
have BumpNet's code — this fix is nearly free; if it feeds raw bin
arrays of whatever length the file provides directly into a fixed-size
input layer, this fix requires that layer to already tolerate variable
input length, or to do its own padding/re-binning, which may or may not
already exist).

**How to test**: entirely on her side — a regression showing BumpNet now
accepts the same 316 CMS histograms (uncropped file) and the previously-
failing 771 of the 823 ATLAS ones, with unchanged training/inference
behavior for the 52 that already passed. Not testable from this repo.

## Option C — a cooperative, lower-risk middle ground

Keep the **producer's** output exactly as it is today (one shared fixed
grid, `trim_empty_tail`'s existing display-range trim, nothing else
changed) — but have it **also** record, per histogram, the already-computed
first/last filled bin as small companion metadata in the same ROOT file
(e.g. a `TParameter<Int_t>` or a tiny sibling `TH1`/`TNamed` per
histogram, or a single small `TTree`/`TMap` for the whole file). BumpNet's
loader would then read that metadata and crop on load — the same
computation Option A would do, but done **once, by the producer, and
handed to the consumer**, rather than either side guessing or
recomputing it, and **without changing the shape of anything already on
disk**.

**What it fixes**: the rejection, for any consumer willing to read the
extra metadata, while leaving the existing fixed-grid histograms exactly
as they are for any consumer that doesn't (e.g. a batch loader that wants
the uniform grid). Genuinely additive, not a replacement.

**What it risks**: BumpNet's loader still needs a code change to read and
act on the new metadata (smaller than Option B alone, but not zero); the
shared pipeline needs a small, additive change (new metadata written
alongside each histogram — not a change to any existing field, class, or
naming convention) — still touches `services/`, so still a shared-code
decision, just a much narrower one than Option A's full crop-in-place.

**How to test**: write the metadata for a known histogram, confirm the
existing bin content/shape is completely unchanged (a simple `diff` of
the histogram's own bytes before/after adding the metadata), then confirm
BumpNet's loader can find and use the new metadata on a real file.

## Recommendation

**Prefer Option B, or Option C if BumpNet's loader cannot easily be
changed on its own** — over Option A. Reasoning: Option A changes the
**producer**, whose output today has exactly one property every consumer
can currently rely on (one shared fixed grid) — and this pipeline has no
visibility into how many consumers besides BumpNet depend on that
property; changing it is a one-way door that affects every future ATLAS
and CMS run, not just this one rejection. Options B and C both leave the
producer's contract with every *other* consumer untouched, and put the
decision and the risk in the hands of the team (BumpNet's own) that can
actually verify whether it's safe on their side.

**What is genuinely this project's decision versus the supervisor's**:
whether to implement Option A (a shared-pipeline change) is this
project's call, made jointly with whoever else depends on the shared
pipeline's fixed-grid output — not something to decide unilaterally here.
Whether Option B is feasible — whether BumpNet's own code can tolerate a
load-time crop — is **entirely the supervisor's/BumpNet team's own
determination**; this document states the trade-off, not the answer.
Option C needs agreement from both sides (a shared-pipeline change,
however narrow, plus a BumpNet-side loader change).

**Separately, and independently of all three options above**: Round 2's
Part 3 alignment audit found one genuine, unrelated naming difference —
our CMS delivery scripts write `..._width_10` (`int()`-truncated) where
the shared pipeline itself writes `..._width_10.0` (the raw config
float). This did not appear to cause rejection in Round 2's evidence (the
ATLAS file's own `_width_10.0` names both pass and fail), but it is a
real alignment gap worth closing on its own, in the same new/study-code
files already identified (`studies/cms_coverage/deliver/build_bumpnet_root.py`,
`studies/m0m1j0_cms/cluster/merge_full_v2.py`) — not proposed as a patch
here since it is unrelated to the rejection this task investigates, but
flagged so it isn't lost.
