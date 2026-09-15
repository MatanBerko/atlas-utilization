# Phase 2.2 — CMS H→γγ event selection: design document

**This is a design document only.** No selection code, pipeline changes,
histograms of the Higgs region, or fits were produced. Small, read-only
exploration scripts used to check specific design assumptions live in
`studies/hgg_cms/design_checks/`, respecting a 1,000-event/file cap and the
blinding rule below.

**Blinding.** No script in this task ever computes or reports a diphoton
mass value for a real DoubleEG event in the window 115–135 GeV. Where a
cutflow needed to know whether a candidate fell in that window, only a
*count* is kept — never the mass itself. See
`design_checks/data_cutflow_and_zee.py`.

Every physics claim below cites its source: a paper section/table, a
NanoAOD branch's own documentation string (read directly from a real
file), or a portal record. Anything not directly verified is marked
**UNVERIFIED**.

---

## Section 1 — Reference analysis

**Identified and verified**: CMS's own 2016 H→γγ properties measurement.
The paper's own first page, extracted directly from the arXiv PDF, prints
its internal report number **CMS-HIG-16-040**; the paper is
[arXiv:1804.02716](https://arxiv.org/abs/1804.02716), published as
**JHEP 11 (2018) 185**, doi:10.1007/JHEP11(2018)185 — the exact reference
the task named, now confirmed by reading the document itself rather than
assumed. It uses the **full 2016 dataset, 35.9 fb⁻¹** (Run2016B–H, not
just G+H — a scope difference already flagged in
`studies/hgg_cms/INVENTORY.md`, "Consequential point 4").

### What the paper's preselection actually requires

Quoted from Section 5.2 ("Photon preselection") and Table 1 of the paper:

- **Kinematics**: leading photon pT > 30 GeV, subleading pT > 20 GeV.
- **η acceptance**: `|η| < 2.5, excluding the barrel-endcap transition
  region 1.44 < |η| < 1.57`, "where the photon energy reconstruction is
  affected by a suboptimal containment of the electromagnetic shower."
- **Shower-shape cuts** (R9, σ_ηη) and an **H/E cut**, both category-split
  (barrel vs. endcap, high-R9 vs. low-R9), exact numeric thresholds in
  Table 1:

  | | R9 | H/E | σ_ηη | I_ph (GeV) | I_tk (GeV) |
  |---|---|---|---|---|---|
  | Barrel, R9∈[0.5,0.85] | — | <0.08 | <0.015 | <4.0 | <6.0 |
  | Barrel, R9>0.85 | — | <0.08 | — | — | — |
  | Endcap, R9∈[0.8,0.90] | — | <0.08 | <0.035 | <4.0 | <6.0 |
  | Endcap, R9>0.90 | — | <0.08 | — | — | — |

  plus an additional combined requirement: "(a) R9 > 0.8 and I_ch < 20 GeV,
  or (b) I_ch/pT < 0.3."
- **Electron veto**: "rejects the photon candidate if its supercluster is
  matched to an electron track with no missing hits in the innermost
  tracker layers" — this is precisely what NanoAOD's `Photon_electronVeto`
  branch encodes (see Section 2).
- **Isolation**: photon isolation I_ph (ΣET of photon PF candidates in
  ΔR=0.3, pileup-corrected), track isolation I_tk (ΔR=0.3 hollow cone,
  inner veto ΔR=0.04), and a loose charged-hadron isolation I_ch.
- **Trigger-vs-preselection relationship**, quoted directly: "The photons
  considered further in this analysis are required to satisfy
  preselection criteria similar to, but slightly more stringent than, the
  trigger requirements." I.e. preselection is a tightened version of the
  trigger's own online cuts (ET 30/18 GeV, loose calo ID, loose isolation,
  H/E, R9 — Section 4 of the paper, already quoted in `INVENTORY.md` A.4).
- **Mass range**: "100 < mγγ < 180 GeV" (Section 7 and Fig. 2 caption).
- **Scaled pT cuts** (Section 7, quoted exactly): "The event selection
  requires two preselected photon candidates with pγ1_T > mγγ/3 and
  pγ2_T > mγγ/4, in the mass range 100 < mγγ < 180 GeV. The use of pT
  thresholds scaled by mγγ prevents a distortion of the low end of the
  invariant mass spectrum. The requirement on the photon pT is applied
  after the vertex assignment."
- **Sidebands**, quoted (Section 8): "mγγ < 115 GeV or mγγ > 135 GeV" —
  the exact numbers this task's blinding rule uses, confirming the
  blinding window matches the paper's own convention, not an arbitrary
  choice.

### Photon identification BDT (beyond preselection)

Section 5.3: a dedicated BDT trained on simulated γ+jet events (prompt
photon = signal, jet fragment = background) is applied *on top of*
preselection. Its inputs include shower-shape variables, isolation
(including a "worst-vertex" charged-hadron isolation variant, tied to the
vertex problem in Section 3 below), and photon η/energy. **This exact BDT
cannot be reproduced from NanoAOD** — it is a CMS-internal, non-public
training. NanoAOD instead ships a *different*, standard EGM POG MVA ID
(`Photon_mvaID`, "Fall17V2") with two pre-computed working points,
`Photon_mvaID_WP80`/`WP90` — see Section 2.

### Diphoton vertex and event categorization — cannot reproduce

Section 6 (vertex) and Section 7 (categorization): a dedicated **vertex
identification BDT** picks the diphoton production vertex among all
reconstructed vertices (inputs: track-based observables, conversion-track
information); a second **vertex probability BDT** estimates whether that
choice is within 10 mm of truth; and a **diphoton BDT** assigns each event
to one of many mutually exclusive categories (targeting ggH, VBF, VH, ttH
production, and mass-resolution/purity sub-categories within ggH), each
fit with its own signal/background model. **None of this is reproducible
with only NanoAOD**: the vertex BDTs need track-level and conversion
information not exposed per-vertex in NanoAOD beyond the single chosen
`PV`, and the diphoton/production-category BDTs are unpublished CMS
internal trainings. Our v1 selection (Section 2) is therefore a single
inclusive category, not a categorized fit — expected to have *worse*
signal-to-background and correspondingly lower significance per collected
luminosity than the paper's categorized result, though by how much is not
quantified here (would need our own optimization study, out of scope for
this design document).

### Estimated cost of what we cannot reproduce

| Missing piece | Effect | Size, from the paper (Section 1 citations above) | Estimated here? |
|---|---|---|---|
| Dedicated diphoton vertex BDT | Worse mass resolution when the wrong vertex is picked | Paper's BDT: ~81% correct-vertex rate (within 10 mm); our default-vertex-only rate is directly measured in **Section 3** below | Yes — measured |
| Dedicated photon ID BDT (vs. generic EGM `mvaID`) | Different background rejection at fixed signal efficiency; not directly comparable | UNVERIFIED — the paper does not quote its BDT's own working-point efficiency numerically in the text extracted here | No |
| Diphoton BDT / production-mode categorization | Lower significance per fb⁻¹ (single inclusive category vs. many optimized ones) | UNVERIFIED — paper does not state an inclusive-vs-categorized significance ratio in the sections read here | No |
| Energy regression refinements (BDT-corrected cluster energy) | Baked into `Photon_pt` already (see Section 2) — not an extra step we're missing, just one we can't customize further | N/A | N/A |

---

## Section 2 — Proposed event selection (default v1)

Numbered cutflow. "Consequential" = could change the Higgs peak position,
width, or yield, or the background shape.

**0. Validated runs.** Filter to lumisections certified good using record
**14220**, `Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`
(`studies/hgg_cms/INVENTORY.md` A.3). *Consequential*: skipping this could
include data from misbehaving sub-detectors — CMS's own NanoAOD production
does **not** pre-filter by certification (certification happens after
reconstruction), so this must be applied explicitly, not assumed to be
already done. Alternative: none sensible — this is a standard, required
step for any CMS analysis.

**1. Trigger.** Require
`HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90 == True` in data —
confirmed to exist as a real branch and to fire in DoubleEG (24.6% of a
1,000-event sample, `INVENTORY.md` C.2). **Also require it in simulation**:
the same bit exists in the ggH signal file and was directly checked here
(`design_checks/mc_trigger_check.py`,
`mc_trigger_check_results.json`) —
59.3% of the first 1,000 simulated ggH events pass it (higher than in raw
data, as expected: the signal sample is enriched in real, high-quality
diphoton pairs already close to the analysis phase space). *Justification*:
requiring the trigger in MC is the standard way trigger inefficiency
becomes part of the simulated signal efficiency automatically, so the
same cut must be applied on both sides for the normalization formula
in Section 4 to be self-consistent. *Consequential*: omitting the trigger
requirement from MC would overestimate the expected signal yield by
whatever fraction of signal MC events the trigger would have rejected.

**2. Photon candidates — kinematics and acceptance.**
- pT > 20 GeV (loose, pre-scaled-cut; matches roughly the paper's
  subleading preselection pT and is loosened further at the diphoton step
  below).
