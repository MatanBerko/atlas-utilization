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
(electron-veto leakage) needed one additional command run **on the
cluster**; that command has now been run — see Part E below — and its
output is committed at
`zee/results/hgg_leakage_estimate_results.json`.

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

## E — Electron-veto leakage into the H→γγ sample — **COMPLETE**

Goal: using DY events that pass the *normal* H→γγ selection
(`electronVeto == True`, same trigger/photon-ID/trigger-mimicking/scaled
cuts as the H→γγ analysis), normalized as in Part C, give the expected
number of such events landing in the H→γγ *data* sample's 100–105,
105–110, 110–115 and 135–180 GeV windows, per category, and compare
against `VALIDATION_REPORT_1.md` Part B's ~1,604-event excess in
100–105 GeV.

### Update — 17 Sep 2026: cluster command run, results below

`studies/hgg_cms/validation/zee/hgg_leakage_estimate.py` was run over all
41 DY jobs (no missing chunks, no missing sumw — `missing_chunks_jobs`
and `missing_sumw_jobs` both empty in the output JSON). Output copied
back to `studies/hgg_cms/validation/zee/results/hgg_leakage_estimate_results.json`.

**Expected leakage (N_expected ± statistical uncertainty):**

| window | inclusive | EBEB | notEBEB |
|---|---:|---:|---:|
| 100–105 GeV | 1,609.8 ± 71.5 | 432.8 ± 39.1 | 1,176.9 ± 59.9 |
| 105–110 GeV | 933.7 ± 55.3 | 274.1 ± 30.1 | 659.6 ± 46.4 |
| 110–115 GeV | 568.9 ± 42.8 | 154.6 ± 22.3 | 414.3 ± 36.6 |
| 135–180 GeV | 768.8 ± 51.4 | 220.5 ± 27.4 | 548.3 ± 43.5 |

The script's own comparison block reports the 100–105 GeV inclusive
leakage (1,609.8 ± 71.5) against Part B's ~1,604-event excess and labels
this "fully" explained (ratio 1.004). **That verdict label is too strong
and is not adopted as-is below** — see the two caveats immediately
following.

**Verdict: consistent with electron-veto leakage being the cause of the
100–105 GeV excess — not "fully explained."** The numerical match is
close, but two things keep this from being an independent confirmation:

1. **The comparison isn't independent of itself.** Leakage doesn't only
   land in 100–105 GeV — it also populates 105–110, 110–115 and 135–180
   GeV, which is exactly the sideband region Part B's own extrapolation
   was fit to (105–115 ∪ 135–180). Summing the three sideband windows
   above: 933.7 + 568.9 + 768.8 ≈ **2,271 events** of leakage sitting
   inside the very fit region used to predict the "expected" 100–105
   count that the excess is measured against. If leakage is real, it
   biases that extrapolation's baseline upward too, so the 1,604-event
   excess and the 1,609.8-event leakage estimate are not two independent
   numbers being compared — the same physical effect partially
   contaminates both sides of the comparison. This doesn't invalidate
   the leakage explanation; it just means the closeness of the match
   isn't as strong a confirmation as it looks.
2. **The DY-based prediction carries systematic uncertainty well beyond
   its quoted statistical error, and that systematic is not quantified
   here.** Two concrete sources, both already on record in this report:
   - Part C's Z→ee data/DY normalization ratio is **0.83** (inclusive)
     *without* any electron-ID or trigger scale factors applied — i.e.
     the DY simulation used for this leakage estimate is known to be off
     from data by ~17% in the *opposite* direction (DY over-predicts
     Z→ee) in the region it's best measured. Applying that same
     normalization to the leakage estimate is an extrapolation of a
     known ~15–20% mismodeling into a kinematic region (real electrons
     faking `electronVeto==True`) that has no direct data control here.
   - The `electronVeto` inefficiency for **real electrons** (the actual
     physical quantity driving this leakage) is not validated against
     data anywhere in this study — everything above is DY simulation's
     own veto response, taken at face value.

   Combining these, a **rough systematic uncertainty of order 20–50% on
   the leakage normalization** (clearly a rough estimate, not a
   measurement — no dedicated systematic study was performed) is a
   reasonable working assumption. At the low end (+20%) the leakage
   estimate would still cover most of the excess; at the high end
   (−50%) it would cover roughly half. Either way it remains a
   physically real and plausible contributor of the right order of
   magnitude — just not a number precise enough to claim the excess is
   *fully* accounted for.

