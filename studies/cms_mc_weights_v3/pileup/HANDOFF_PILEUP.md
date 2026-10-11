# HANDOFF — pileup study of the ≥3-jet data excess

**Branch:** `study/cms-mc-pileup`, from `origin/feature/cms-mc-weights-v3`
(`68ab281`, verified before branching).
**Work directory:**
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_pileup_20261011/`
**Status: COMPLETE.** Parts A and B both ran. Nothing is still running.

Diagnostic only. No selection, object definition, threshold, builder default,
registry value or delivered output was changed.

---

## VERDICT

**Pileup does not explain the ≥3-jet excess.** All five pre-stated criteria
fail or point away from pileup, and all three signatures of the alternative
(generator modelling of hard extra radiation) are met. Confidence: **high**.

The single most telling pair of numbers: the official pileup weight **fixes
the vertex distribution** — mean good vertices data/MC goes from 1.138 to
**1.037** (μμ) — and yet the ≥3-jet excess **barely moves**: 1.279 → 1.263.
Pileup in this MC really is mismodelled, and correcting it does not touch the
jet problem.

---

## Part A1 — the official pileup profile (found, and used)

| | |
|---|---|
| what | CMS LUM POG `correctionlib` pileup weights |
| correction | `Collisions16_UltraLegacy_goldenJSON`, version 0 |
| era of the file | 2016 **postVFP**, Ultra-Legacy |
| URL | `https://opendata.cern.ch/eos/opendata/cms/corrections/jsonpog-integration-2016post.tar` |
| member | `POG/LUM/2016postVFP_UL/puWeights.json.gz` |
| tarball sha256 | `113730e8bd3e72ecb9548cb158c8990579022432d202416317828f4bce3eb28a` |
| input | `NumTrueInteractions`, [0, 99), `flow: clamp` |
| variations | nominal, up, down |
| derivation | official golden-JSON LUM POG weights, taken as published |

**Approximation, stated:** the file covers the **whole 2016 postVFP period**;
our data is **Run2016 G+H**, a subset of it (16.393 fb⁻¹). It is the finest
granularity published. Nothing was hand-typed or taken from a forum — the
file is downloaded on the cluster and read at run time. `correctionlib` is
not in the shared environment and this study may not modify that environment,
so `pu_weights.py` reads the JSON directly; it refuses to run if the file's
node layout is anything other than the category+uniform-binning+clamp it
implements.

## Part A2/A3 — the weight, checked (all VERIFIED BY RUNNING)

Denominator built from **all generated events** of each sample (98 files,
116,385,442 events; only `Pileup_nTrueInt` and `genWeight` read), because the
selection sculpts pileup.

| record | mean w_PU over all generated events | ⟨nTrueInt⟩ before → after | empty-MC-but-weighted bins | events ≥ 99 |
|---|---:|---|---:|---:|
| 35669 DY | **0.99988** | 22.354 → 24.891 | 28 | 0 |
| 67801 ttbar | **0.99993** | 22.355 → 24.891 | 27 | 0 |
| 37728 ggH | **1.00031** | 22.358 → 24.904 | 40 | 0 |

The mean landing on 1.000 confirms these samples follow the standard UL16 MC
pileup profile the official weights assume. Weight range **0.00030 – 2.414**;
nothing was capped. The "empty-MC-but-weighted" bins are all at nTrueInt
above ~60 where the samples have no events at all — they cannot contribute.

Data has about **11% more pileup** than this MC (⟨nTrueInt⟩ 22.4 → 24.9 after
weighting): a real but modest shift.

## Part A4 — the pilot plots, with and without w_PU (absolute normalisation)

Light-jet multiplicity in Z events, data/MC **before → after** the weight:

| jets | μμ before | μμ after | ee before | ee after |
|---|---:|---:|---:|---:|
| 0 | 1.035 | 1.042 | 0.954 | 0.977 |
| 1 | 1.018 | 1.009 | 0.938 | 0.943 |
| 2 | 1.032 | 1.022 | 0.944 | 0.945 |
| **3** | **1.279** | **1.263** | **1.174** | **1.167** |
| **4** | **1.573** | **1.540** | **1.518** | **1.488** |
| **5+** | **2.030** | **1.964** | **2.108** | **1.993** |

