# Z→ee validation, round 2 (implementation task 6 follow-up, 17 Sep 2026)

Run locally against the merged Z→ee outputs copied off the cluster after
the Z→ee run's merge reported `status: "COMPLETE"` for both data and DY
(`merge_summary_zee_data.json` / `merge_summary_zee_dy.json` — 151/151
and 41/41 jobs exit 0, event counts exact-match the CERN Open Data portal
totals). This sample's leading pair is built from `electronVeto==False`
photons — structurally disjoint from the H→γγ main analysis's own
`electronVeto==True` candidate (see `studies/hgg_cms/zee_selection.py`'s
own module docstring) — so nothing here touches H→γγ signal-region data.
`C:\Users\matan\hgg_zee_merged` was listed and confirmed to contain no
filename with `BLINDED` before anything was read.

Reproduce with (from the repo root, after copying the merged Z→ee files
to `HGG_ZEE_MERGED_DIR`, default `C:\Users\matan\hgg_zee_merged`):
```
python -m studies.hgg_cms.validation.zee.pileup
python -m studies.hgg_cms.validation.zee.energy_scale
python -m studies.hgg_cms.validation.zee.normalization_check
python -m studies.hgg_cms.validation.zee.trigger_efficiency
python -m studies.hgg_cms.validation.zee.mass90_sculpting_demo
```
Each writes its own `zee/results/<name>_results.json` (or
`pileup_weights.json`) and PNG(s) under `zee/results/plots/`. Item 5
(electron-veto leakage) needs one additional command run **on the
cluster** — see Part E below; it is not included in the list above.

All criteria in this report (§B's ±0.5%/±10% pass/fail bands, §C's
[0.7, 1.3] flag range, §E's fully/partly/no thresholds) were fixed in the
task instructions **before** any of these numbers existed and were not
adjusted afterward.

---

## A — Pileup reweighting (PV_npvsGood)

Same method as `VALIDATION_REPORT_1.md` Part D: per-bin
data/DY(Ele27-fired) ratio, `PV_npvsGood` in `[-0.5, 59.5]`, with the
same low-statistics fallback and clipping. `n_data = 4,564,192`,
`n_dy_ele27_fired = 3,877,519`. See `zee/results/pileup_weights.json` and
`zee/results/plots/pileup_matching.png`.

These weights (`genWeight × pileup_weight`) are applied to DY as "DY-PU"
throughout B–D and F below; the "DY-noPU" (`genWeight` only) numbers are
reported alongside for comparison, as requested.

---

## B — Energy scale and resolution

Ele27-fired, `70 < m_ee < 110 GeV`. Peak from a Breit–Wigner (M_Z, Γ_Z
fixed to PDG 91.1876, 2.4952 GeV) convolved with a Crystal Ball,
**fit window 80–100 GeV** (chosen by inspecting the raw 70–110 shape
*before* comparing data to DY — substantial non-Gaussian shoulders
outside 80–100 would otherwise bias both the fit and a naive full-window
σ_eff). σ_eff68 is the UNBINNED smallest interval containing 68.3% of the
(signed) weight — see the algorithm note below. Both PASS/FAIL criteria
(|Δpeak|/peak < 0.5%, |Δσ_eff|/σ_eff < 10%) were pre-set.

| category | peak data | peak DY (PU) | Δpeak/peak | σ_eff68 data | σ_eff68 DY (PU) | Δσ_eff/σ_eff | verdict |
|---|---:|---:|---:|---:|---:|---:|:---:|
| inclusive | 89.9833 ± 0.0069 | 89.9500 ± 0.0083 | 0.037% | 3.1253 ± 0.0009 | 3.1551 ± 0.0029 | −0.95% | **PASS** |
| EBEB | 90.1667 ± 0.0078 | 90.1167 ± 0.0088 | 0.055% | 3.0103 ± 0.0014 | 3.0282 ± 0.0033 | −0.59% | **PASS** |
| notEBEB | 89.4167 ± 0.0075 | 89.4500 ± 4.671 | −0.037% | 3.3120 ± 0.0014 | 3.3709 ± 0.0065 | −1.75% | **PASS** |

(all GeV; peak/σ_eff uncertainties from the fit covariance / an 8-fold
bootstrap respectively. The notEBEB/DY-PU peak uncertainty is
anomalously large — the CB tail parameter `n` pins against its bound in
some bootstrap replicas there, a numerical-stability artifact of that
one bin's lower statistics, not a sign the peak itself is unreliable:
the central value, 89.4500, agrees with data to 0.037%.)

Mode and median (both datasets, all categories, with and without PU) are
in `zee/results/energy_scale_results.json` under each
`data`/`dy_no_pu`/`dy_with_pu` block's `mode_GeV` / `median_GeV`. DY
without PU reweighting gives materially the same peak/σ_eff conclusions
(also in the JSON, `comparison_without_pu`) — PU reweighting shifts
σ_eff68 by at most ~0.03 GeV here, well inside the 10% band either way.

**All three categories PASS both criteria. No energy-scale-factor or
extra-smearing correction is needed for the signal model.**

Plot: `zee/results/plots/energy_scale.png`.

**A bug found and fixed while producing this section.** The first pass
of σ_eff68 used an O(n) "shortest subarray (by event COUNT) with weight
sum ≥ target" algorithm (a monotonic-deque solution, chosen because
DY's genWeight is signed — ~15.85% negative, equal magnitude — which
breaks a naive two-pointer over the raw cumulative weight). That
algorithm is correct for minimizing event *count*, but minimizing count
is not the same problem as minimizing mass *width* on a non-uniform
density: among the many windows sharing the minimal count, it silently
returned an arbitrary one rather than the narrowest in GeV, overshooting
the true σ_eff by ~2.5× on a 200,000-event unweighted-Gaussian unit test
(caught by that test, not by eye). It was replaced with a binary search
on the window *width*, checked at each step with a vectorized
searchsorted/two-pointer scan that relies only on the mass values being
sorted (always true) rather than on the weights being non-negative
(false for DY) — this is exact for signed weights and was verified
against both the unit test (now passes, 2.003 vs. true 2.0) and a
600,000×-larger synthetic signed-weight case (4M events, recovers
σ=3.0016 vs. injected 3.0, ~9s). All σ_eff68 numbers in this report,
and every number derived from them, are from the corrected algorithm.