### Estimated leakage shape in 115–135 GeV (from an exponential fit — an estimate, not a measurement)

The four measured windows (100–105, 105–110, 110–115, 135–180 GeV) were
fit as event density (N_expected / window width) to a simple exponential
in mass, `density(m) = A·exp(−k·m)`, by weighted least squares in
log-space (weights = 1/σ_ln², propagating each window's quoted
statistical uncertainty). This is a 4-point fit to 2 parameters (2 dof)
so it should be read as an order-of-magnitude estimate, not a precision
result — and the fit is visibly imperfect (χ²/ndf well above 1 in all
three categories, largely because the 135–180 GeV bin is 9× wider than
the other three and a single exponential's curvature isn't exactly
matched by that bin's width-averaged density).

Integrating the fitted exponential over 115–135 GeV:

| category | estimated N_expected, 115–135 GeV |
|---|---:|
| inclusive | ≈ 1,790 ± 60 (fit-propagated) |
| EBEB | ≈ 500 ± 30 (fit-propagated) |
| notEBEB | ≈ 1,290 ± 50 (fit-propagated) |

(uncertainties from propagating the fit's parameter covariance only —
they do not include the systematic on the overall DY normalization
discussed above, which dominates). Take this as a rough estimate of the
scale and shape of leakage under the blinded peak, not a precise
prediction.

**Implication for the background-model task**: this leakage component is
smooth and non-resonant — it does not produce a peak or bump, so a smooth
background function fit across the blinded region will absorb most of
it, the same way it absorbs the rest of the QCD/γ+jet continuum. What it
does add is **curvature**: the fit above shows leakage falls off steeply
between 100 and 115 GeV (density drops by roughly a factor of ~3 across
just that 15 GeV span in every category), which is a much steeper local
slope than the smooth QCD/γ+jet continuum alone. A background function
with too little shape freedom near the low edge could show larger
residuals there, or (if fit including 100–105 GeV) have its overall
normalization pulled by this locally steep component. This is exactly
why leakage matters for the fit-range and bias-study decisions below,
even though it doesn't fake a signal peak.

### Update — 17 Sep 2026: correction — the single exponential above is a poor description

As already flagged when it was fitted, the single exponential across all
four windows does not describe the leakage shape well. Looking at just
the three sub-115-GeV windows: the yield falls by a consistent factor of
**≈0.59 per 5 GeV** (inclusive: 933.7/1,609.8 = 0.580, then
568.9/933.7 = 0.609 — a steep, Z-tail-like component). Extrapolating
*that* steep component alone to 115–135 GeV gives **≈730 events**
(inclusive; ≈213 EBEB, ≈511 notEBEB) — well below the ≈1,790 the
single-exponential fit gave above. The same steep-only component
predicts only **≈100 events** in 135–180 GeV, against the **769
actually measured** there. That is a factor of ~7.7 under-prediction,
which means a second, much flatter component (the non-resonant
high-mass Drell-Yan continuum, which does not fall off nearly as fast)
must dominate by 135–180 GeV. A single exponential, fit across both
regimes at once, ends up compromising between the two and is not a
faithful description of either.

**Revised bracket for the 115–135 GeV leakage estimate: roughly
≈730 (steep-component-only) to ≈1,790 (single-exponential fit)
events, inclusive** — a factor of ~2.5 wide, not a precise number. This
does not change Part B's verdict above (leakage remains "consistent
with... not fully explaining" the 100–105 GeV excess, for the same two
caveats already given), but it does mean the previously-quoted ≈1,790
estimate should not be read as more precise than it is, and it sharpens
why the bias-study requirement below asks for the actual measured shape
rather than any fitted formula.

