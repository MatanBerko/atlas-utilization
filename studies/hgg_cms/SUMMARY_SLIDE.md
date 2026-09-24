# H→γγ Open Data result — group meeting summary

- **Independent H→γγ search on public CMS 2016 Open Data** (Runs G+H,
  16.393 fb⁻¹ ± 1.2%) — our own selection, signal model, background
  model, and statistical analysis, built from scratch.
- **Local significance Z = 4.13σ** (p = 1.82×10⁻⁵) at m_H = 125.09 GeV,
  vs. a pre-registered expected Z = 3.91σ. Per our own pre-declared
  wording rule (3≤Z<5), this is **"evidence for a signal"**, not yet a
  5σ observation.
- **μ = 1.06 (+0.37/−0.30)** — consistent with the Standard Model
  (μ=1) well within 1σ.
- **Best-fit mass 125.7 (+0.34/−0.27) GeV**, consistent with the
  world-average 125.09 GeV.
- Result is carried almost entirely by the high-purity **EBEB**
  category (Z=4.10σ); the lower-purity **notEBEB** category alone
  gives only Z=0.87σ.
- **Global (look-elsewhere-corrected) significance ≈ 3.64σ**
  (Gross–Vitells) for the largest excess anywhere in the 110–150 GeV
  scan range — still evidence-level after the trials penalty.
- **Six pre-declared robustness checks** (background function, fit
  range, spurious-signal terms, per-category, per-run-period, energy
  scale/resolution) all land in Z ≈ 2.6–4.9σ, all positive, none
  reversing the result.
- **The hardest problem we hit:** no background function passed our
  own bias criterion in the notEBEB category — traced to a real effect
  (candidate functions there disagree with each other by more than the
  size of the signal peak itself), not bad luck. We used the
  least-bad available function and carry its cost as a systematic
  (+14.6% signal-yield uncertainty in notEBEB).
- **Blinded and pre-registered**: the model, fit procedure, and
  reporting thresholds were frozen (by file hash) before the signal
  region was ever opened; only two procedural deviations after
  freezing, both pre-approved, neither touching the analysis itself.
- **What would improve it most:** an MVA-based photon categorization
  and a VBF category (like CMS's real analysis), a proper vertex
  algorithm, and the CMS-style background-function envelope method
  instead of a single fixed choice.

![money plot](stats/results/plots/final/hgg_money_plot.png)

*S/B-weighted m_γγ spectrum, 1 GeV bins: data (black), signal+background
fit (red), background component of that fit (dashed blue, ±1σ band).
Lower panel: background-subtracted residual with the fitted signal
curve. Full details: `FINAL_REPORT.md` §9.4.*