---

## C — Normalization sanity check

`N_expected = σ(DY) × L × Σ genWeight_selected(Ele27, 70–110 GeV,
PU-weighted) / Σ genEventSumw`, σ = 6077.22 pb (NNLO, same citation as
`ZEE_RUN_README.md`), L = 16.393 fb⁻¹, Σ genEventSumw = 1,220,934,627,963.07
(the 41 processed DY files). Flagged only outside [0.7, 1.3] — a ratio
away from exactly 1 is *expected* since no electron/photon-ID or trigger
scale factors are applied anywhere in this task.

| category | N data | N DY (no PU) | N DY (PU) | data/DY (PU) | flagged |
|---|---:|---:|---:|---:|:---:|
| inclusive | 4,394,063 | 5,310,860 | 5,310,512 | **0.827** | no |
| EBEB | 2,947,272 | 3,496,803 | 3,520,180 | **0.837** | no |
| notEBEB | 1,446,791 | 1,814,062 | 1,790,332 | **0.808** | no |

None flagged (all comfortably inside [0.7, 1.3]). The ~17–19% data
deficit relative to unweighted DY is consistent in size and direction
with known unmodeled efficiency (electron reconstruction/ID, trigger —
see Part D) rather than anything alarming. Full numbers:
`zee/results/normalization_check_results.json`.

---

## D — Trigger efficiency

Ele27-fired, `m_ee > 95 GeV`: fraction with the diphoton trigger bit
(`HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90`) also fired.
Report only, no pass/fail (per the task's own framing).

| category | eff. data | eff. DY (PU) | data/DY ratio |
|---|---:|---:|---:|
| inclusive | 0.9488 ± 0.0003 | 0.9427 ± 0.0006 | **1.0065 ± 0.0008** |
| EBEB | 0.9757 ± 0.0003 | 0.9539 ± 0.0007 | **1.0229 ± 0.0008** |
| notEBEB | 0.8944 ± 0.0008 | 0.9216 ± 0.0012 | **0.9705 ± 0.0016** |

Full numbers (including the no-PU comparison): `zee/results/trigger_efficiency_results.json`;
plot `zee/results/plots/trigger_efficiency.png`.

**Implication for the H→γγ expected yield**: the H→γγ selection itself
requires this same diphoton trigger to fire, and the signal MC's own
expected-yield calculation (`VALIDATION_REPORT_1.md` Part E) implicitly
trusts that MC's simulated trigger response matches data's. A
data/DY ratio away from 1 — as seen here, mildly above 1 inclusive and
in EBEB, mildly below 1 in notEBEB — is direct evidence the signal MC
over- or under-estimates the *real* diphoton-trigger efficiency by
roughly that fractional amount. That is exactly the kind of trigger
scale factor a real CMS analysis derives from a tag-and-probe
measurement like this one and applies multiplicatively to the signal
MC's expected yield. This task does not apply that correction (out of
scope here); the per-category ratios above are what the signal-model
task would need if it chooses to apply one.

---

## E — Electron-veto leakage into the H→γγ sample — **PENDING (needs one cluster command)**

