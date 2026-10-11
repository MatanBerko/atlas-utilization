# HANDOFF — where the ≥3-jet data excess comes from

**Branch:** `study/cms-mc-jet-excess`, from `origin/study/cms-mc-pileup`
(`d03b3f0`, verified before branching).
**Work directory:**
`/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_jets_20261011/`
**Status: COMPLETE.** Parts A–E all done. Nothing is still running.

Diagnostic only. No selection, object definition, threshold, builder default,
registry value or delivered output was changed. Every alternative jet
definition is built alongside the delivered one inside the probe.

**Cluster route:** `wipp-campus` (the direct alias) would not connect from
the user's home VPN — TCP to `wipp-an1:22` timed out, then stalled at
"banner exchange". `wipp-home` (the same host and account, via
`sshproxy@wipp-jump.weizmann.ac.il`) works and is what this study used. Both
aliases point at `wipp-an1.weizmann.ac.il`, user `berkom`.

---

## VERDICT

**The excess is the generator, not our setup.** Our own Drell-Yan sample,
compared with the published Z+jets measurement **at particle level, with no
detector, no selection of ours and no correction in between**, under-predicts
by 17% at 3 jets, 39% at 4 jets and 59% at ≥5 jets. Scaling the simulation up
to the published particle-level cross section removes **81–120%** of the
detector-level excess and leaves a residual ratio of 1.05 / 0.96 / 0.82.

Everything in our own setup that was tested is too small: the jet definition
(nothing), jet energy resolution (3–4%), jet energy scale (would need a 4σ
mis-scale), noise or fake jets (none seen), leptons or photons counted as
jets (data is *below* simulation on every such measure).

**Confidence: high.**

---

## Part A — the published reference

| | |
|---|---|
| paper | CMS-SMP-19-009, arXiv:2205.02872, Phys. Rev. D 108 (2023) 052004 |
| luminosity | 35.9 fb⁻¹, full 2016 |
| HEPData | record `ins2078067`, Table 1a (Fig. 4), DOI `10.17182/hepdata.115655.v1/t1` |

`fetch_hepdata_reference.py` re-downloads Table 1a on every online run and
**refuses to write the evidence file if the live record disagrees with the
stored copy**. HEPData 403s most non-browser agents; it serves a plain `curl`
one, which is what the script sends (three agents tried, one worked).

### A1 — the measurement (VERIFIED BY RUNNING, downloaded from HEPData)

Exclusive jet multiplicity, σ in pb, and the JES/JER parts of the
uncertainty budget:

| N jets | σ [pb] | total | JES | JER |
|---|---:|---:|---:|---:|
| 0 | 618 ± 17 | 2.7% | 0.80% | 0.084% |
| 1 | 97.7 ± 4.4 | 4.5% | 3.7% | 0.33% |
| 2 | 22.3 ± 1.1 | 4.9% | 4.2% | 0.19% |
| 3 | 4.75 ± 0.29 | 6.2% | 5.5% | 0.29% |
| 4 | 1.113 ± 0.084 | 7.6% | 6.8% | 0.14% |
| 5 | 0.265 ± 0.021 | 8.1% | 6.7% | 1.0% |
| 6 | 0.0609 ± 0.0082 | 13% | 8.0% | 0.58% |
| 7 | 0.0131 ± 0.0039 | 30% | 9.6% | 2.4% |
| 8 | 0.0051 ± 0.0015 | 29% | 12% | 3.1% |

The **inclusive** multiplicity is not a table in this record; it is DERIVED
in the evidence file by summing the exclusive bins (the measurement stops at
8 jets, and the uncertainty is a quadrature sum that ignores bin-to-bin
correlation).

### A1 — the predictions (UNVERIFIED, read off Fig. 4a)

The record tabulates the measurement but **not** the predictions, so these
are read off the figure's lower panels by eye, to about ±0.02. That reading
uncertainty is not the theory uncertainty.

| N jets | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| MG5_aMC NLO FxFx (≤2j NLO), pred/data | 0.96 | 1.04 | 1.02 | 1.04 | 0.89 | 0.76 | 0.68 | 0.68 | 0.42 |
| MG5_aMC LO MLM (≤4j LO), pred/data | 0.95 | 0.91 | 0.81 | 0.86 | 0.94 | 0.96 | 0.99 | 1.15 | 0.51 |