The weight removes **4–10% of the excess**, leaving 26%, 54% and 96%
unexplained at 3, 4 and 5+ jets in μμ.

Plots: `plots/A3_pu_weight_and_profile.png`, `plots/A4_P1_zpeak_mumu.png`,
`plots/A4_P2_zpeak_ee.png`, `plots/A4_P3_jet_multiplicity.png`,
`plots/A4_P3_bjet_multiplicity.png`.

## Part B — the fingerprint checks

40 data files (10 each of DoubleMuon G/H and DoubleEG G/H) and 20 MC
(10 × DY, 10 × ttbar), chosen evenly spaced through each list. μμ from
DoubleMuon (inclusive), ee from DoubleEG (exclusive) — the delivery's own
de-duplication rule. 2,983,050 μμ and 819,674 ee Z events in the data subset.

Part B is a **shape** study: a data file's integrated luminosity is not
recoverable from what is stored, so MC — put on an absolute footing with
σ_eff×1000×L/Σw over the subset actually read — is rescaled by one reported
factor per channel (μμ 0.3222, ee 0.1328) to match the data subset's
inclusive Z yield. Every criterion Part B tests is a shape statement. The
absolute test is Part A4.

### The decisive measurement (B2 vs B2b)

**B2** — data/MC at ≥3 jets vs good vertices — rises steeply:
μμ 0.85 → 2.84 (45σ), ee 0.875 → 2.20 (21σ).

But the **0–2-jet** ratio rises just as steeply (μμ 0.649 → 2.039), because
the MC simply has too few high-pileup events. **B2b** divides that out:

> double ratio = [data/MC at ≥3 jets] / [data/MC at 0–2 jets]

| channel | double ratio across the 5 pileup bins | slope | first → last |
|---|---|---:|---|
| μμ | 1.311, 1.273, 1.222, 1.238, 1.391 (±0.018) | +0.0037/vertex | +0.080 (2.9σ) |
| ee | 1.253, 1.240, 1.246, 1.174, 1.284 (±0.031) | +0.0006/vertex | +0.031 (0.7σ) |

**Essentially flat at ≈1.25–1.3 across the whole pileup range**, and sitting
well above 1 everywhere. The jet excess exists at every pileup level and does
not grow with pileup. The μμ points are not monotonic (they dip then rise),
so the small fitted slope is driven by the highest bin; ee shows no slope at
all. `plots/B2b_double_ratio_vs_npvs.png`.

---

## The five pre-stated criteria

| | criterion | verdict | the numbers |
|---|---|---|---|
| **(i)** | after w_PU the ≥3-jet ratios move most of the way to 1 | **NOT SUPPORTED** | only 4–10% of the excess is removed (μμ 5+: 2.030 → 1.964). The weight *is* working: mean vertices data/MC 1.138 → 1.037 |
| **(ii)** | the B2 ratio rises clearly with PV_npvsGood | **met as literally stated, but it is not jet-specific** | B2 rises 0.85 → 2.84 (45σ) — but so does the 0–2-jet ratio (0.649 → 2.039). The double ratio B2b is flat (+0.080, 2.9σ in μμ; +0.031, 0.7σ in ee) |
| **(iii)** | the excess shrinks strongly at 40–50 GeV | **NOT SUPPORTED** | μμ 3 jets 1.258 / 1.234 / 1.195 at 30/40/50 GeV; μμ 5+ 2.146 / 2.142 / 1.846; ee 3 jets 1.187 / 1.182 / 1.201 |
| **(iv)** | the extra jets are soft and/or forward | **NOT SUPPORTED** | 3rd-jet mean pT: μμ data 45.41 vs MC 45.99 GeV (1.3% softer); mean \|η\|: data 1.128 vs MC 1.148 (1.7% more central). ~1–2% differences cannot produce a 30–100% excess |
| **(v)** | data fails the pileup-jet ID clearly more than MC | **PARTLY — and in the wrong place** | fail fraction data/MC: 1 jet 0.0778/0.0519 (+50%), 2 jets 0.0523/0.0344 (+52%), 3 jets 0.0386/0.0317 (+22%), 4 jets 0.0302/0.0250 (+21%), **5+ jets 0.0219/0.0258 (data 15% LOWER)**. The gap shrinks and reverses exactly where the excess is largest |