- Supercluster η acceptance: `|η_SC| < 2.5`, excluding
  `1.4442 < |η_SC| < 1.566` (paper's own numbers, quoted above, to 4
  significant figures as commonly quoted by CMS EGM; the paper itself
  rounds to 1.44/1.57). **How NanoAOD encodes this, verified directly**:
  `Photon_isScEtaEB` ("is supercluster eta within barrel acceptance") and
  `Photon_isScEtaEE` ("is supercluster eta within endcap acceptance") —
  both booleans, read directly from a real file (`INVENTORY.md` C.1).
  Proposed rule: **keep a photon only if `isScEtaEB OR isScEtaEE` is
  true**; a photon in the excluded gap has neither flag set. This specific
  behavior (that the gap sets *both* flags false, rather than one of them
  covering the gap) was **not independently re-verified with actual gap
  photons in this task** — the 1,000-event `design_checks` samples did not
  happen to contain a controlled check of this — and is flagged as
  **UNVERIFIED, low-risk**: even if the assumption were wrong, the
  visible symptom would be a small (or zero) η-gap exclusion rather than a
  silent bias, and would show up immediately as an eta distribution
  spike at 1.44–1.57 in the first real cutflow validation (Section 5).
- *Consequential*: yes — the η gap and acceptance directly shape which
  photons are considered and thus the background composition and
  resolution (gap photons have markedly worse energy resolution, per the
  paper's own stated reason for excluding them).

**3. Photon identification.** **Default: `Photon_mvaID_WP90 == True`.**
WP90/WP80 are CMS EGM POG standard working points, named for their
approximate signal efficiency by construction (~90%/~80% for genuine
prompt photons passing preselection) — confirmed via CMSSW's own naming
convention (`mvaPhoID-RunIIFall17-v2-wp90`/`wp80`,
[cms-sw/cmssw photons_cff.py](https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/photons_cff.py))
and the CMS Open Data workshop's own physics-objects material
([cms-opendata-workshop.github.io](https://cms-opendata-workshop.github.io/workshop2024-lesson-physics-objects/02-electrons.html)).
Precise numeric fake-rate/efficiency curves for this specific MVA are
**UNVERIFIED here** — not extracted from a primary CMS EGM document in
this task (see [arXiv:2012.06888](https://arxiv.org/pdf/2012.06888),
"Electron and photon reconstruction and identification with the CMS
experiment at the CERN LHC", as the general reference where such numbers
would be published, not read in this pass).
- **Alternative A — `Photon_mvaID_WP80`**: tighter, ~80% efficiency,
  better background rejection. Trade-off: fewer signal events, smaller
  statistical uncertainty on the background shape estimated from data
  sidebands (fewer sideband events too).
- **Alternative B — `Photon_cutBased >= 1`** (loose) or `>= 2` (medium):
  the older cut-based ID; NanoAOD's own doc string gives the ordinal
  meaning directly, "(0:fail, 1:loose, 2:medium, 3:tight)"
  (`INVENTORY.md` C.1). Generally lower-performing than the MVA at fixed
  efficiency (general EGM POG knowledge; not numerically verified here).
- *Consequential*: yes, directly sets signal efficiency and background
  rate; **default is WP90**, both alternatives should be tried as a
  systematic cross-check once real fits exist (Phase 4+), not in this
  design phase.

**4. Electron veto.** **Default: `Photon_electronVeto == True`**
("conversion-safe", matches the paper's own definition quoted in Section
1 almost verbatim — NanoAOD's doc string: "pass electron veto"). CMS's own
measurement of this cut's efficiency (Table 2, quoted in Section 1) is
20–60 GeV pT, no significant pT dependence (within ±1%), ~99% purity
sample. **Alternative: `Photon_pixelSeed == False`** ("has pixel seed") —
a simpler, more aggressive veto (any pixel hit pattern consistent with a
track, not just "matched electron with no missing inner hits") that
typically has a *higher* rejection of real converted photons too (lower
signal efficiency) — not the paper's choice, kept here only as a fallback
if `electronVeto` behaves unexpectedly in the real cutflow validation.
*Consequential*: yes — this is also the cut we deliberately **invert**
for the Z→ee validation sample (Section 5.2).

**5. Trigger-mimicking / shower-shape cuts.** Photon_r9, Photon_hoe,
Photon_sieie, and the isolation branches (`Photon_pfRelIso03_all`,
`Photon_pfRelIso03_chg`) are all available and documented directly
(`INVENTORY.md` C.1). **Proposed default: do not apply Table 1's exact
numeric thresholds as a separate step.** Rationale: Table 1's cuts were
tuned by CMS specifically against *their* isolation variable definitions
(I_ph/I_tk/I_ch, computed with the *dedicated diphoton vertex*, footnote
in Section 1) — NanoAOD's `pfRelIso03_all`/`_chg` are the *standard* EGM
isolation, computed with the *default* PV, not vertex-matched the same
way. Reusing CMS's exact numeric thresholds on a differently-defined
isolation variable is not obviously correct and was not verified here.
Instead, rely on `Photon_mvaID_WP90` (step 3), which already uses R9,
σ_ηη, H/E, and isolation as MVA *inputs* (standard EGM MVA ID design —
UNVERIFIED that this specific MVA's inputs exactly match Table 1's
variable list, but they are the same general quantities). **This is a
consequential, open design choice** — see "Decisions for review" #3.

**6. Diphoton pair selection.** Take the two `pT`-leading photons that
pass steps 2–5 (not "any pair" — matches the paper's own leading/subleading
convention). Then require the **scaled cuts**: `pT1 > mγγ/3` and
`pT2 > mγγ/4`, computed from the just-formed pair's own mass, matching the
paper's Section 7 wording exactly (quoted in Section 1). *Consequential*:
using flat GeV thresholds instead would distort the low-mass end of the
spectrum, exactly the effect the paper's own text warns about — so the
scaled cuts are not optional.

**7. Mass window.** `100 < mγγ < 180 GeV` (paper's own range, Section 1).

**8. Mass calculation.** From `Photon_pt`/`eta`/`phi` treating photons as
massless (`consts.py`'s own `KNOWN_MASSES["Photons"] = 0.0`, unchanged —
see `INVENTORY.md` D.4). **Energies are NOT re-corrected**: `Photon_eCorr`'s
own doc string, quoted verbatim in `INVENTORY.md` C.1, is "ratio of the
calibrated energy/miniaod energy" — `Photon_pt` is already the calibrated
value; multiplying by `eCorr` again would double-apply the correction.
**This will be checked physically, not just assumed**, using the Z→ee
cross-check in Section 5.2: if energies were being mishandled (e.g.
double-corrected), the reconstructed "Z" peak from electron-veto-inverted
photon pairs would sit measurably off from 91.19 GeV in a data-driven way
that doesn't depend on trusting the doc string alone.

---

## Section 3 — The vertex issue (consequential)

**In plain words.** Each photon's direction is measured from wherever the
detector says the "event happened" (the primary vertex) — a wobble in this
choice tilts both photons' angles very slightly, which shifts the computed
Higgs mass. CMS's real analysis identifies this vertex with a dedicated
algorithm, described in the paper's Section 6, achieving about 81%
"correct" assignments (within 10 mm of the truth). **NanoAOD does not
give us that algorithm's inputs** (per-vertex track-level and conversion
information beyond the single chosen `PV`), so our selection can only use
the *default* vertex NanoAOD already picked — the one with the highest
sum-pT² of associated tracks (`PV_score`'s own doc string, read directly
from the signal file and saved in
`design_checks/vertex_and_pileup_branches.txt`: "main primary vertex
score, i.e. sum pt2 of clustered objects"). The question this
section answers empirically: **how much worse is that default choice?**

**Method.** Read ≤1,000 events from the postVFP ggH signal file
(`design_checks/vertex_study.py`). For each event: find the two
generator-level photons that are direct daughters of the Higgs
(`GenPart_pdgId==22`, mother's `GenPart_pdgId==25`, using
`GenPart_genPartIdxMother`); match each to the closest reconstructed
photon (ΔR < 0.1, unique bijective match); compute the reconstructed
diphoton mass from that truth-matched pair only (not the leading-pT pair,
to remove combinatorics/fakes from the resolution measurement); and split
events by whether the reconstructed **default** vertex (`PV_z`) is within
1 cm of the true generated vertex (`GenVtx_z`) — both branches exist and
were read directly (`GenVtx_x/y/z`: "gen vertex x/y/z"; `PV_x/y/z`: "main
primary vertex position x/y/z coordinate").

**Note on what this measures, precisely.** NanoAOD does not store the
photon supercluster's (x, y, z) position, so it is not possible to
*recompute* the mass under a hypothetical different vertex choice from
these branches. What is measured instead is the resolution actually
present in the *already-stored* `Photon_pt`/`eta`/`phi` — which reflect
whatever vertex CMS's central reconstruction used — split by whether that
vertex happened to be close to the truth. This is the real, relevant
number for this analysis (it is what we are actually stuck with), not a
simulation of a smarter algorithm we can't build.

**Results** (from `design_checks/vertex_study_results.json`, n=1,000
events read, all statistics below are from this sample only):

| | value |
|---|---|
| Fraction of events with default PV within 1 cm of true vertex | **70.0% ± 1.4%** (700/1000) |
| Events with exactly 2 Higgs-daughter photons in `GenPart` | 1000/1000 |
| Events with a successful ΔR<0.1 truth match to 2 distinct reco photons | 761/1000 |
| "Right-vertex" truth-matched pairs (Δz<1cm) | n=545, mean mγγ=122.8 GeV, RMS=7.34 GeV, effective σ₆₈=**2.54 GeV** |
| "Wrong-vertex" truth-matched pairs (Δz≥1cm) | n=216, mean mγγ=123.6 GeV, RMS=6.37 GeV, effective σ₆₈=**2.73 GeV** |

(Effective σ₆₈ = half-width of the smallest interval containing 68.3% of
the mγγ−125 GeV distribution, as specified in the task.)

**Interpretation, stated honestly.** The default (highest-sum-pT²)
vertex is within 1 cm of truth in **70% ± 1.4%** of events — noticeably
*worse* than the paper's dedicated-BDT rate of ~81%, as expected, since
we're using a simpler, generic algorithm. The resolution difference
between right- and wrong-vertex events (2.54 vs. 2.73 GeV effective σ,
right vs. wrong), however, is **small relative to its own statistical
uncertainty** at this sample size (each group's own bootstrap/√(2(n-1))
RMS uncertainty is ~5-7% relative, comparable to the ~7% relative
difference between the two groups) — i.e., **this 1,000-event sample
cannot distinguish "the wrong vertex clearly hurts resolution" from "no
resolvable effect at this vertex-choice granularity"** for this specific,
already-stored `Photon_eta`. Two explanations are plausible and were not
distinguished here: (a) the true effect is real but needs a larger sample
to resolve against the ~2.5 GeV intrinsic photon-energy-resolution floor
that dominates either way, or (b) NanoAOD's stored `Photon_eta` may be
less sensitive to the exact vertex choice than the paper's own
custom-repointed value (plausible, since standard PAT photon
reconstruction may not re-point per-vertex as sensitively as a dedicated
diphoton-specific correction would). **This should be repeated with a
much larger simulated sample before the real analysis relies on any
specific number here** — see Section 8, task list.

**Implication for the signal model.** Even without resolving (a) vs. (b)
above, the presence of *some* wrong-vertex population with a longer tail
(RMS-vs-effective-σ₆₈ ratio is 7.34/2.54 ≈ 2.9 for right-vertex vs.
6.37/2.73 ≈ 2.3 for wrong-vertex — both show non-Gaussian tails beyond the
68% core) supports using a **narrow core plus a wider tail** shape for the
signal model — a double-sided Crystal Ball or a double Gaussian, not a
single Gaussian — with the width(s) fixed from simulation, not left free
in the final fit. This is consistent with the general lesson from the
earlier toy study (branch `study/lr-toy-study`): letting shape parameters
float when they should be fixed from simulation risks absorbing fake
signal.

---

## Section 4 — Simulation treatment

### Normalization

`N_expected = σ × BR × L × (Σ_selected genWeight) / (Σ_all genWeight)`

- σ, BR, L: from `INVENTORY.md` B.4 and A.2 (13 TeV YR4 cross sections,
  BR(H→γγ)=0.00227, L=16.393380531 fb⁻¹ recorded G+H).
- **Σ_selected genWeight**: sum of the per-event `genWeight` branch
  (confirmed present, "generator weight", `INVENTORY.md` C.3) over events
  passing the full selection.
- **Σ_all genWeight**: **verified to exist as a dedicated branch**,
  not something to be summed by re-reading every event. The signal
  file's **`Runs`** tree (a separate, one-row-per-processed-run tree) has
  branch **`genEventSumw`** (`double`, doc string "sum of gen weights"),
  read directly from the ggH file in this task. For a multi-file dataset,
  the true denominator is the **sum of `genEventSumw` across every file's
  `Runs`-tree entry** in that sample — not just one file's value. This
  must be accumulated once per full production run (not per design check,
  which only opened one file of several per sample).
- Because `genWeight` here is not simple ±1 (magnitude ≈21.7, ~0.3%
  negative — `INVENTORY.md` C.3), Σ_all genWeight is *not* well
  approximated by "number of generated events" — it must be read from
  `genEventSumw`, not inferred.

### Pileup

**No dedicated data pileup-profile record exists on the portal**
(`INVENTORY.md` B.5) — confirmed again here, no new search needed.
**Proposed alternative**: reweight simulation to data using the
*reconstructed*-vertex-count distribution, `PV_npvsGood` ("number of good
reconstructed primary vertices: !isFake && ndof>4 && abs(z)<=24 &&
position.Rho<=2" — doc string read directly from the signal file,
`design_checks/vertex_and_pileup_branches.txt`), measured in a **signal-free data
control region** (e.g. the sidebands, `mγγ<115` or `>135`, respecting
blinding) as the "data" side of the reweighting, and the same variable in
signal MC as the "MC" side. **Limitation, stated plainly**: `PV_npvsGood`
is correlated with, but not identical to, the true number of
pileup interactions (`Pileup_nTrueInt`, MC truth only) — reweighting on
the reconstructed proxy instead of the (data-unavailable) truth
quantity is the standard fallback when no official pileup JSON exists,
but it inherits any data/MC mismodeling of the vertex-reconstruction
efficiency itself. **Consequential**: yes — pileup mismodeling shifts
photon isolation and identification efficiency, both selection-critical;
flagged in Section 7.

### Photon energy smearing in simulation

Both `Photon_dEsigmaUp` and `Photon_dEsigmaDown` exist in the signal file
and are systematic-variation branches ("ecal energy smearing value
shifted 1 sigma up" — **quoted verbatim; note both branches carry
identically-worded titles, "up" for both Up and Down, an apparent
copy-paste artifact in the original NanoAOD production, not something
this task can fix**). Their mere existence, by the standard EGM POG
naming convention (a "shifted by 1 sigma" branch implies a nominal,
already-central value it is shifted *from*), **suggests** that the
nominal `Photon_pt` in MC already has the central smearing correction
applied — but this is **UNVERIFIED**: no branch's doc string explicitly
states "this value already includes nominal smearing," and this task did
not independently confirm it (e.g. by comparing MC and data resolution
directly — that comparison is Section 5.2's Z→ee check, and its sample
here is far too small to be conclusive either way, see Section 5).
**Recommended before relying on this**: check CMS's own EGM POG "Scale and
Smearing" documentation directly (not done in this task) before the real
fit assumes MC resolution is already data-like.

### Background simulation

**Explicitly not used for the fit.** Per `INVENTORY.md` B.3, the UL16
DiPhotonJetsBox/GJet/QCD samples cover most, but not all
(GJet/QCD Pt-40toInf double-EM-enriched bins are missing), of the
background phase space, and CMS's own standard practice — matched by this
project's plan — is to take the **background shape from data sidebands**,
not simulation, precisely because simulating the full QCD/γ+jet spectrum
accurately enough for a background *model* (not just a rough cross-check)
is notoriously hard. **Bias studies will be data-driven**: fit several
plausible background function families (e.g. power-law, exponential,
Bernstein-polynomial) to the sideband data, generate pseudo-data from each
fitted family, and re-fit each pseudo-dataset with every family, checking
how much bias a "wrong" background functional form injects into the
signal yield — the same spurious-signal philosophy already validated on
this project's toy study (`study/lr-toy-study`). No background MC
dependency in the default plan.

### Z→ee validation sample

**Found**: recid **35669**,
`/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM`
— 71,839,442 events, 41 files, 91.18 GB, confirmed **postVFP**
(`run_period: ["Run2016G","Run2016H"]`, read directly from the record's
own metadata, same verification method as `INVENTORY.md` B.1).
[record/35669](https://opendata.cern.ch/record/35669).

---

## Section 5 — Validation plan (before unblinding anything)

### 5.1 Cutflow (small-sample, order-of-magnitude only)

From `design_checks/data_cutflow_and_zee.py`, 1,000 raw Run2016G events
(one file), full proposed selection (Section 2, steps 1–7, **except the
golden-JSON run/lumi filter**, not implemented in this quick check — see
caveat below) — counts, not the final analysis efficiency:

| Step | Events surviving |
|---|---|
| 0. All events read | 1000 |
| 1. Pass trigger | 246 |
| 2. ≥2 photons, pT>20 GeV | 206 |
| 3. ≥2 in η acceptance (EB or EE) | 193 |
| 4. ≥2 pass `mvaID_WP90` (and step 3) | 36 |
| 5. ≥2 also pass `electronVeto`; leading pair formed | 11 |
| 6. Pair mass in (100,180) GeV | 6 |
| 6a. — of which in sidebands (<115 or >135) | 3 |
| 6b. — of which **blinded** (115–135), not examined | 3 |

**Caveat, stated plainly**: this is 1,000 *raw* trigger-agnostic events
from one file, not a representative luminosity-weighted sample, and the
golden-JSON filter was not applied (would need to download and parse the
full run/lumisection JSON, out of scope for a quick design check) — real
per-cut efficiencies require the full dataset and are Phase 2.3+'s job.
The purpose here is only to confirm the selection *logic* runs and
produces a sane funnel shape (sharp drop at the ID cut, as expected for a
generic trigger-passing sample with no ID applied yet).

**Signal-side cutflow**: from the same vertex-study read (ggH, 1,000
events): 1000 → (trigger, 59.3% pass, measured separately in this task) →
761 events have a truth-matchable diphoton pair at all (Section 3);
a full step-by-step signal-side cutflow using the *reconstructed*
selection (not just truth-matching) was not separately run in this task
to stay within the file/event budget — recommended as an early Phase 2.3
task (see Section 8).

### 5.2 Z→ee check (electron veto inverted)

**Method**: same photon-collection selection as Section 2, but
`Photon_electronVeto == False` at step 4 (instead of `True`) — exactly
mirroring the tag-and-probe method the reference paper itself uses for
Table 2 (Section 1: "Z→e+e− events" via photon-object reconstruction).
**Expected**: peak at 91.19 GeV (Z boson mass, PDG).

**Acceptance criterion, defined here in advance** (before looking at real
statistics beyond this 1,000-event check): the full-statistics data peak
position must agree with the DY simulation's (recid 35669) peak position
to **within ±1 GeV**, and the two widths (effective σ₆₈) to within **30%
relative** of each other, before trusting the simulation's photon-energy
modeling for anything else. This is a threshold chosen for this design
document, not taken from the reference paper.

**Result from the 1,000-event data-only check** (no DY simulation file
opened yet — that comparison needs both samples run at full statistics,
Phase 2.3+): 21 candidate pairs in 50–130 GeV, mean **96.0 GeV**, RMS 9.1
GeV, effective σ₆₈ ≈ 4.5 GeV. Most values cluster in 88–94 GeV (consistent
with Z→ee), with a handful of outliers up to 126.6 GeV (expected
contamination — this selection has no shower-shape or isolation cut
beyond the inverted electron veto, so genuine non-Z pairs and converted
photons are not rejected). **This 21-event sample is far too small to
test the ±1 GeV / 30% acceptance criterion above** — it is reported only
to show the method produces a plausible, roughly-Z-like clustering, not
as a validation result. The real check needs the full dataset.

### 5.3 Sideband checks

From the same cutflow run: 3 candidate pairs found in the sidebands
(1 below 115 GeV at 105.4 GeV, 2 above 135 GeV, up to 155.7 GeV) — too few
from a single 1,000-event file to say anything about background shape;
this is expected and simply confirms the sideband-only reporting
mechanism itself works and that blinding was respected (3 further
candidates fell in the blinded window and were correctly never examined).

### 5.4 Expected signal yield and Asimov significance

Using `INVENTORY.md` B.4's produced-event numbers (≈2,051 H→γγ decays
produced in Run2016G+H before selection, dominated by ggH at ≈1,808) and
a rough overall efficiency estimate: preselection-level efficiencies in
the reference paper's own Table 2 range from ~50% to ~95% per photon
depending on category, so a *very rough* two-photon combined efficiency
(preselection × ID × trigger, ignoring vertex/categorization losses) of
order 30–50% would be a reasonable starting assumption for ggH — **this
number is NOT computed or verified in this task**, it is flagged
explicitly as **the single most important number for Phase 2.3 to
actually measure** (via the real, full-statistics cutflow) before an
Asimov significance can be quoted honestly. Computing the Asimov
significance itself is deferred to Phase 4.1 as instructed, using the
already-validated LR tools (`study/atlas-hgg-lr-reproduction`, commit
`290ca09`) once a real efficiency number and a real (not sideband-only)
background shape estimate exist.

---

## Section 6 — Pipeline changes (engineering design)

General pattern used by every capability below: NanoAOD's existing
**`EventIds`** mechanism (`run`/`luminosityBlock`/`event`, declared per-
schema as `event_id_branches`) is the precedent to extend, not a new
concept. It already threads a *scalar-per-event* (not per-particle)
category through the whole read path, bypassing the
"must have pt+eta+phi" gate that every physics-object category is
otherwise required to pass:

- **Declaration**: `services/parsing/schemas.py:45-49`
  (`NANOAOD_EVENT_ID_BRANCHES`) and `:129`
  (`"event_id_branches": NANOAOD_EVENT_ID_BRANCHES.copy()`, inside the
  `"cms-nanoaod"` schema entry).
- **Extraction**: `services/parsing/file_parser.py:299-303`
  (`_extract_branches_by_schema`, `if event_id_branches: obj_branches["EventIds"] = ...`).
- **Accessibility gate bypass**: `file_parser.py:519-521`
  (`... or obj_name in ("DirectObjects", "EventIds")`).
- **Re-attachment as top-level scalar fields**: `file_parser.py:125-145`
  (`event_id_fields = obj_events.pop("EventIds", None)` ... `zipped = ak.with_field(...)`).
- **Selection hook point**: `orchestration/handlers/parsing_handler.py:277-284`
  — where `apply_parsing_event_selection` is called on the already-zipped,
  already-scalar-field-carrying `batch.events`.

### 6.1 Validated-runs (golden JSON) filter

- **Files/functions**: new function in `services/parsing/event_selection.py`
  (alongside `apply_parsing_event_selection`, `event_selection.py:58`),
  e.g. `apply_validated_runs_filter(events, golden_json)` — operates on
  the already-present top-level `run`/`luminosityBlock` scalar fields
  (proof they're already there: `NANOAOD_EVENT_ID_BRANCHES`,
  `schemas.py:45-49`). Called from
  `orchestration/handlers/parsing_handler.py:277-284`, before or fused
  with the existing `apply_parsing_event_selection` call.
- **New config key**, example:
  ```yaml
  parsing_task_config:
    validated_runs_json: null   # e.g. a local path or portal URL to
                                 # Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt
  ```
- **Default behaviour when absent**: `null` (or key missing) → filter is a
  no-op, exact existing behaviour preserved for every current config.
- **ATLAS path unaffected**: ATLAS schemas (`"2024r-pp"`, etc.) do not
  declare `event_id_branches` at all (`schemas.py:106-108`, no such key),
  so `run`/`luminosityBlock` are never attached as scalar fields for
  ATLAS releases in the first place — the new filter function would check
  for the fields' presence and no-op if absent, provably never touching
  ATLAS. Proof by test: run the existing ATLAS regression config with the
  new key present but pointing at a real JSON — assert byte-identical
  output to today (ATLAS has no run/luminosityBlock fields to filter on).
- **Unit safety**: run/lumisection numbers are plain integers, no
  GeV/MeV interaction at all.
- **Tests**: (a) unit test with a synthetic 3-event array (`run`,
  `luminosityBlock`) against a small in-memory JSON, covering "certified",
  "not certified", "certified but different run" cases; (b) regression
  test: existing CMS config with `validated_runs_json: null` produces
  identical parsed output to before this change, byte-for-byte.
- **Size**: **Medium** (new filter concept, new config surface, but a
  well-defined, self-contained lookup — no interaction with kinematic
  cuts or particle counts).
- **Dependency**: none on the other four; can be built first.

### 6.2 HLT trigger requirement

- **Files/functions**: extend the `EventIds`-style pattern with a
  sibling, e.g. `NANOAOD_TRIGGER_BRANCHES` (schema-declared, per-config
  list of one or more `HLT_*` names) in `schemas.py`, read through the
  same `_extract_branches_by_schema` path (`file_parser.py:299-303`
  pattern) and re-attached as scalar boolean fields
  (`file_parser.py:125-145` pattern, generalized to more than one scalar
  category). New cut applied alongside golden-JSON filtering
  in `event_selection.py`, e.g. `apply_trigger_requirement(events, required_triggers)`.
- **New config key**, example:
  ```yaml
  parsing_task_config:
    required_triggers: []       # e.g. ["HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90"]
    require_triggers_in_mc: true
  ```
- **Default behaviour when absent**: empty list → no trigger requirement,
  exact existing behaviour preserved.
- **ATLAS path unaffected**: same argument as 6.1 — ATLAS schemas
  declare no trigger branches, so the new schema key
  (`"trigger_branches": []`, analogous to `event_id_branches`) defaults to
  absent for every non-CMS schema; proof is the same "field never exists
  to filter on" argument plus a byte-identical regression test.
- **Unit safety**: booleans, no GeV/MeV interaction.
- **Tests**: unit test with a synthetic array having the HLT branch
  True/False in different events; regression test as in 6.1.
- **Size**: **Small** — the mechanism to extend already exists
  (`EventIds`), this is mostly config plumbing and one new schema list.
- **Dependency**: shares its underlying "add another named scalar
  category" mechanism with 6.1 and 6.4 (pileup/weights) — building a
  single generalized "scalar event fields" mechanism once, used by
  golden-JSON run/LS, trigger bits, and weights/pileup alike, is more
  efficient than three separate ad hoc extensions (see Section 8's
  ordering).

### 6.3 Additional `Photon_*` fields

- **Files/functions**: `services/parsing/schemas.py:121-127`, the
  `"cms-nanoaod"` schema's `"objects"]["Photons"]` list — currently
  `["pt", "eta", "phi", "mass"]` (`INVENTORY.md` D.1). Extend to include
  (at minimum) `eCorr, cutBased, mvaID, mvaID_WP80, mvaID_WP90,
  electronVeto, pixelSeed, r9, sieie, hoe, isScEtaEB, isScEtaEE,
  pfRelIso03_all, pfRelIso03_chg` — all confirmed present and documented
  (`INVENTORY.md` C.1). No new config key needed for *reading* them (the
  schema is not currently exposed as user-configurable per-field); the
  existing `kinematic_cuts.photons` YAML block
  (`event_selection.py:16-23`, `normalize_yaml_kinematic_cuts`) already
  supports adding `rel_isolation_max` per object, so cutting on the
  isolation fields needs no new code, only new field availability.
  **A genuinely new capability is needed for the boolean fields**
  (`electronVeto`, `mvaID_WP90`, `isScEtaEB`/`EE`) and the η-*gap*-exclusion
  pattern — `filter_events_by_kinematics`
  (`services/calculations/physics_calcs.py:241+`) only supports a single
  contiguous `{min, max}` range per field, not "boolean must be True" or
  "exclude this inner sub-range." Proposed: a small, generic
  `bool_cuts: {photons: {electronVeto: true, mvaID_WP90: true}}` YAML
  block, and an `eta_exclude: {min, max}` option alongside the existing
  `eta: {min, max}`.
- **Default behaviour when absent**: no `bool_cuts`/`eta_exclude` keys →
  no such cuts applied, exact existing behaviour preserved; the *extra*
  Photon_* fields being read but unused changes memory/IO slightly but no
  analysis output, for every config that doesn't reference the new
  fields.
- **ATLAS path unaffected**: this change is entirely inside the
  `"cms-nanoaod"` schema entry; ATLAS schema entries are untouched.
  Proof: diff the ATLAS schema dict before/after — zero lines changed.
- **Unit safety**: none of these are momentum/energy fields, no
  GeV/MeV interaction — except `Photon_pt`/`mass` themselves, already
  correctly handled (`INVENTORY.md` D.4, unchanged by this proposal).
- **Tests**: unit tests for `bool_cuts` and `eta_exclude` on a synthetic
  photon array (values inside/outside the gap, True/False flags);
  regression test with the extended field list but no new cuts configured
  — must reproduce today's parsed Photon pt/eta/phi/mass columns exactly.
- **Size**: **Small** for the field-list extension itself; **Small–Medium**
  for the new `bool_cuts`/`eta_exclude` cut types in
  `physics_calcs.filter_events_by_kinematics`.
- **Dependency**: independent of 6.1/6.2/6.4.

### 6.4 Simulation weights and pileup info

- **Files/functions**: same generalized "scalar event fields" mechanism
  as 6.1/6.2 — add `genWeight` (per-event) as a new scalar category, and
  `Pileup_nTrueInt` (MC) / `PV_npvsGood` (data+MC) similarly.
  **`genEventSumw`** is different in kind: it lives in the **`Runs`** tree,
  not `Events` (confirmed directly, Section 4) — one value per input file,
  not per event. This needs a *separate* small aggregation step (sum
  across files in a sample), most naturally done once per dataset at the
  orchestration level (e.g. alongside `orchestration/handlers/fetch_metadata_handler.py`,
  which already resolves per-record file lists and MC/data separation —
  see `INVENTORY.md`/this doc's Section 4 discussion of `parse_mc`), not
  inside `FileParser`'s per-file, per-event logic.
- **New config keys**, example:
  ```yaml
  parsing_task_config:
    read_event_weights: false   # genWeight (Events tree, per event)
    read_pileup_info: false     # Pileup_nTrueInt (MC) / PV_npvsGood (data+MC)
  fetch_metadata_task_config:
    read_gen_event_sumw: false  # genEventSumw (Runs tree, per file; summed per sample)
  ```
- **Default behaviour when absent**: `false` → no weight/pileup columns
  attached, exact existing behaviour preserved; every currently-passing
  CMS config (bjet test, m0m1j0, zpeak test, etc.) does not set these
  keys and would see zero change.
- **ATLAS path unaffected**: `genWeight`/`Pileup_nTrueInt`/`genEventSumw`
  are CMS-NanoAOD-specific branch names, declared only inside the
  `"cms-nanoaod"` schema entry's new lists; ATLAS PHYSLITE has its own,
  different MC-weight branches (not investigated in this task — **out of
  scope**, flagged so nobody assumes this design covers ATLAS MC weights
  too).
- **Unit safety**: `genWeight` and `Pileup_nTrueInt`/`PV_npvsGood` are not
  momentum/energy quantities — no interaction with
  `schema_needs_mev_to_gev_conversion` (`schemas.py:604-622`) at all;
  this must be double-checked in code review to ensure nobody
  accidentally routes a weight value through the mass-scaling code path.
- **Tests**: unit test that `genWeight` survives a full parse→zip round
  trip unmodified (including its sign, given ~0.3% of events have
  negative weights — `INVENTORY.md` C.3); a `genEventSumw`-aggregation
  unit test with 2–3 synthetic per-file values; regression test with the
  keys `false`/absent, byte-identical to current output.
- **Size**: **Medium** (two different tree-scopes — `Events` per-event vs.
  `Runs` per-file — is real added complexity, not just "read one more
  branch").
- **Dependency**: benefits from the same generalized scalar-field
  mechanism as 6.1/6.2 for the `Events`-tree part; the `Runs`-tree
  (`genEventSumw`) part is independent and can be built separately.

### 6.5 Barrel–endcap gap flag

Already covered as part of 6.3 (`isScEtaEB`/`isScEtaEE` are two of the
extra `Photon_*` fields, and the `eta_exclude` cut type is the mechanism
that uses them). Listed separately here only because the task asked for
it as its own line item — **no additional file/function beyond 6.3**.

### Analysis-folder output format and scaling

**Per-event output for selected diphoton events** (in
`studies/hgg_cms/`, not shared code): one row per selected event —
`run, luminosityBlock, event, mgg, pt1, eta1, phi1, r9_1, mvaID_1, pt2,
eta2, phi2, r9_2, mvaID_2, PV_npvsGood, genWeight (MC only),
Pileup_nTrueInt (MC only), source_record`. **File format**: the pipeline
already writes intermediate per-object arrays as `.npy`/sqlite-shard
files consumed by `services/pipelines/histograms_pipeline.py` and
`services/storage/sqlite_shards.py` (seen in the histogram-pipeline
import, not fully re-read in this design pass); the natural choice is to
reuse whichever of those two the shared "mass-calculation" stage already
emits, so the fine-binned histogram step (below) can reuse the same
merge/concatenate machinery `histograms_pipeline.py` already has, rather
than inventing a third storage format. **This specific choice should be
confirmed against `services/pipelines/im_pipeline.py`'s (the
mass-calculation pipeline) actual output format in Phase 2.3** — not
re-read line-by-line in this design pass, flagged as a small follow-up
check, not a design risk.

**Scale**: 164,185,704 input data events (`INVENTORY.md` A.1) plus signal
and background MC (`INVENTORY.md` B.1–B.3, totaling several hundred
million more events across all background samples, dominated by
`GJet_Pt-15To6000-Flat` and `DiPhotonJetsBox`). **CPU-time estimate, from
this task's own timing**: `design_checks/data_cutflow_and_zee.py` read
1,000 events (all ~1370 branches available, but only ~10 branches
actually requested) via HTTPS in well under a minute per file, dominated
by network latency for the remote read, not local CPU — **not
representative of a real batch job's per-event cost**, which is
lower once the client reads many events per request in one file (as the
real pipeline's own batching, `file_parser.py:539-546`, already does) but
scales with the number of files and total events regardless. **No
extrapolated total-runtime number is given here** — that would need a
timed run on a representative multi-file batch, which is a cluster-scale
activity explicitly out of scope for this design task. **Output size**:
the per-event output above (roughly 15 float/int columns) is a few orders
of magnitude smaller than the input NanoAOD files (which carry ~1,370
branches per event, almost all unused by this analysis) — a rough
back-of-envelope (15 columns × 8 bytes × a few million surviving events,
after the ~99%+ rejection seen even in the crude 1,000-event cutflow
above) suggests **tens of MB, not GB**, for the full selected-event
output — not independently measured, flagged as an estimate only.

**Processing plan**: (1) a single local NanoAOD file end-to-end through
the (to-be-built) selection, verifying the per-event output schema and
row count against a hand-checked cutflow on that same file; (2) a small
multi-file batch (a handful of files from one record) to check the
merge/concatenation step and confirm `genEventSumw` aggregation across
files works; (3) only then the full-dataset cluster run — not attempted
in this task.

---

## Update — physics checks (2026-09-15)

Three follow-up physics checks were run after design review, to replace
assumptions with measurements. Scripts and JSON results are in
`studies/hgg_cms/physics_checks/`; every file URL and event range read is
recorded in `physics_checks/file_list.py`. Files read: **1** postVFP ggH
signal file (50,000 events) and **2** DoubleEG data files (25,000 events
each from Run2016G and Run2016H, 50,000 total) — within the task's
5-file/50,000-event limits for each sample. **Blinding was respected
throughout**: no data diphoton mass in [115, 135] GeV was ever computed
and kept; only counts of candidates falling there were recorded
(`check_c_results.json`, `c2_data_sidebands_blinded_and_zee`).

Selection used in all three checks: the "v1 + trigger-mimicking (TM)"
photon preselection defined in `physics_checks/common.py`'s module
docstring — v1 (pT>20 GeV, η acceptance, `electronVeto`, `mvaID_WP90`)
plus Table 1's shower-shape/isolation cuts approximated with NanoAOD's
`Photon_r9`/`hoe`/`sieie`/`pfRelIso03_all`/`pfRelIso03_chg` branches (doc
strings quoted and confirmed "full5x5" in
`physics_checks/branch_docstrings.txt`). **Table 1's numeric values were
re-verified against the paper's own extracted text before use**
(`physics_checks/table1_verification.txt`) — exact match, no discrepancy.

### Check A — is simulated photon energy already smeared?

**Yes — confirmed by two independent methods, plus an explicit primary
source.**

1. **`Photon_eCorr` distribution** (`plots_A2_eCorr_mc_vs_data.png`,
   `check_a_results.json`): for pT>20 GeV photons, MC's eCorr has RMS
   **1.19%**, more than double data's **0.55%**, with MC's mean
   (1.000060) essentially exactly 1 — while data's mean is offset
   (+0.51% barrel, +0.77% endcap), consistent with data getting a *scale*
   correction (a real, deterministic shift) and MC getting a *smearing*
   correction (a zero-mean, broadening, stochastic term). This matches
   this document's own pre-set rule exactly: RMS ≥0.3% and |mean−1|≤0.3%
   → **"MC smearing appears applied."**
2. **Direct response check** (`plots_A3_response_mc.png`): for photons
   truth-matched to Higgs-daughter gen photons, the corrected
   `Photon_pt`/`GenPart_pt` response is measurably **wider** than the
   pre-correction (`pt/eCorr`) response, in every category — effective
   σ₆₈ barrel-high-R9: 1.26%→1.68%; barrel-other: 2.71%→3.15%; endcap:
   2.84%→3.26%. The correction *broadens* MC resolution, exactly what a
   smearing correction (not a pure recalibration) does by construction.
3. **Primary source, found and quoted**
   (`physics_checks/check_a_cms_documentation_search.txt`): the CMS
   WorkBookNanoAOD TWiki states explicitly, "Up to NanoAOD10, residual
   energy scale and resolution corrections are applied to the stored
   photons to match the data" — UL2016 NanoAODv9 (this analysis) is
   within that "up to NanoAOD10" range.
   [twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD)

### Check B — vertex reference and real mass resolution

**B1 — which point are stored photon directions measured from?**
(`plots_B1_regression_barrel.png`, `plots_B1_regression_endcap.png`,
`check_b_results.json`). Regressing Δcotθ·R_SC against `GenVtx_z`
(hypothesis i, reference = detector origin) vs. against
`GenVtx_z − PV_z` (hypothesis ii, reference = the default primary
vertex): **hypothesis (ii) wins clearly and unambiguously.**

| | slope | R² | residual corr. with PV_z |
|---|---|---|---|
| (i) origin, barrel | 0.360±0.004 | 0.19 | −0.77 (large — model doesn't fit) |
| **(ii) default PV, barrel** | **0.935±0.001** | **0.981** | **0.038 (~0, model fits)** |
| (i) origin, endcap | 0.385±0.008 | 0.18 | — |
| **(ii) default PV, endcap** | **0.961±0.003** | **0.890** | — |

The origin hypothesis is visibly rejected in the scatter plot itself
(huge scatter, wrong slope); the default-PV hypothesis produces a tight,
nearly-diagonal line. The slope is close to but not exactly 1
(0.94–0.96) — attributed to the simplified fixed-radius geometric model
(`R_SC`=129cm assumed for every barrel photon), not to a wrong reference
point, given how cleanly hypothesis (ii) otherwise fits. **Verdict:
NanoAOD's stored `Photon_eta`/`phi` are already computed relative to the
default primary vertex (`PV_z`), not the detector origin.** No beamspot
position branch exists in the file, so hypothesis (iii) was not testable
(noted, not silently skipped).

**Consequence for re-aiming (revises Section 7 #4 below)**: since
`Photon_eta` already uses `PV_z`, "re-aiming to `PV_z`" is a **no-op** —
confirmed numerically in B2 (option (a) "stored" and option (b) "re-aimed
to PV_z" agree to 6+ significant figures in every category, as they must
if B1's finding is correct). Only re-aiming to the *true* vertex (option
(c), unreachable in a real analysis) can do anything, and it does very
little inclusively (see below) — meaning **re-aiming would not help our
selection**, because NanoAOD already does the only re-aiming we have the
information to do.

**B2 — mass resolution after the full selection, truth-matched photons**
(`plots_B2_mass_abc_inclusive.png`, `plots_B2_mass_abc_by_category.png`,
n=19,770 truth-matched events out of 19,792 passing the full selection —
trigger, v1+TM, scaled cuts, 100–180 GeV):

| category | (a) stored / (b) re-aimed to PV_z | (c) re-aimed to true vertex (ideal) |
|---|---|---|
| inclusive | σ₆₈ = 2.046 ± 0.016 GeV | σ₆₈ = 1.984 ± 0.015 GeV |
| both barrel | σ₆₈ = 1.792 ± 0.017 GeV | σ₆₈ = 1.757 ± 0.017 GeV |
| ≥1 endcap | σ₆₈ = 2.556 ± 0.032 GeV | σ₆₈ = 2.458 ± 0.030 GeV |

Peak (mode) is 124.75–125.25 GeV in every case, consistent with 125 GeV
within the histogram's 0.5 GeV binning. **Sensitivity check** (R_EFF
135cm/Z_EFF 320cm instead of 129cm/314cm, `b2_systematic_geometry` in the
JSON): σ₆₈ changes by <0.2% relative — the geometric-model choice barely
matters within the stated range.

**Split by vertex quality** (stored value only): **66.1%** of these
full-selection events have `|PV_z − GenVtx_z| < 1 cm` (13,069/19,770;
statistical uncertainty ≈0.3%, superseding the earlier
761-event/no-selection Section 3 estimate of 70.0%±1.4%, which review
correctly flagged as unrepresentative). For these: **σ₆₈ = 1.787 ± 0.017
GeV**; for the other 33.9% (`|Δz|≥1cm`): **σ₆₈ = 2.601 ± 0.029 GeV** — a
large, now statistically clear difference (Section 3's original small
sample could not resolve this; with proper photon selection and 25× the
statistics, it is now unambiguous). **The vertex absolutely does matter**
for events where the default vertex happens to be wrong; it just cannot
be fixed by re-aiming (see above) since NanoAOD already uses the best
information available to it.

**Plain leading-pair check (no truth-matching, "what the analysis will
actually see")**: σ₆₈ = 2.049 ± 0.016 GeV, n=19,792 — statistically
indistinguishable from the truth-matched inclusive number above,
confirming truth-matching did not bias the resolution estimate.

**Plain-language conclusion**: the vertex matters — events with a
mismodeled vertex have ~45% worse mass resolution than events with a
good one — but NanoAOD's stored photon directions already use the best
vertex we have (`PV_z`), so there is nothing to gain by "re-aiming"
within this design's means. The only way to do better is a dedicated
vertex-finding algorithm like the paper's own (Section 3, Section 1),
which is out of reach with NanoAOD alone. This directly informs the
signal-model choice (Section 7 #8): the ~34% wrong-vertex population with
its ~45%-wider core is the source of the tail that motivates a
narrow-core-plus-tail shape, not a symmetric single Gaussian.

### Check C — effect of trigger-mimicking (TM) cuts

**C1 — signal MC** (`plots_C1_hlt_pass_fraction.png`,
`check_c_results.json`, n=50,000 ggH events):

| | offline efficiency (of all events) | HLT-pass fraction (of offline-selected) |
|---|---|---|
| without TM | 43.0% ± 0.2% | 93.9% ± 0.16% |
| **with TM** | **40.0% ± 0.2%** | **99.0% ± 0.07%** |
| without TM, barrel-barrel | 27.5% ± 0.2% | 96.5% ± 0.16% |
| with TM, barrel-barrel | 26.2% ± 0.2% | 99.5% ± 0.06% |
| without TM, other | 15.5% ± 0.2% | 89.4% ± 0.35% |
| with TM, other | 13.8% ± 0.2% | 98.1% ± 0.16% |

**Signal efficiency cost of TM: 3.0 percentage points absolute (43.0%→
40.0%), a 7.0% relative reduction.** In exchange, the HLT pass fraction
among offline-selected events rises from 93.9% to 99.0% overall, and even
the worst category ("other", i.e. at least one endcap photon) rises from
89.4% to 98.1% — confirming the review's stated expectation exactly:
"offline cuts tighter than the trigger make the trigger nearly fully
efficient."

**C2 — data** (`plots_C2_zpeak_with_without_TM.png`): of 50,000 raw
trigger-passing events, full-selection candidates in 100–180 GeV drop
from 97 (without TM: 74 sideband + 23 blinded) to 92 (with TM: 70
sideband + 22 blinded) — a small (~5%) relative loss, consistent with
C1's 7% MC estimate given small-number statistics. **Z control region**
(electron-veto-inverted, 70–110 GeV): 661 events without TM vs. 651 with
TM (−1.5%) — peak **91.5 GeV in both cases** (matches PDG 91.19 GeV
closely), effective σ₆₈ 2.430 GeV (without TM) vs. 2.423 GeV (with TM) —
**statistically indistinguishable**. TM cuts cost almost nothing in this
control region while (per C1) buying a large trigger-efficiency
improvement in simulation.

**C3 — orthogonal trigger cross-check (data, rough estimate, as
labeled)**: using `HLT_Ele27_WPTight_Gsf` (a single-electron trigger,
confirmed present in both data files, independent of the diphoton path)
plus the Zee (electron-veto-inverted) selection: 34.8%±1.1% of these
events also pass the diphoton HLT bit without TM, 39.5%±1.2% with TM — a
real but much smaller increase than C1's MC-based near-100% result.
**This is not a contradiction**: this cross-check uses real electrons
selected by an electron-specific trigger with its own, different
kinematic/tracking requirements, not photon-like ECAL objects at the
diphoton trigger's own thresholds — so it is expected to look different
from C1's same-object-type measurement, and is reported here only as a
plausibility check, exactly as the task specified.

**Plain-language conclusion**: trigger-mimicking cuts cost about 7% of
signal efficiency, and in exchange make the trigger almost always fire
in simulation (93.9%→99.0%) — closing the gap the review flagged
(requiring the HLT bit in MC "without trigger efficiency corrections").
In real data, the same cuts cost noticeably less (a few percent) and
leave the Z-peak position and width unchanged. **Decision: apply the TM
cuts** (Section 7 #3, updated below).

---

## Review corrections to the physics-check update (2026-09-15)

A second review of the physics-check "Update" section above found three
issues, addressed here rather than by rewriting that section:

**1. Vertex (Check B) — the close/far width difference is mostly not
caused by the vertex choice.** Check B reported effective σ₆₈ = 1.79 GeV
for events with `|PV_z−GenVtx_z|<1cm` vs. 2.60 GeV for the rest, and
separately that re-aiming *every* event to the true generated vertex
(the unreachable ideal) only improves the *inclusive* resolution from
2.05 to 1.98 GeV (~3%). These two numbers are in tension if read as
"the vertex causes the width difference": if mismodeling the vertex by
≥1cm were itself responsible for a 1.79→2.60 GeV degradation, fixing it
for the ~34% of events that have it should visibly move the inclusive
number by much more than 3%. It doesn't. **Correct reading**: the
close/far split is mostly a *correlation*, not a *cause* — events with a
poorly-reconstructed vertex are disproportionately the same events with
other resolution-degrading properties (e.g. more likely to have an
endcap photon, lower-R9 photons, etc.), and it is mostly those other
properties, not the vertex mismodeling itself, driving the width
difference between the two groups. The re-aiming test (which isolates
the vertex's own causal effect by changing *only* the assumed vertex
position, holding everything else fixed) is the more reliable measure of
that causal effect, and it says the vertex itself is a **minor**
contributor (~3%) to the resolution, not the dominant one the close/far
split alone would suggest. **B1 is unaffected by this correction** and
remains a clean, separate result: stored photon directions are
referenced to the default primary vertex `PV_z`, not the detector
origin (barrel regression slope 0.935±0.001, R²=0.981, vs. slope
0.360±0.004, R²=0.19 for the origin hypothesis) — the slope's deviation
from exactly 1 is most likely the fixed-effective-radius (`R_SC`=129cm)
geometric approximation, not a wrong reference point, given how cleanly
the PV hypothesis otherwise fits (tight residuals, near-zero residual
correlation with `PV_z`; see the scatter plots). **Conclusion, corrected:
use the stored photon directions (no re-aiming) — not because re-aiming
to `PV_z` would be a no-op (it would, but that's now a secondary point),
but because the vertex has only a minor (~3%) effect on the achievable
resolution in the first place.**

**2. Check C3 is invalid as a trigger-efficiency measurement.** The
diphoton trigger, `HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90`,
requires a diphoton mass above **~90 GeV online** (that's what the
trigger name's own "Mass90" encodes). Check C3 selected Z→e⁺e⁻-like pairs
in the 70–110 GeV window and measured what fraction *also* passed this
trigger — but pairs below ~90 GeV are then failing the trigger's own
online mass requirement, not (only) because of any inefficiency in the
rest of the trigger's photon-identification logic. C3's reported
34.8%/39.5% therefore mixes a real efficiency effect with an artifact of
comparing against a mass region the trigger was never going to fully
accept. **This does not change Check C1's own conclusion** (C1 never
imposed any Z-mass-like window; it used the full, unbiased offline
selection and its own scaled-pT/100–180 GeV cuts), so the "apply TM
cuts" decision (Section 7 #3) stands on C1 alone. C3's numbers are
retracted as a trigger-efficiency estimate and should be read only as
"these two cross-checks are not directly comparable," not as evidence
against C1.

**Added to Section 8 validation task 7**: measure the diphoton-HLT pass
fraction in data using a tag-and-probe method that avoids the online
mass cut — e.g. select Z→e⁺e⁻-like pairs via the orthogonal
`HLT_Ele27_WPTight_Gsf` single-electron trigger, restricted to *offline*
m_ee above ~95–100 GeV (safely clear of the "Mass90" threshold, unlike
C3's 70–110 GeV window which straddles it), and compare the resulting
diphoton-HLT pass fraction between data and DY simulation (recid 35669).
This is a new item in the task 7 acceptance criteria below, not yet run.

**3. Rough scale estimate (labelled as such).** Combining
`INVENTORY.md` B.4's ≈2,051 produced H→γγ events (Run2016G+H, all
production modes) with Check C1's ≈40% ggH offline selection efficiency
(without TM cuts; 40.0% with TM cuts, C1 above) gives a **rough estimate
of ≈800 selected Higgs events**, dominated by ggH, **before any
per-production-mode efficiency is actually measured** (VBF/WH/ZH/ttH
have different kinematics and were not separately checked) and before
the trigger-mimicking efficiency cost is folded in mode-by-mode. This is
an order-of-magnitude sanity number for planning purposes only, not a
prediction to be quoted elsewhere without redoing it per production
mode.

---

## Section 7 — Decisions for review

1. **Photon ID working point default: `mvaID_WP90`**, not `WP80` or
   cut-based. *Consequential.* Alternatives and trade-offs in Section 2,
   step 3.
2. **Electron veto default: `Photon_electronVeto`**, not `pixelSeed`.
   *Consequential.* Section 2, step 4.
3. **Trigger-mimicking shower-shape cuts (Table 1's exact numeric
   thresholds) are NOT applied as a separate step** in the default v1 —
   relying on `mvaID_WP90` to cover the same physics instead. *Open,
   consequential* — flagged as the least-settled choice in this document;
   revisit once the analysis-level isolation/shower-shape variables can
   be directly compared to Table 1's definitions (needs care about the
   vertex-dependence of CMS's own I_ph/I_tk/I_ch, Section 2 step 5).
   **Original: not applied. Updated (2026-09-15, "Update — physics
   checks" above): APPLY the trigger-mimicking (TM) cuts** — H/E<0.08,
   the barrel/endcap R9-or-shower-shape-and-isolation cuts, and the
   combined charged-isolation requirement, using the NanoAOD proxies
   defined in `physics_checks/common.py` (I_ch≈`pfRelIso03_chg`×pT,
   I_ph≈(`pfRelIso03_all`−`pfRelIso03_chg`)×pT, I_tk≈I_ch — explicitly
   NOT CMS's exact vertex-dependent definitions). Reason: without TM
   cuts, requiring the HLT bit in MC (Section 2 step 1) with no trigger
   efficiency correction leaves a real gap between offline and trigger
   selections (93.9% HLT-pass among offline-selected events, worse in
   categories with an endcap photon: 89.4%); WITH TM cuts this rises to
   99.0% (98.1% for the endcap category) — measured directly in Check C,
   at a cost of 3.0 percentage points (7.0% relative) of signal
   efficiency. Data-side cost is smaller (~5% of candidates) and the
   Z→ee peak position/width are unaffected by the cuts. See "Update —
   physics checks" above for full numbers and plots.
4. **Vertex: use NanoAOD's default (highest sum-pT²) `PV`, no
   custom re-pointing.** *Consequential*, quantified in Section 3: ~70%
   correct-vertex rate (vs. paper's ~81%), with an inconclusive
   (small-sample) resolution penalty that should be re-measured at scale.
   **Original: inconclusive resolution penalty (Section 3, no photon
   selection applied, dominated by poorly-measured photons — mean 122.8
   GeV, RMS 7 GeV, flagged by review as unrepresentative). Updated
   (2026-09-15): confirmed with proper selection and 25× the statistics
   (Check B, n=19,770). (i) NanoAOD's stored photon directions ARE
   already computed relative to the default `PV_z`, not the detector
   origin — regression slope 0.935–0.961 with R²=0.89–0.98 vs. slope
   0.36–0.39 with R²≈0.18 for the origin hypothesis (`check_b_results.json`,
   `plots_B1_regression_*.png`). This means "re-aiming to PV_z" is a
   no-op — it is already done. (ii) The vertex DOES matter: events with
   `|PV_z−GenVtx_z|<1cm` (66.1%±0.3% of selected events, an updated,
   more precise number than Section 3's original 70.0%±1.4%) have
   σ₆₈=1.79 GeV vs. 2.60 GeV for the rest — a real, now statistically
   clear ~45% resolution penalty. (iii) There is nothing this design can
   do about it: re-aiming to the true vertex (only possible with
   generator truth, unreachable in a real analysis) improves the
   *inclusive* resolution by just 2.046→1.984 GeV (3%), because NanoAOD
   already uses the best available (default) vertex. Decision UNCHANGED
   in effect (still no custom re-pointing — there is nothing to re-point
   TO without CMS's own dedicated vertex algorithm), but now backed by a
   real measurement instead of an inconclusive one, and directly informs
   Section 7 #8's signal-model shape.
   **Correction (2026-09-15, see "Review corrections to the physics-check
   update" above): point (ii)'s "real, now statistically clear ~45%
   resolution penalty" is mostly a CORRELATION, not the vertex's own
   causal effect — the re-aiming test in point (iii) (2.046→1.984 GeV,
   ~3%) isolates the vertex's actual causal contribution by changing only
   the assumed vertex position, and it is minor, not ~45%. Point (i) is
   unaffected and remains the load-bearing result: stored directions
   already use `PV_z`, so there is nothing to re-aim to. Net effect on
   the decision: unchanged (still no custom re-pointing), but for a
   different reason than originally stated — not because "re-aiming
   would be a no-op that wouldn't matter anyway" (true but secondary),
   rather because the vertex's own effect on resolution is small to
   begin with.**
5. **Combined `VHToGG` sample vs. separate `WplusH`/`WminusH`/`ZH_HToGG`
   samples** (`INVENTORY.md` B.1): default is the **separate** samples
   (matches how cross sections are quoted per-mode); do not mix with the
   combined sample. *Consequential* if gotten wrong (double-counting).
6. **Pileup reweighting via `PV_npvsGood`** in a data control region,
   not a true pileup profile (none exists on the portal). *Consequential*
   for photon ID/isolation efficiency modeling.
7. **MC photon-energy smearing already applied to nominal `Photon_pt`**:
   plausible from branch-naming convention, **UNVERIFIED** by direct
   documentation. *Consequential* if wrong — would mean signal MC width
   is too narrow relative to data.
   **Original: UNVERIFIED. Updated (2026-09-15): CONFIRMED, by three
   independent pieces of evidence (Check A above) — (i) MC `Photon_eCorr`
   RMS (1.19%) is more than double data's (0.55%) with a mean consistent
   with exactly 1, the signature of a zero-mean broadening (smearing)
   correction rather than a deterministic scale shift; (ii) the
   truth-matched MC response distribution is measurably WIDER after
   `Photon_eCorr` is applied than before, in every photon category
   (e.g. barrel high-R9 effective σ₆₈: 1.26%→1.68%); (iii) an explicit
   primary-source statement, CMS's own WorkBookNanoAOD TWiki: "Up to
   NanoAOD10, residual energy scale and resolution corrections are
   applied to the stored photons to match the data" — this analysis uses
   NanoAODv9, within that range. No longer consequential as an open risk
   — resolved.
8. **Signal model shape: narrow core + wide tail** (double Gaussian or
   Crystal Ball), width fixed from simulation. *Consequential*,
   supported by Section 3's tail evidence, but not yet fit or optimized.
   **Original: motivated by Section 3's small, unrepresentative sample.
   Updated (2026-09-15): confirmed and quantified by Check B — after the
   full selection, truth-matched signal has effective σ₆₈ = 2.05±0.02 GeV
   inclusively (1.79±0.02 GeV both-barrel, 2.56±0.03 GeV with ≥1 endcap
   photon), with a real, resolvable tail traced directly to the ~34% of
   events with a mismodeled vertex (their own σ₆₈ = 2.60±0.03 GeV vs.
   1.79±0.02 GeV for the well-modeled 66%) — not just generic
   non-Gaussianity. This supports fitting the barrel-barrel and
   ≥1-endcap categories with SEPARATE signal shapes/widths (not one
   inclusive shape), each still a narrow-core-plus-tail form, with all
   widths fixed from this simulation measurement. The plain leading-pair
   (no-truth-matching) resolution (σ₆₈=2.049±0.016 GeV) matches the
   truth-matched number closely, so this simulation-based width should
   transfer reasonably to what the real selection sees.
9. **Background model: data sidebands only, no MC background
   dependency**, validated by a data-driven bias study across function
   families. *Consequential* — this IS the analysis's core method, so
   getting the function-family list right matters most in Phase 3+.

### Silent failure modes and their checks

| Silent failure | What it would look like | The check that catches it |
|---|---|---|
| **Double energy correction** (re-applying `Photon_eCorr` on top of already-corrected `Photon_pt`) | Higgs peak (and Z→ee peak) shifted by the same few-percent factor as the correction itself, but no error or crash | Z→ee check (Section 5.2): a peak systematically off 91.19 GeV by a few percent is the direct fingerprint of this bug |
| **Using preVFP simulation for a postVFP dataset** (or vice versa) | Everything runs; normalization and pileup-sensitive efficiencies are subtly wrong | Every signal/background record used was cross-checked against its own `run_period` metadata field (`INVENTORY.md` B.1) — not just the "APV" naming convention; repeat this exact check for any *new* record added later |
| **Missing golden-JSON filter** | Everything runs; a small excess of noisy/bad-quality events inflates backgrounds slightly, no crash | Compare integrated luminosity computed from the *actually-used* run list against the official `Run2016Glumi.txt`/`Run2016Hlumi.txt` totals (`INVENTORY.md` A.2) — a mismatch flags the filter isn't being applied |
| **Wrong `genWeight` normalization** (e.g. using event *count* instead of `genEventSumw`, or forgetting the ~0.3% negative-weight events) | Signal yield off by whatever the average weight deviates from 1 (small here, ≈21.7 magnitude cancels in the ratio, but a bug that drops negative weights would bias it) | Compute `Σ genWeight / N_events` and compare to 1.0 within the expected small deviation; explicitly count negative-weight events and confirm the ratio matches the ~0.3% measured here |
| **Trigger not actually applied to data** (config key present but silently ignored, or applied only to MC) | Data yield too high, background shape includes non-triggered events with different kinematics | Compare the measured trigger-pass fraction in the real full-statistics cutflow against this design check's 24.6% (data)/59.3% (signal MC) order-of-magnitude — a large deviation flags a broken cut, not just statistical noise |

---

## Section 8 — Implementation plan

Ordered so that later tasks depend on earlier ones being merged and
tested; each is scoped for one implementation session.

1. **Generalize the scalar-event-field mechanism** (`EventIds` →
   a named-list-of-scalar-categories pattern) in `schemas.py`/`file_parser.py`.
   *Acceptance*: existing `EventIds` behaviour is a special case of the
   new mechanism; full existing test suite passes unchanged; a new unit
   test adds a synthetic second scalar category and confirms it round-trips.
2. **Golden-JSON validated-runs filter** (Section 6.1), built on task 1.
   *Acceptance*: unit tests pass (certified/not-certified/wrong-run
   cases); regression test confirms identical output to today with the
   new config key absent; a real-file smoke test on one Run2016G file
   shows the expected small drop in event count from the filter.
3. **HLT trigger requirement** (Section 6.2), built on task 1.
   *Acceptance*: unit + regression tests as in task 2; a real-file smoke
   test reproduces this design document's own 24.6%/59.3% pass fractions
   (data/signal) within statistical uncertainty on a larger sample.
   **Updated (2026-09-15)**: also implement the trigger-mimicking (TM)
   photon cuts (Section 7 #3, "Update — physics checks" above) as part of
   this task or task 6 (whichever ends up owning photon-level selection
   cuts) — acceptance should additionally reproduce Check C1's HLT-pass-
   given-offline-selected fractions (93.9% without TM, 99.0% with TM,
   `physics_checks/check_c_results.json`) within statistical uncertainty.
4. **Extend the CMS photon schema field list, plus `bool_cuts` and
   `eta_exclude` cut types** (Section 6.3). *Acceptance*: unit tests for
   both new cut types on synthetic data; regression test confirms
   `pt`/`eta`/`phi`/`mass` output is byte-identical to today when no new
   cuts are configured; a real-file smoke test confirms `isScEtaEB`/`EE`
   correctly exclude the 1.4442–1.566 gap (resolving this design
   document's one open UNVERIFIED item from Section 2).
5. **`genWeight`/pileup scalar fields + `genEventSumw` aggregation**
   (Section 6.4), built on task 1 for the `Events`-tree part; the
   `Runs`-tree aggregation is independent and can be built in parallel.
   *Acceptance*: unit tests for weight round-tripping (including sign)
   and multi-file `genEventSumw` summation; regression test with the new
   keys absent/false.
6. **`studies/hgg_cms/` analysis code**: the diphoton selection itself
   (steps 2–8 of Section 2, using the now-available fields from tasks
   2–5), the per-event output writer (Section 6's format), and a
   real-data-scale cutflow validation. *Acceptance*: reproduces this
   design document's small-sample cutflow shape on a full file; produces
   the per-event output file with the specified columns; explicit
   assertion that no code path ever reads a `Photon_eCorr`-multiplied
   energy (guards against the double-correction failure mode).
   **Updated (2026-09-15)**: "the diphoton selection itself" now
   explicitly includes the trigger-mimicking cuts (Section 7 #3) — use
   `physics_checks/common.py`'s `photon_tm_mask`/`compute_isolation_proxies`
   as the reference implementation (same NanoAOD-proxy definitions,
   documented caveats about not matching CMS's exact vertex-dependent
   isolation included).
7. **Fine-binned histogram + Z→ee / sideband validation scripts**
   (Section 5), consuming task 6's output. *Acceptance*: Z→ee peak
   position and width measured with real statistics against the ±1 GeV /
   30%-relative-width criterion defined in Section 5.2; sideband-only
   plots (blinding preserved) produced for at least one background
   function family.
   **Updated (2026-09-15)**: Check C2 already previews this at small
   statistics — data-only Z peak (electron-veto-inverted), 91.5 GeV,
   σ₆₈≈2.4 GeV, unaffected by TM cuts (`plots_C2_zpeak_with_without_TM.png`).
   Still outstanding for this task: the actual data-vs-DY-simulation
   (recid 35669) comparison Section 5.2 specifies, at full statistics.
   **Added (2026-09-15, "Review corrections to the physics-check update"
   above): Check C3's diphoton-HLT pass fraction (34.8%/39.5%) is invalid
   as a trigger-efficiency measurement, because the trigger's own
   "Mass90" online cut biases a 70–110 GeV Z-mass window. This task's
   acceptance criteria now also include: measure the diphoton-HLT pass
   fraction in data using a tag-and-probe method that avoids that bias —
   select Z→e⁺e⁻-like pairs via the orthogonal `HLT_Ele27_WPTight_Gsf`
   single-electron trigger, restricted to offline m_ee above ~95–100 GeV
   (clear of the "Mass90" threshold), and compare the resulting
   diphoton-HLT pass fraction between data and DY simulation (recid
   35669). Not yet run.**
8. **Vertex study at full statistics** (repeat Section 3's check on many
   more simulated events, still respecting per-task event/file limits
   where applicable, or as part of a proper batch job once available).
   *Acceptance*: the right-vs-wrong-vertex resolution difference is
   either confirmed with a statistically significant separation, or
   confirmed absent — resolving Section 3's open (a)-vs-(b) question —
   before the signal model's tail assumption (Section 7, item 8) is
   locked in for a real fit.
   **Updated (2026-09-15): LARGELY SUPERSEDED by Check B above**
   (`physics_checks/check_b_vertex.py`, n=19,770 truth-matched signal
   events after full selection, 25× Section 3's original sample). The
   right-vs-wrong-vertex resolution difference is now confirmed with a
   clear, statistically significant separation (σ₆₈ 1.79 vs. 2.60 GeV),
   and the vertex-reference question (B1) is fully resolved (stored
   directions already use `PV_z`). What remains open for a true
   full-statistics/multi-file pass: repeating this on the OTHER
   production modes (VBF/WH/ZH/ttH, not just ggH) and on more ggH files/
   events than the single-file, 50,000-event budget used here, before
   finalizing per-category signal-model parameters for the real fit.