**This is the first important finding.** The statement "the generators
describe the exclusive jet multiplicity within uncertainties" is true only in
the weak sense: the published NLO FxFx prediction — the same generator and
merging scheme as our sample — is itself **24% low at 5 jets, 32% low at 6
and 7, and 58% low at 8**. It agrees "within uncertainties" only because the
theory band and the data's own uncertainty are large there. The LO sample,
which has matrix elements for up to 4 jets instead of 2, does far better at
high multiplicity. That is the signature of a sample running out of
matrix-element jets.

### A1 — the paper's object definitions (verbatim quotes in the evidence file)

* **Jets**: anti-kT R = 0.4, PF + charged-hadron subtraction, **tight** jet
  ID, **|η| < 2.4**, **ΔR > 0.4** from every selected lepton, **pT > 30 GeV**
  for the single-differential cross sections. **No b-tag requirement or veto
  anywhere** — b jets are counted as jets.
* **Leptons**: leading pT > 30, subleading pT > 20 GeV, |η| < 2.4 (electrons
  excluding 1.444 < |η| < 1.566), medium ID both flavours, opposite charge,
  **mass 91 ± 20 GeV**.
* **Particle level**: cτ > 1 cm excluding neutrinos; leptons **dressed with
  photons within R < 0.1**.
* **Signal MC**: MG5_aMC 2.2.2/2.3.2, FxFx merging at 30 GeV, Z + **up to 2
  jets at NLO**, PYTHIA8 8.212, tune **CUETP8M1**, NNPDF3.0 NLO, αs = 0.118.
  The paper's own words: *"effectively yielding leading order (LO) accuracy
  for Z+3 jets."*
* **Normalisation**: *"the simulated samples are normalized to the integrated
  luminosity of the data sample using their respective cross sections."*

### A2 — how their setup differs from ours

Recorded in full in `evidence/hepdata_smp19009.json`. The ones that matter:
legacy 2016 ReReco vs our UL2016 postVFP NanoAODv9; full 2016 (35.9 fb⁻¹) vs
Run2016 G+H (16.393 fb⁻¹); **particle level vs detector level**; their
subleading lepton 20 GeV vs our 25; and the same FxFx generator but a
**different tune** — theirs CUETP8M1, our sample's CP5.

---

## Part B — the paper's counting on our data and our MC

40 data files (10 each of DoubleMuon G/H and DoubleEG G/H) and 20 MC
(10 × DY, 10 × ttbar) — the same subset the pileup study used.
**85,702,728 events read.** 2,983,050 μμ and 819,674 ee data Z events.

**Normalisation (stated):** each MC sample is put on an absolute footing with
σ_eff × 1000 × L_fb / Σw over the subset actually read, then rescaled by one
number per channel to match the data subset's inclusive Z yield, because a
data file's luminosity is not recoverable from what is stored. The factors
are **μμ 0.3222, ee 0.1328**. Everything in Parts B, C1–C4 and C6 is a shape
statement and is untouched by that factor. **Part C5 is absolute, in pb, with
no rescaling at all.**

### B1 and B2 — the jet definition changes nothing

data / simulation, μμ (VERIFIED BY RUNNING):

| definition | 0 | 1 | 2 | 3 | 4 | 5+ |
|---|---|---|---|---|---|---|
| delivered light jets (P3) | 0.999 | 0.992 | 0.998 | **1.258 ± 0.027** | **1.498 ± 0.075** | **2.146 ± 0.246** |
| delivered jets, b counted in | 0.999 | 0.988 | 1.000 | **1.256 ± 0.025** | **1.547 ± 0.068** | **1.977 ± 0.173** |
| paper-like jets, our Z | 0.999 | 0.986 | 1.003 | **1.265 ± 0.026** | **1.562 ± 0.071** | **1.998 ± 0.180** |
| paper-like jets, paper Z | 1.002 | 0.984 | 1.003 | **1.265 ± 0.025** | **1.545 ± 0.068** | **1.969 ± 0.168** |

ee behaves the same (1.187 / 1.53 / 1.91 at 3 / 4 / 5+ under every
definition). **Excluding b jets, |η| 2.5 vs 2.4, the Z mass window and the
leading-lepton threshold together move the 3-jet ratio by less than 1%.**
None of our definitional choices creates the excess.