`Jet_puId` is present in both data and MC with the identical title *"Pileup ID
flags with 106X (2016) training"*; "loose" is taken as bit 0. **Diagnostic
only — the pileup-jet ID was not applied to anything.**

### Generator modelling instead?

The task's stated signature is *"the excess survives at 50 GeV, is flat in
PV_npvsGood, and persists after w_PU"*. **All three hold**: it survives at
50 GeV (iii), the jet-specific part is flat in pileup (B2b), and it persists
after w_PU (i). Hard extra radiation that the Drell-Yan generator
under-produces at high jet multiplicity fits every observation here.

**Confidence: high** that pileup is not the main cause. Honest caveats:
* the official profile covers whole postVFP, not G+H specifically;
* Part B is a 40-data/20-MC file subset and a shape study;
* Part B's MC is DY + ttbar only;
* pileup is not *zero*: w_PU removes 4–10% of the excess and μμ's double
  ratio has a 2.9σ slope, so a small pileup component is present — it is just
  not the bulk.

## Plots

`studies/cms_mc_weights_v3/pileup/plots/`: `A3_pu_weight_and_profile.png`,
`A4_P1_zpeak_mumu.png`, `A4_P2_zpeak_ee.png`, `A4_P3_jet_multiplicity.png`,
`A4_P3_bjet_multiplicity.png`, `B1_npvs.png`, `B2_ratio_vs_npvs.png`,
**`B2b_double_ratio_vs_npvs.png`**, `B3_ratio_vs_threshold.png`,
`B4_third_jet.png`, `B5_pujet_id.png`.

## Jobs

| Job ID | What | Commit | Result |
|---|---|---|---|
| `5210846/7/8` | A2 MC pileup profile, 98 files | `5398ac4` | 3/3 exit 0 |
| `5210849[1-60]` | Part B probe, first pass | `5398ac4` | 60/60 exit 0 |
| `5210857` | A3 + A4 | `e3e019d` | exit 0, 7.1 GB, 4 min |
| `5210872` | Part B merge, first pass | `e3e019d` | exit 0 |
| `5210884[1-60]` | Part B probe, re-run with `--pu-json` | `47f386f` | 60/60 exit 0 |
| `5210906` | Part B merge with the B2b double ratio | `47f386f` | exit 0 |

The probe was re-run once because the first pass was never handed
`--pu-json`, so its pileup-weighted histograms were empty and B1's weighted
curve could not be drawn. One `qsub` was rejected for violating queue limits
and was resubmitted with `-l io=25`.

## File-count budget

| | |
|---|---:|
| budget | < 3,000 |
| **added by this study** | **349** |
| quota before / after | 108,163 → **108,512** of a 150,000 soft limit |

The pinned checkout was archived as required: `repo/` (1,971 inodes,
164,807,656 bytes) → `repo.tar` (1,971 entries — verified equal — 165,058,560
bytes), then the original removed. That is the only removal this study made.

## How to resume or re-run

```
ssh wipp-campus
W=/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_pileup_20261011
tar -xf $W/repo.tar -C $W        # restore the pinned checkout
```
or clone fresh and `git checkout 47f386f`. The official pileup file stays at
`$W/corrections/POG/LUM/2016postVFP_UL/puWeights.json.gz`.

Read-only throughout: the delivered production, the pilot work dir, every
other `output/` and `work/` directory. `/storage/agrp/marybo/` never
accessed. No ACL changed. Jobs wrote nothing to the real `$HOME`.