### Fit-range decision (input to the background-model task)

- **Default fit range: 105–180 GeV.** Excludes 100–105 GeV, the one
  window Part B flagged (+4.2σ above even the better power-law
  extrapolation) and where leakage is largest and steepest.
- **Pre-declared robustness variation: 110–180 GeV.** To be run
  alongside the default as a systematic cross-check — if the extracted
  background (and any derived signal yield) is stable between 105–180
  and 110–180, that's evidence the 105–110 GeV window isn't distorting
  the fit; if it shifts materially, that's itself informative about how
  much residual leakage curvature leaks past 105 GeV.
- 100 GeV as a fit-range floor is **not recommended**, consistent with
  every prior recommendation in this study — leakage is largest and
  steepest there, precisely where a smooth function has the least
  ability to distinguish it from noise.

This decision point is recorded here as an input; the background-model
task makes the final call.

### Bias-study requirement (recorded for the next task)

The signal-extraction bias study must include a leakage-like component
in its pseudo-data, not just the smooth QCD/γ+jet continuum:

- **Shape**: **not** the fitted exponential above — per the correction
  immediately above, a single exponential is a poor description (it
  either over-predicts 115–135 GeV or under-predicts 135–180 GeV by a
  large factor, depending which windows it favors). Instead, use the
  **actual mass distribution of the leaked DY events**: the same
  electronVeto-swapped H→γγ selection, histogrammed finely (1 GeV bins)
  over 100–180 GeV per category, exported as a template by
  `studies/hgg_cms/validation/zee/hgg_leakage_mass_template.py` (reads
  the same already-parsed DY chunks as `hgg_leakage_estimate.py`, needs
  no new download/re-parsing/`qsub`). This has not been run yet — see
  the signal-model task's final message for the exact command to run it
  on the cluster.
- **Normalization**: centered on this section's DY-based N_expected
  estimate, **varied by ±50%** to bracket the systematic uncertainty
  discussed above (data/DY normalization mismatch + unvalidated
  electron-veto inefficiency for real electrons).
- **Where it matters most**: candidate background functions must be
  stress-tested against this pseudo-data **especially in notEBEB**,
  where roughly **72%** of the total leakage across all four measured
  windows lands (2,799 of 3,881 events summed over the four windows,
  notEBEB vs. inclusive) — a materially larger fraction than notEBEB's
  ~50% share of the inclusive sideband population (Part F of
  `VALIDATION_REPORT_1.md`), so a background function that looks
  adequate inclusively could still be biased specifically in the
  notEBEB category.

### Other results recorded here for the signal-model task

- **Energy scale/resolution (Part B above): PASS in all three
  categories.** No energy-scale correction or extra smearing is needed
  for the signal model.
- **Diphoton trigger data/DY ratios (Part D above): EBEB 1.0229 ±
  0.0008, notEBEB 0.9705 ± 0.0016.** These are candidate multiplicative
  trigger scale factors for the expected signal yield
  (`VALIDATION_REPORT_1.md` Part E). Whether to apply them is a decision
  for the signal-model task, not this one.

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
| E (electron-veto leakage) | informational — **complete** | leakage is consistent with being the cause of the 100–105 GeV excess (not "fully" — see Part E's two caveats: sideband contamination of the comparison baseline, and an unquantified ~20–50% systematic on the DY normalization); feeds fit-range and bias-study decisions for the background-model task |

Nothing else raised a flag. No H→γγ blind-window data was read, printed,
or plotted while producing this report (this report never touches
`hgg_full_merged` at all — everything here is Z→ee control-region data
and DY simulation).