One difference from the paper is deliberately left open: its subleading
lepton threshold is 20 GeV and ours stays at the delivered 25, because
lowering it would mean replacing the delivered lepton selection, which this
study may not do. It is common to data and simulation.

### B3 — ours against the published ratio

| jets | ours μμ delivered | ours μμ paper-like | ours ee paper-like | published data / NLO |
|---|---|---|---|---|
| 0 | 0.999 | 1.002 | 1.032 | 1.042 |
| 1 | 0.992 | 0.984 | 0.898 | 0.962 |
| 2 | 0.998 | 1.003 | 0.944 | 0.980 |
| 3 | 1.258 | **1.265** | **1.187** | 0.962 |
| 4 | 1.498 | **1.545** | **1.537** | 1.124 |
| 5+ | 2.146 | **1.969** | **1.869** | 1.316 (their = 5) |

**Our paper-like ratio does not agree with the published one.** At 3 jets the
published measurement says that generator is fine (0.96) while ours is 1.27;
the published uncertainty there is 6.2% and ours 2%, so the gap is far
outside both. The two are not the same quantity — ours is detector level and
theirs is particle level, and ours is one specific UL16 sample — which is
exactly what Part C5 then pins down.

Plot: `plots/B1_B2_jet_definitions.png`, `plots/B3_vs_published.png`.

---

## Part C — the suspects

### C1 — jet energy resolution: **RULED OUT** (removes 3–4%)

Official JME POG smearing, hybrid method (scaling against the matched
generator jet, stochastic otherwise), from
`POG/JME/2016postVFP_UL/jet_jerc.json.gz` in
`https://opendata.cern.ch/eos/opendata/cms/corrections/jsonpog-integration-2016post.tar`
(sha256 `113730e8bd3e72ecb9548cb158c8990579022432d202416317828f4bce3eb28a`,
the same tarball and checksum the pileup study used), corrections
`Summer20UL16_JRV3_MC_PtResolution_AK4PFchs` and
`Summer20UL16_JRV3_MC_ScaleFactor_AK4PFchs`. `correctionlib` is absent from
the shared environment and may not be installed into it, so `jer.py` reads
the JSON directly and **refuses to run if the node layout or the formula is
not the one it implements**. 70% of jets are generator-matched; the mean
smearing factor is 1.006 with a spread of 0.089.

| | 3 jets | 4 jets | 5+ jets |
|---|---|---|---|
| μμ | 1.265 → 1.254 (**4.3%**) | 1.562 → 1.502 (**10.7%**) | 1.998 → 2.056 (**−5.8%**) |
| ee | 1.187 → 1.173 (**7.6%**) | 1.526 → 1.515 (**2.1%**) | 1.909 → 1.887 (**2.4%**) |

Mean over the three bins: **3% (μμ), 4% (ee)**. The negative μμ 5+ entry is a
fluctuation in the least populated bin. This matches the paper's own JER
systematic on these cross sections (0.14–1.0%) in size.

### C2 — jet energy scale: **RULED OUT** (would need a 4σ mis-scale)

`Jet_pt` in NanoAODv9 is the **corrected** pT in both data and simulation:
the file's own `Jet_rawFactor` branch is titled *"1 - Factor to get back to
raw pT"*, which only makes sense if what is stored is already corrected
(VERIFIED BY RUNNING — read from the files themselves). `Jet_jetId` is titled
*"Jet ID flags bit1 is loose (always false in 2017 since it does not exist),
bit2 is tight, bit3 is tightLepVeto"*, confirming that the delivered `& 2`
is tight.

Scanning a scale shift applied to simulation: closing the 3-jet gap needs
**+9.9% (μμ)** or **+7.0% (ee)**. Calibrating against the paper's own JES
systematic on the same bin (5.5%), one standard deviation of jet energy scale
is worth about 2.4% of scale here, so the required shift is **4.1σ (μμ) /
4.0σ (ee)**. At 4 and 5+ jets even a +10% shift does not reach 1.

Plot: `plots/C1_C2_jer_jes.png`.

### C3 — noise or fake jets in data: **RULED OUT**