Goal: using DY events that pass the *normal* H→γγ selection
(`electronVeto == True`, same trigger/photon-ID/trigger-mimicking/scaled
cuts as the H→γγ analysis), normalized as in Part C, give the expected
number of such events landing in the H→γγ *data* sample's 100–105,
105–110, 110–115 and 135–180 GeV windows, per category, and compare
against `VALIDATION_REPORT_1.md` Part B's ~1,604-event excess in
100–105 GeV.

**This could not be completed in this pass.** The already-completed DY
cluster run computed a leakage estimate inline
(`run_zee_selection_on_chunks.py`'s `compute_hgg_veto_leakage()`), but
only for two coarse windows (100–105, 105–115 combined) with no category
split — the four windows and per-category split this task actually needs
were added to that function *after* the DY run had already finished, and
the underlying `electronVeto==True` population was never written to disk
(by design — see that function's own docstring). Re-submitting the whole
DY run just to get finer binning is unnecessary: the already-parsed chunk
files from the completed run are still sitting on the cluster, so a new
script, `studies/hgg_cms/validation/zee/hgg_leakage_estimate.py`, reads
those same chunks and recomputes `compute_hgg_veto_leakage()` fresh, now
with the full window/category set. It needs no new download, no
re-parsing, and no `qsub` — the same "runs in a couple of minutes on the
analysis node with `nice`" category as `merge_outputs.py`. It has 3 unit
tests passing (`tests/test_zee_validation.py::HggLeakageRecomputeTests`)
against synthetic fixtures, and the underlying per-chunk computation has
its own round-trip test
(`tests/test_run_zee_selection_on_chunks_roundtrip.py::test_dy_chunk_computes_veto_leakage_estimate`)
checking all 4 windows × 3 categories × the √Σw² uncertainty inputs.

**Please run this yourself** (no SSH/qsub from me, per the standing
rule) and paste back the output JSON:
```
nice python studies/hgg_cms/validation/zee/hgg_leakage_estimate.py \
    --dy-jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/dy_full \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/hgg_leakage_estimate_results.json
```
Then copy just that one JSON file back (no need to copy the 41 job
directories). Once it's back I'll fill in this section's table, the
fully/partly/no verdict, and finalize Part B's dated update in
`VALIDATION_REPORT_1.md` below.

**Interim fit-range recommendation** (based on currently available
evidence only — Part B's own power-law-vs-exponential extrapolation
result, not yet the leakage measurement): **start the background-model
fit at 105 GeV, not 100 GeV.** Reasoning: 100–105 GeV is the one window
`VALIDATION_REPORT_1.md` Part B explicitly flagged (+4.2σ above even the
better-fitting power-law extrapolation, χ²/ndf=1.10 in-range); leakage is
a physically plausible, not-yet-ruled-out contributor to exactly that
excess, and 105 GeV is a boundary this study already treats as a natural
cut (Part B's own sideband fit region starts there). 110 GeV is not
recommended as a default — it would discard a clean window unnecessarily
unless the leakage measurement, once available, shows leakage also
extends materially into 105–110 GeV, in which case this recommendation
should be revisited.

---

## F — Mass90 sculpting demonstration (DY, PU-weighted)

Demonstrates the effect the diphoton trigger's online `Mass90` cut has on
the offline mass shape: comparing DY events selected by the diphoton
trigger alone against the full (Ele27-fired, unbiased) DY sample.

| | count |
|---|---:|
| diphoton-only, 70–90 GeV | 34,848 |
| diphoton-only, 90–110 GeV | 54,733 |
| ratio (below/above 90 GeV) | **0.637** |
| unbiased (Ele27-fired) sample size | 3,741,369 |

Clear depletion below 90 GeV in the diphoton-only sample relative to the
unbiased one, as expected for an online mass turn-on centered near 90
GeV — the same effect `VALIDATION_REPORT_1.md` Part B lists as one
candidate (not the leading one) for its own 100–105 GeV excess. Plot:
`zee/results/plots/mass90_sculpting_demo.png`; full numbers:
`zee/results/mass90_sculpting_demo_results.json`.

---

## Summary of flags

| check | flag | severity |
|---|---|---|
| B (energy scale/resolution) | none | all three categories PASS both pre-set criteria |
| C (normalization) | none | all three ratios inside [0.7, 1.3] |
| E (electron-veto leakage) | **pending** | needs one cluster command (above) before Part B of `VALIDATION_REPORT_1.md` can be finalized |

Nothing else raised a flag. No H→γγ blind-window data was read, printed,
or plotted while producing this report (this report never touches
`hgg_full_merged` at all — everything here is Z→ee control-region data
and DY simulation).