The 3rd-and-later jets in data and simulation are the same objects. pT, η, φ
and all four PF energy fractions agree to a few per cent
(`plots/C3_extra_jet_shapes.png`). The (η, φ) occupancy map shows **no hot
spot**: over 450 cells the data/simulation ratio runs 0.58 to 1.89 with only
1.3% of cells above 1.5, which is what ~85 jets per cell of Poisson noise
looks like; the mild red band is at |η| ≳ 2, the sparsest edge of the
acceptance (`plots/C3_occupancy.png`).

### C4 — leptons or photons counted as jets: **RULED OUT**

On every measure, the extra jets in **data are no more lepton-like than in
simulation — in most cases less**:

| fraction of 3rd+ jets, μμ | data | simulation |
|---|---:|---:|
| failing tightLepVeto jet ID | 0.12% | 0.16% |
| total EM fraction > 0.9 | 0.044% | 0.045% |
| containing ≥1 electron | 11.9% | 13.0% |
| containing ≥1 muon | 3.8% | 3.3% |

ee is the same picture. The ΔR distributions to the nearest selected lepton,
to **any** lepton with no ID requirement at all, and to the nearest photon
all agree (`plots/C4_lepton_photon.png`). Note the delivery requires **tight**
jet ID, not tightLepVeto — that is a real difference from a lepton-veto
selection, but it affects one jet in 800 and affects simulation slightly more
than data.

### C5 — generator-level closure: **EXPLAINS** (removes 81–120%)

This is the measurement that settles it. Our own DY sample's particle-level
cross section, with the paper's exact particle-level definition (NanoAOD
`GenDressedLepton`, which is dressed within R < 0.1 — the paper's own
prescription), **absolute, in pb, with no rescaling**:

| jets | ours μμ [pb] | measured [pb] | ours / measured |
|---|---:|---:|---:|
| 0 | 578.4 ± 0.6 | 618 ± 17 | 0.936 ± 0.001 |
| 1 | 103.5 ± 0.3 | 97.7 ± 4.4 | 1.059 ± 0.003 |
| 2 | 23.17 ± 0.18 | 22.3 ± 1.1 | 1.039 ± 0.008 |
| 3 | 3.946 ± 0.074 | 4.75 ± 0.29 | **0.831 ± 0.016** |
| 4 | 0.684 ± 0.031 | 1.113 ± 0.084 | **0.615 ± 0.028** |
| 5+ | 0.141 ± 0.015 | 0.344 ± 0.023 | **0.410 ± 0.043** |

(errors are MC statistics; the measurement's own 6–8% is carried separately
into Part D. ee agrees: 0.857 / 0.642 / 0.429. Our 5+ bin is inclusive, so it
is compared with the sum of the published 5, 6, 7 and 8 jet bins.)

The particle-level counts deliberately carry **genWeight alone** — L1
prefiring is a detector effect and is jet dependent, so folding it in would
have suppressed exactly these bins. Its size is recorded anyway: 0.981 at 0
jets falling to 0.952 at 5+.

**Our sample is also worse than the published FxFx curve** (0.83 vs 1.04 at
3 jets, 0.62 vs 0.89 at 4). The most likely reason, stated as interpretation
and not as a measurement: our sample uses the **CP5** tune and the published
one **CUETP8M1**, and CP5's lower parton-shower αs produces fewer extra jets
— which is precisely where a ≤2-jet FxFx sample gets its 3rd, 4th and 5th
jets from.

Plot: `plots/C5_generator_closure.png`.

### C6 — reco vs gen migration

Column-normalised, μμ, simulation: a generator 3-jet event is reconstructed
with 3 jets 73.7% of the time, with 2 jets 18.8%, with 4 jets 5.5%. Diagonal
purity 0.96 / 0.85 / 0.81 / 0.74 / 0.71 / 0.83 for 0…5+ jets. Reconstruction
does lose jets, but it loses them in simulation and in data alike — and C1
and C2 bound how much that loss could differ.
Plot: `plots/C6_migration.png`.

---

## Part D — what each suspect explains

| channel | jets | data/MC | C1 JER | C2 JES needed | C5 generator | residual after C5 |
|---|---|---:|---:|---:|---:|---:|
| μμ | 3 | 1.265 | 4.3% | 4.1σ | **81 ± 31%** | 1.051 |
| μμ | 4 | 1.562 | 10.7% | beyond +10% | **107 ± 24%** | 0.961 |
| μμ | 5+ | 1.998 | −5.8% | beyond +10% | **118 ± 25%** | 0.819 |
| ee | 3 | 1.187 | 7.6% | 4.0σ | **91 ± 40%** | 1.017 |
| ee | 4 | 1.526 | 2.1% | beyond +10% | **104 ± 25%** | 0.979 |
| ee | 5+ | 1.909 | 2.4% | beyond +10% | **120 ± 25%** | 0.820 |

| suspect | μμ | ee | verdict |
|---|---|---|---|
| C1 jet energy resolution | 3% | 4% | **RULED OUT** |
| C2 jet energy scale | needs 4.1σ+ | needs 4.0σ+ | **RULED OUT** |
| C3 noise / fake jets | no hot spot, identical shapes | same | **RULED OUT** |
| C4 leptons / photons as jets | data below simulation | same | **RULED OUT** |
| C5 generator modelling | 102% | 105% | **EXPLAINS** |

Missing simulated processes cannot rescue the others: ttbar is only **5.5% of
the simulation at 3 jets, 10.6% at 4 and 17.2% at 5+**, and single top and
dibosons — which we do not have — are smaller still.

**Overall conclusion, high confidence:** the ≥3-jet excess is our Drell-Yan
sample under-producing hard extra radiation, not a defect in our selection,
calibration or reconstruction. The residual after correcting the generator to
the published measurement is 1.05 / 0.96 / 0.82 — consistent with one at 3
and 4 jets and over-corrected at 5+.

### Still untested

* The 5+ residual of 0.82 is over-corrected. Our 5+ bin is inclusive and the
  published comparison bin is a sum of four sparse bins; detector migration
  into 5+ (C6 shows 6.4% of generator-4-jet events reconstruct as 5+) is not
  unfolded. This is not understood to better than ~20%.
* The CP5-vs-CUETP8M1 tune explanation is an interpretation, not a
  measurement. Testing it needs a second DY sample with a different tune,
  which is outside this study.
* ee at 1 and 2 jets sits at 0.90 and 0.94 — a separate ~6–10% electron-side
  normalisation question that this study did not look at and that is not the
  jet excess.
* Only DY and ttbar are in the subset; single top and dibosons are absent.
* The subleading lepton threshold is 25 GeV, not the paper's 20.

---

## Part E — does this concern the ATLAS side?

Written assessment only. Nothing was run on ATLAS data or simulation, and
`/storage/agrp/marybo/` was never accessed.

### E1 — what the upstream pipeline applies to ATLAS jets

VERIFIED BY RUNNING (`git grep` over `upstream/master`, fetch-only remote,
push URL `DISABLED`):

| correction | applied upstream? | evidence |
|---|---|---|
| jet calibration (JES) | **not by the pipeline** — taken as it comes in PHYSLITE | `services/parsing/schemas.py:24` reads only `["pt","eta","phi","mass"]` for `Jets` |
| JVT (pileup-jet removal) | **NO** | no JVT branch is read anywhere; a repository-wide search for `jvt`, `isBad`, `looseBad`, `jetClean`, `calibrat`, `smear` over every file in `upstream/master` returns nothing but unrelated stage-timing code |
| jet cleaning | **NO** | same search |
| JER smearing | **NO** | same search |
| b-tagging | yes, as a raw discriminant cut | `config.yaml:97-100` (`enable_jet_tagging: true`, `DL1d: 2.51`) and `services/parsing/schemas.py:31-35` (`BTagging_AntiKt4EMPFlowAuxDyn.DL1dv01_pb/pc/pu`) |
| kinematics | pT > 30 GeV, \|η\| < 2.5 | `config.yaml:121-122` |

`services/parsing/event_selection.py:66` (`apply_parsing_event_selection`)
applies kinematic cuts and object-count ranges and nothing else.

What the ATLAS Open Data documentation says:

* PHYSLITE *"incorporates calibrated objects and selections with lower
  transverse momentum (pT) thresholds, coupled with elements like machine
  learning scores"* —
  <https://opendata.atlas.cern/docs/documentation/data_format/physlite>.
  So the **calibration is already applied** before the analyser sees the jets.
* The research ntuples expose `jet_pt_jer1` and `jet_pt_jer2`, *"transverse
  momentum of the jet after applying a specific systematic uncertainty from
  the jet energy resolution calibration"*, and a `ScaleFactor_JVT` —
  <https://opendata.atlas.cern/docs/tutresearch/derivation_framework>.
  A JVT scale factor only exists to accompany a JVT **selection**, which the
  analyser is expected to make.
* UNVERIFIED: the documentation does not state whether the nominal PHYSLITE
  jets already carry a JER smearing, only that JER *variations* are provided.
  Do not assume either way.

### E2 — would the same suspects bite on the ATLAS side?

* **C5, the one that actually explains the CMS excess, is generator-specific,
  not experiment-specific.** The question transfers directly: what Z+jets
  generator do the ATLAS samples use, and how many jets does its matrix
  element cover? If it is Sherbra/Sherpa merged to higher multiplicity it
  will behave better than a ≤2-jet FxFx sample; if it is a low-multiplicity
  merged sample it will show the same growing deficit. **This is worth
  checking before anyone reads an ATLAS high-jet-multiplicity data/MC ratio
  as a detector problem.**
* **JVT is a real gap on the ATLAS side that has no CMS counterpart here.**
  ATLAS ships a JVT scale factor precisely because analysers are expected to
  cut on JVT; the upstream pipeline does not, and reads no JVT branch. Its
  absence would show up as a jet-multiplicity data/MC trend that **grows with
  pileup** — which is the signature the CMS pileup study explicitly looked
  for and did not find on the CMS side (the double ratio was flat at
  ≈1.25–1.3 across the whole pileup range). On ATLAS it has not been looked
  for at all.
* **Jet cleaning** is likewise not applied; its effect would be localised in
  (η, φ) — the C3 occupancy map is the test, and it is cheap.
* C1/C2 (resolution and scale) are small on the CMS side and there is no
  reason to expect them to be larger on ATLAS, where the calibration is
  applied in PHYSLITE.

---

## Plots

`studies/cms_mc_weights_v3/jets/plots/`:
`B1_B2_jet_definitions.png`, `B3_vs_published.png`, `C1_C2_jer_jes.png`,
`C3_extra_jet_shapes.png`, `C3_occupancy.png`, `C4_lepton_photon.png`,
**`C5_generator_closure.png`**, `C6_migration.png`.

## Jobs

| Job ID | What | Commit | Result |
|---|---|---|---|
| `5213412[1-60]` | probe, first pass | `efc6599` | 60/60 exit 0 |
| `5213414[1-60]` | probe, second pass (the one used) | `d5bc51e` | 60/60 exit 0 |
| interactive | merge, tables, plots | `d29ddc3` | exit 0 |

The probe was re-run once because the first pass folded the L1 prefiring
weight into the particle-level counts, which would have biased Part C5 in
exactly the bins it is about. The second pass wrote to `probe2/` so the first
pass was not overwritten; `probe/` also holds two interactive smoke-test
files, which the merge skips by name.

## Commits

| Commit | What |
|---|---|
| `efc6599` | Part A reference, the probe, the JER reader, the self-checks |
| `26a5e98` | particle-level counts keep genWeight alone; the merge and plots |
| `d5bc51e` | `PROBE_DIR`, so a re-run does not overwrite |
| `aadf6d0` | Part D scoring; JER table no longer divides by no excess |
| `d29ddc3` | 5+ kept in the scale scan |

## File-count budget

| | |
|---|---:|
| budget | < 3,000 |
| **added by this study** | see the final report |
| quota before | 108,515 of a 150,000 soft limit |

The pinned checkout is archived as required (`repo.tar` beside it, entry
count verified, original removed). That is the only removal this study made.

## How to resume or re-run

```
ssh wipp-home                       # wipp-campus does not connect over the VPN
W=/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_jets_20261011
tar -xf $W/repo.tar -C $W           # restore the pinned checkout
```
or clone fresh and `git checkout d29ddc3`. The official correction files stay
at `$W/corrections/POG/{JME,LUM}/2016postVFP_UL/`. The file subset is
`$W/probe_mapping.txt`.

Read-only throughout: the delivered production, the pilot work dir, the
pileup work dir, every other `output/` and `work/` directory.
`/storage/agrp/marybo/` never accessed. No ACL changed. Jobs wrote nothing to
the real `$HOME`. Upstream was fetched read-only and its push URL is still
`DISABLED`.
