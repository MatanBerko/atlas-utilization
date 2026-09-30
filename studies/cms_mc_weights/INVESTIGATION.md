# CMS MC normalisation investigation

Branch: `investigate/cms-mc-normalisation`, off fork `master` (origin =
`github.com/MatanBerko/atlas-utilization`) at commit `4f50b99`. Read-only
against upstream (`github.com/Zhavi221/atlas-utilization`) throughout — PR #23
was read via `git fetch .../pull/23/head` (no local branch, no push, no PR
comment). Nothing in `services/`, `orchestration/`, `domain/`, configs,
`RECIPE.md` or the inventory was modified. No qsub/batch jobs were used; the
one cluster job (Task B) ran interactively on the analysis node, `nice`d,
under `work/cms_mc_norm_investigation/`, in well under an hour.

Evidence discipline: every number below traces to a file in `evidence/` (raw
portal JSON, gzipped where large; the two CMS luminosity `.txt` files opened
directly; a small per-file JSON readout from the one cluster job) or to a URL
that was actually fetched and is quoted. Anything not directly verified is
marked **UNVERIFIED**.

---

## A. State check

**Git state** — all matched the brief exactly:
- `origin` = `https://github.com/MatanBerko/atlas-utilization.git` (confirmed
  before anything else was done).
- `origin/master` HEAD = `4f50b99` ("Add docs/BRANCH_LAYOUT.md ...") — matches.
- `origin/survey/full-inventory` HEAD = `ddb6dc1` ("Add complete CMS Open
  Data inventory...") — matches; read via `git show
  origin/survey/full-inventory:<path>`, never checked out/merged.
- Upstream PR #23 head = `9be20a9` ("fix: move WeightsRegistry import to top
  of file"), not merged into upstream `master` (`4f50b99` also on upstream —
  confirmed identical fork/upstream master at this point). Fetched via
  `git fetch https://github.com/Zhavi221/atlas-utilization.git pull/23/head`
  only; no `upstream` push, no PR interaction.

**What `services/parsing/mc_weights.py` does today** (all on fork `master`,
unchanged by this investigation):
- `file_is_simulation()` detects MC purely from the `Events` tree's own
  branch list (`genWeight` present → simulation), no global "is this a MC
  run" flag.
- `resolve_weight_and_pileup_groups()` adds `genWeight` (and, for MC,
  `Pileup_nTrueInt` alongside the data/MC-common `PV_npvsGood`) to the
  per-file scalar-branch read list when `read_event_weights` /
  `read_pileup_info` are set; raises `SimulationFieldRequestedOnDataError` if
  weights are requested on a file with no `genWeight` (wrong
  record/config), rather than silently producing wrong output.
- `read_runs_tree_sums()` sums `genEventSumw` / `genEventCount` /
  `genEventSumw2` over every entry of a file's `Runs` tree (with retry on
  transient read failure), and `aggregate_sumw_for_processed_files()` sums
  these across every file **actually processed in this run** — and this is
  the one, explicit **consistency rule** implemented here: if any processed
  file's `Runs`-tree read fails, the whole aggregation raises rather than
  silently summing over a subset, so the genWeight numerator and the
  genEventSumw denominator can never silently cover different file sets.
  This is a materially different design from PR #23's registry (see §E).

**Where weights reach histogram filling on fork master today: nowhere in the
shared pipeline.** `domain/statistics.py`'s `ParsingStatistics.sumw_by_record`
only *carries* the aggregated sums as metadata; nothing in
`services/pipelines/histograms_pipeline.py` on fork master multiplies a fill
by `genWeight` or by any cross-section/luminosity factor — that pipeline is
ATLAS-only for weighting purposes (see §E) and ships with no CMS weighting
hook at all yet. Weights are only *used* to fill a histogram in one place in
the whole repo: the ad-hoc study script
`studies/m0m1j0_cms/cluster/merge_ttbar.py`, which reads raw per-event
`genWeight` alongside the mass array, applies the *same* selection mask to
both, and calls `np.histogram(mass, weights=genWeight)` to produce a
**separate**, clearly-named `m0m1j0_ttbar_postprocessed_weighted.root`
file alongside an **unweighted** primary histogram
(`RECIPE.md` §8 point 4, confirmed directly in the script,
`merge_ttbar.py:374-376`). This is the raw sum of generator weights in each
bin — **not** a physical yield: no cross section, no luminosity, and no
`1/sum(genWeight)` normalization is applied anywhere in this study
(`RECIPE.md` §8 points 4-5, confirmed).

> **Plain-language summary:** The pipeline already knows how to read CMS's
> per-event weight and how to add up the correct per-file normalization
> denominator, and it's careful about not letting the two get out of sync.
> But nothing turns that into an actual normalized histogram outside one
> ttbar-only study script, and even there the result is just "raw weight
> sum per bin," not a cross-section-normalized yield.

---

## B. What the files provide

One cluster job (interactive, `nice`d, analysis node, `envs/atlas-pipeline`,
well under the 1-hour budget) opened 2 files per sample for the 3 required
records, reading only `Runs`-tree scalars and `Events`-tree `genWeight` (+
existence/length checks on the named branches) — never a full-file read.
Raw per-file JSON: `evidence/task_b_results.json`; portal metadata used to
pick files: `evidence/task_b_file_picks.json`; plots:
`plots/genweight_<recid>.png` (log-y).

**Runs-tree branch list (identical across all 3 samples' Runs trees, 8
branches, 1 entry per file in every case checked):** `LHEPdfSumw`,
`LHEScaleSumw`, `genEventCount`, `genEventSumw`, `genEventSumw2`,
`nLHEPdfSumw`, `nLHEScaleSumw`, `run`. No `_`-suffixed NanoAOD variants
exist in these UL16 v9 files — the plain names are the only ones present.

| Sample (2 files each) | genEventSumw (sum over file) | genEventSumw2 | genEventCount | Σ genWeight (Events) | rel. diff vs genEventSumw | neg-weight frac | \|genWeight\| |
|---|---:|---:|---:|---:|---:|---:|---|
| 67801 TTTo2L2Nu (powheg, NLO) file 1 | 9,807,582.26 | 7.188e8 | 136,000 | 9,807,583.0 | 7.6e-8 | 0.4015% | constant, **72.6983 pb⁻¹-units** |
| 67801 file 2 | 90,871,566.4 | 6.659e9 | 1,260,000 | 90,871,568.0 | 1.7e-8 | 0.3975% | constant, 72.6983 (same) |
| 35669 DYJetsToLL_M-50 amcatnloFXFX (NLO) file 1 | 32,886,984,122 | 1.234e15 | 1,933,726 | 32,886,984,704 | 1.8e-8 | **16.336%** | constant, 25,259.67 |
| 35669 file 2 | 32,820,778,517 | 1.233e15 | 1,931,733 | 32,820,779,008 | 1.5e-8 | 16.369% | constant, 25,259.67 (same) |
| 42407 LQToBMu_M-400_pair (madgraph, LO) file 1 | 26,850.91 | 127,029.4 | 5,676 | 26,850.91 | -1.7e-8 | 0.0% | **not constant**, 24 distinct values, range 4.670–4.801 |
| 42407 file 2 | 8,956.23 | 42,401.0 | 1,892 | 8,956.23 | -5.5e-8 | 0.0% | not constant, 8 distinct values, range 4.664–4.816 |

Σ`genWeight` over the whole file equals `genEventSumw` to ~1–8×10⁻⁸ relative
— i.e. exactly, to float32 rounding — in **every** file checked, confirming
`genEventSumw` is nothing more than the pre-computed sum of the same
per-event `genWeight` values, not an independent number.

`genEventSumw2` is the sum of `genWeight²` (its ratio to `genEventSumw²` is
consistent with per-event-weight-squared variance in every file, not
independently re-derived here but consistent with the CMS documentation
convention for this branch).

**LHE/PS weight vectors** (all four present in every file checked):
`LHEWeight_originalXWGTUP` is a **scalar** (`float`, one value per event, not
jagged, contrary to a naive "vector" assumption), `LHEScaleWeight` is
`float[]` with constant length 9 (67801/35669) or 8 (42407 — madgraph LO
sample, one fewer scale-variation point), `LHEPdfWeight` is `float[]` with
constant length 103 in all three samples (NNPDF3.1 100-replica set + 3
extra), `PSWeight` is `float[]` with constant length 4 everywhere.

**Pileup/prefiring branches**: `Pileup_nTrueInt`, `L1PreFiringWeight_Nom`,
`L1PreFiringWeight_Up`, `L1PreFiringWeight_Dn` are present in all 6 files
checked. No branch containing the substring `puWeight` exists in any of
them — pileup-reweighting *inputs* exist, but no pre-computed pileup
*weight* branch does (this pipeline would have to compute it itself; see
§H).

**genWeight distribution shape** (see the 3 PNGs): TTTo2L2Nu and
DYJetsToLL_M-50 amcatnloFXFX both show the classic two-spike pattern (NLO
generator produces essentially only ±1 constant-magnitude weight per event,
confirmed by "1 unique |value|" in both) — the log-y plot is two bars, not a
continuum. LQToBMu_M-400_pair (madgraph LO) instead shows a small number of
close but distinct positive values (8–24 depending on file) — consistent
with LO madgraph's per-event PDF/scale reweighting spread rather than a true
NLO ± unit weight.

**Correct aggregation rule, in plain terms**: for a given record, sum
`genEventSumw` (and `genEventCount`, `genEventSumw2`) over the `Runs` tree of
**every file whose `Events` tree was actually read this run** (never assume
one entry per file, though it was 1 in all 6 files checked; never use a
record-level total that might include files this run didn't touch) — this
is exactly what `aggregate_sumw_for_processed_files()` already does on fork
master (§A). The per-event weight to use when filling a histogram is the
raw `genWeight` value (not its sign, not 1.0) — confirmed by the fact that
Σ`genWeight` reproduces `genEventSumw` to 8 significant figures in every
file.

> **Plain-language summary:** For every sample checked, "how many effective
> events were generated" is just the sum of the same `genWeight` numbers
> that get read per event — nothing hidden or independently defined. The
> Drell-Yan NLO sample has real, sizeable negative weights (~16%, as
> expected for amcatnloFXFX); the powheg ttbar sample has a small ~0.4%
> negative fraction; the leptoquark LO sample has none. All the auxiliary
> weight-systematic branches (scale/PDF/parton-shower variations) exist with
> the expected fixed lengths in every file, and the ingredients needed for
> pileup and L1-prefiring corrections are present, but no ready-made pileup
> weight exists — it would have to be computed.

---

## C. Cross sections

Every NanoAODSIM sample examined has its cross section on the **MiniAODSIM
sibling record**, never on the NanoAODSIM record itself (confirmed
directly: no key or substring matching "cross" exists anywhere in a
NanoAODSIM record's own JSON, e.g. 67801 — matching what
`studies/m0m1j0_cms/RECIPE.md` §8 already found for this exact record).
Siblings were found via each record's own `relations` field (never by title
matching — every one of the 38 records checked resolved cleanly this way,
and a `title_match` sanity check — comparing the physics-process name
segment of the NanoAOD and MiniAOD titles — passed for all 38). Raw JSON
saved under `evidence/nano_records/<recid>.json.gz` and
`evidence/mini_records/<sibling_recid>.json.gz`; the combined table is
`evidence/task_c_xsec_table.json`, tabulated into `candidate_samples.csv`.

**Exact field names** (from the sibling's `metadata.cross_section` object,
confirmed on record 67800, TTTo2L2Nu's MiniAODSIM sibling):
`total_value` (pb), `total_value_uncertainty` (pb), `filter_efficiency`,
`matching_efficiency`, `neg_weight_fraction`.

**Coverage**: of the 38 records checked (35 Task-F candidates + 3 extra LQ
samples for Task D), 34 have a `cross_section` block on their sibling; 4
don't (`LQToBMu_M-400_pair` and its 3 LQ cousins — leptoquark MiniAODSIM
records carry no `cross_section` field at all, checked directly). Of the 23
Tier-1 candidate records specifically, **23/23 (100%) have a portal cross
section**; Tier-0 is 1/2 (TTTo2L2Nu yes, the LQ sample no); Tier-2 (DY
HT/Zpt-binned) is 10/10.

### C(1): TTTo2L2Nu portal value vs. the 88.29 pb reference

Portal value (record 67800): `total_value` = **6.871×10² pb** (687.1 pb),
`total_value_uncertainty` = 0.5174 pb, `filter_efficiency` = 1.000,
`matching_efficiency` = 1.0, `neg_weight_fraction` = 0.4018% (matches the
directly-measured 0.40% from Task B almost exactly).

This does **not** match 88.29 pb, but the discrepancy is fully explained,
not a portal error: **`TTToSemiLeptonic`'s sibling (67992) reports the
identical value, 6.871×10² pb**, to 4 significant figures (confirmed
directly). Two different exclusive ttbar decay-channel samples cannot
physically share a cross section unless the number recorded is the **shared
inclusive ttbar cross section**, not the decay-mode-specific one — i.e. the
portal's `total_value` here is the full-ttbar POWHEG generator cross
section, carried over identically onto each of the decay-exclusive
NanoAOD/MiniAOD samples, with no branching-ratio scaling applied to it and
no generator filter recorded against it (`filter_efficiency = 1.000`,
because CMS doesn't book-keep the decay-mode split as a "filter" in this
field).

Reference check, using the LHC TopWG's own recommended value (opened
directly, `https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO`):
inclusive σ(ttbar) at 13 TeV, mtop = 172.5 GeV, **NNLO+NNLL = 833.9 pb**
(Top++v2.0, ATLAS+CMS recommended). The task's 88.29 pb reference is this
NNLO+NNLL value times the dilepton (any-flavor, e/μ/τ→ℓ) branching fraction
(~10.6%, from W→ℓν branching fractions). The portal's 687.1 pb is ~82.4% of
833.9 pb — a gap of the same size (~15–20%) that is well known to separate
an NLO(-only) POWHEG generator cross section from the NNLO+NNLL-resummed
value; applying the same 10.6% BR to the portal's 687.1 pb gives ≈72.8 pb,
consistent with 88.29 pb at the same ~18% NLO-vs-NNLL gap.

**Conclusion — is the portal σ usable?** Yes, but **only after correcting
it**: for these decay-exclusive powheg ttbar samples, the recorded
`total_value` must be multiplied by the appropriate ttbar decay-mode
branching fraction before use (it is the shared inclusive cross section,
not the exclusive one) — using it as-is would overcount TTTo2L2Nu's yield by
roughly a factor of ~9.4 (833.9/88.29). Both `TTTo2L2Nu` and
`TTToSemiLeptonic`'s Tier-1 candidate rows in `candidate_samples.csv` carry
this same 687.1 pb value for exactly this reason — this is not a data-entry
error.

### C(2): does the portal's σ already include the filter efficiency?

**No — confirmed both from the portal's own documentation and from direct
empirical cross-checks. Confidence: high.**

The portal's own cross-section guide
(`https://opendata.cern.ch/docs/cms-guide-xsec`, fetched directly) states
CMS's GenXSecAnalyzer reports cross sections at up to three distinct
stages: *"Before matching: the cross section before jet matching and any
filter. After matching: the cross section after jet matching BUT before any
filter. Filter efficiency: the efficiency of any filter. After filter: the
cross section after jet matching and additional filters are applied. This
is your final cross section."* — i.e. `total_value`, `matching_efficiency`
and `filter_efficiency` are reported as separate factors specifically so
they can be multiplied together; multiplying `total_value` by
`filter_efficiency` (and `matching_efficiency`, where present) is exactly
what's required, not a double-count.

Empirical check on a record with `filter_efficiency` ≠ 1
(`/QCD_Pt-1000_MuEnrichedPt5_TuneCP5_13TeV-pythia8/` → MiniAODSIM sibling
63145, `evidence/record_qcd_muenriched_filtertest.json.gz`, fetched
directly): `total_value` = 1.079 pb, `filter_efficiency` = 0.1311, no
`matching_efficiency` key at all (no ME-jet matching involved for this
pure-PYTHIA8 sample). The 1.079 pb is the right order of magnitude for the
*raw*, pre-muon-filter QCD dijet cross section in this pT-hat bin — the
final physical cross section for the muon-enriched, produced sample is
1.079 × 0.1311 ≈ 0.1414 pb. Every Tier-1 candidate checked in this study
happens to have `filter_efficiency = 1.000` (none of them use a generator
filter), but several (the amcatnloFXFX and madgraphMLM DY/diboson samples)
have `matching_efficiency` between 0.1 and 0.8, which the same "multiply
in" rule applies to identically.

One residual ambiguity, stated honestly: the guide distinguishes
"before-matching" from "after-matching-but-before-filter," and it wasn't
independently verified *which* of these two stages `total_value` always
represents when both `matching_efficiency` and `filter_efficiency` are
present together on the same record — but this doesn't change the
double-counting answer either way, since both correction factors are always
reported alongside `total_value` specifically for the user to apply.

### C(3): reachable higher-order reference sources (only those actually opened)

- **LHC Top WG** (ttbar, single top):
  `https://twiki.cern.ch/twiki/bin/view/LHCPhysics/TtbarNNLO` — opened
  directly; σ(ttbar, 13 TeV, NNLO+NNLL) = 833.9 pb (scale +20.5/−30.0 pb,
  PDF+αs ±21.0 pb). No channel-split (dilepton/semilep/hadronic) number is
  given on this page itself — that split was taken from the task's own
  88.29 pb reference figure, not re-derived here.
- **LHC Higgs WG**: `https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV`
  — opened directly; ggH (N3LO QCD+NLO EW) = 48.52 pb at mH=125.09 GeV,
  ggH (NNLO+NNLL QCD+NLO EW) = 44.08 pb; VBF (NNLO QCD+NLO EW) = 3.779 pb.
  Compare portal (this study's siblings): ggH→ZZ→4l M125 portal σ =
  28.87 pb (this already includes the small H→ZZ→4l branching fraction and
  powheg2+JHUGen generator-level filtering, so it is *not* directly
  comparable to the bare 44–48.5 pb production numbers above without also
  applying the H→ZZ→4l branching ratio — not independently re-derived
  here). VBF portal σ = 3.935 pb, close to the bare VBF production number
  (3.779 pb) before the decay branching ratio is applied — **this is a
  strong hint that at least this VBF sample's portal value is closer to a
  raw production cross section than a fully-decay-inclusive one; not fully
  resolved here, UNVERIFIED beyond this observation.**
- **Drell-Yan / diboson published values**: not independently re-derived
  from a theory paper in this session; the portal's own sibling values (see
  `candidate_samples.csv`) were used as-is, cross-checked only via the
  matching/filter-efficiency mechanics in C(2), not against an external NNLO
  DY/diboson calculation.
- **LHC SUSY WG top-squark pair tables** (for the scalar-LQ proxy):
  `https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SUSYCrossSections13TeVstopsbottom`
  — opened directly; NNLOapprox+NNLL stop-pair cross section at m(stop) =
  400 GeV = **2.276 pb** (±4.88%). This is directly relevant to the 42407
  (LQToBMu_M-400_pair) sample (§D) as an approximate cross-section proxy.
  **Caveat, stated explicitly per the task**: this proxy is valid only if
  the leptoquark is scalar (color-triplet, spin-0 — matching the QCD
  pair-production diagrams of a stop) *and* the t-channel lepton-exchange
  contribution to LQ pair production is negligible. A paper specifically
  studying this
  (arXiv:2108.11404, abstract fetched directly) states corrections from
  t-channel lepton-exchange diagrams can reach **~60%** in some scenarios —
  so this caveat is not a formality; it can matter a lot, and was not
  checked case-by-case for the M-400 sample here.

### C(4): 2016 G+H golden-JSON luminosity

Portal record `https://opendata.cern.ch/record/1059` ("CMS luminosity
information for 13TeV proton-proton collision data taken in 2016") links
per-era files rather than quoting a number on the page itself; the two
files were downloaded directly
(`https://opendata.cern.ch/record/1059/files/Run2016Glumi.txt` and
`.../Run2016Hlumi.txt`, saved to `evidence/`) and their own `brilcalc`
summary lines read:

```
Run2016G: | nfill 32 | nrun 70 | totdelivered(/fb) 8.013877685 | totrecorded(/fb) 7.653261227 |
Run2016H: | nfill 32 | nrun 86 | totdelivered(/fb) 9.155092544 | totrecorded(/fb) 8.740119304 |
```

**2016 G+H recorded luminosity = 7.653261227 + 8.740119304 = 16.393380531
fb⁻¹ ≈ 16.39 fb⁻¹** (delivered: 17.169 fb⁻¹). This directly resolves the
"not independently verified" gap flagged in `studies/m0m1j0_cms/RECIPE.md`
§8 point 5 for this exact DoubleMuon dataset.

> **Plain-language summary:** The cross sections we need live one page away
> from the NanoAOD record, on its "MiniAOD sibling," and every sample we
> checked has one *except* the leptoquark samples. The ttbar dilepton
> number needs a correction (multiply by the dilepton branching fraction)
> because CMS recorded the shared, whole-ttbar number on it, not the
> dilepton-only one — once corrected it lines up with the standard
> reference. The displayed cross section is deliberately *before* any
> generator filter or matching efficiency, so those extra factors must be
> multiplied in, not skipped. We now have a real, sourced number for the
> 2016 G+H luminosity (16.39 fb⁻¹) where before it was an open question.

---

## D. Leptoquark

`42407` (LQToBMu_M-400_pair) and siblings' MiniAODSIM records' `methodology`
field only stores the McM validation-runner shell wrapper, not the physics
fragment itself — but that wrapper names the exact McM prepid
(`EXO-RunIISummer20UL16wmLHEGEN-02146`), and its underlying fragment (fetched
directly from the live McM API,
`https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/EXO-RunIISummer20UL16wmLHEGEN-02146`)
gives the actual gridpack path:
`/cvmfs/cms.cern.ch/phys_generator/gridpacks/2017/13TeV/madgraph/V5_2.6.5/LQToBMu/LQToBMu_madgraph_LO_pair-M400_...tarball.tar.xz`
— confirming **MadGraph5_aMC@NLO LO, pair production**, M=400 GeV,
hadronized with Pythia8 TuneCP2. The 3 sibling channels (42262 LQToBEle,
42870 LQToSMu, 42630 LQToDEle) are the identical production/decay pattern
with a different quark+lepton decay flavor (b+e, s+μ, d+e respectively —
all still pair production, same McM production chain). The gridpack tarball
itself (which would definitively confirm scalar-vs-vector inside the UFO
model) was not opened — that lives on cvmfs, not reachable from this
session — so scalar-vs-vector for the CMS sample rests on external
corroboration, not a direct read of the model file:
a web search (queries and links in-session) turned up published CMS/theory
descriptions of second-generation leptoquark pair production at CMS
consistently describing it as **scalar** leptoquark pair production via
gg-fusion + qq̄-annihilation (the same QCD process as squark-pair
production) — consistent with, but not a substitute for, opening the actual
model card.

**ATLAS ~400 GeV scalar leptoquark sample**: found via `atlasopenmagic`
(`get_all_metadata()`, run on the cluster, `envs/atlas-pipeline`), scanning
all 5 cached releases (2024r-pp, 2020e-13tev, 2025e-13tev-beta,
2025r-evgen-13tev, 2025r-evgen-13p6tev) for `physics_short` containing "LQ".
Full record: `evidence/atlas_lq_candidates.json`. Only `2025r-evgen-13tev`
has scalar-LQ pair-production samples at exactly M=400 GeV, and there are
exactly two: DSID **312117**
(`aMcAtNloPy8EG_A14N30NLO_LQu_el_ld_0p3_beta_0p5_hnd_1p0_M400`) and DSID
**312159** (`..._LQd_el_..._M400`), both with `process` field
**"scalar leptoquark pair production"** (ATLAS's own metadata confirms
scalar) and cross section 2.15 pb. **Both decay to an electron, not a
muon** — the muon-decay members of the same ATLAS family exist only at
M=300 (DSID 310194, 7.962 pb) and M=600/700/850/1450 GeV, never at M=400.

**Recommended closest CMS match, stated plainly**: CMS's `LQToBMu_M-400_pair`
(muon decay) has **no exact ATLAS counterpart at the same mass and decay
flavor**. The mass-exact ATLAS match (312117/312159, M=400) decays to an
**electron**, not a muon — a genuine decay-mode mismatch, not a detail to
paper over. If Maryna's reference sample is indeed one of these two
(312117 or 312159), the honest framing for Matan is: CMS's
`LQToBMu`/`LQToBEle` pair (42407/42263) brackets both ATLAS decay flavors at
M=400, but only the **electron**-decay CMS sibling (`LQToBEle_M-400_pair`,
42263) matches ATLAS's exact-mass decay flavor; the muon-decay CMS sample
Matan already has selected does not.

> **Plain-language summary:** CMS's 400 GeV leptoquark sample is a genuine,
> low-order ("leading order") MadGraph pair-production sample of a scalar
> leptoquark decaying to a b-quark and a muon. ATLAS's closest 400 GeV
> scalar leptoquark samples decay to an **electron**, not a muon — so if
> Maryna's ATLAS reference is one of those two, the decay channel doesn't
> match ours exactly; the electron-decay CMS sibling would be the fairer
> comparison, not the muon one currently selected.

---

## E. PR #23 (read-only)

Diff read via `git diff origin/master...FETCH_HEAD` (22 files, +1363/−162);
nothing merged, nothing pushed, no upstream interaction. Report only.

**Data structures**

| Field/structure | Meaning | CMS source available? |
|---|---|---|
| `MCDatasetMetadata.cross_section_pb` | generator σ | atlasopenmagic `get_metadata()["cross_section_pb"]` — **ATLAS-only API**; CMS equivalent is the portal sibling's `cross_section.total_value` (§C), not wired up |
| `.sum_of_weights` | normalization denominator | atlasopenmagic `["sumOfWeights"]` — a single **dataset-level** number from ATLAS's own metadata service, not computed from files this pipeline processed (contrast §A) |
| `.k_factor`, `.gen_filt_eff` | higher-order/filter corrections, default 1.0 | same source; portal equivalent for CMS would be `matching_efficiency`×`filter_efficiency` (§C(2)) |
| `MCWeightingConfig.target_luminosity_fb`, `.luminosity_by_campaign` | analysis-chosen target lumi | config-only, not a dataset property |
| `weights_registry.json` format | `{"default_weight": 1.0, "weights": {source_prefix: float}}` | built by `utils/build_weights_registry.py` from `{source_prefix: DSID}` + fetched metadata |
| `weights_registry.json` DSID extraction | 3 regexes (`dsid_?(\d{6,8})`, `TeV\.(\d{6})\.`, `\.(\d{6})\.[A-Za-z]`) matching a **6-digit ATLAS DSID token** | ATLAS URL/filename convention only |

**Weight application at fill time** (`services/pipelines/histograms_pipeline.py`):
`_fill_hist()` fills `hist.Fill(val, weight)` where `weight` comes from
`WeightsRegistry.weight_for(source_prefix)` — a **single flat per-dataset
factor** (`compute_normalization()` = σ·k·ε_filter·L / sumOfWeights),
optionally multiplied by a **per-event** `_mcw` companion array
(`mc_event_weights[i]`, i.e. the flattened `mcEventWeight` — see below) when
one exists alongside the signature. `hist.Sumw2()` is called whenever a
registry is present, to track weighted errors correctly.

**Every place that assumes ATLAS, specifically:**

1. **DSID extraction and the silent default-weight-1.0 fallback**
   (`weights_registry.py`): `WeightsRegistry.weight_for()` returns
   `self.default_weight` (1.0) for any source prefix not found in the
   registry, logging a warning **once** per prefix and then proceeding
   silently forever after. This is entirely reasonable for ATLAS's own
   "unknown → treat as unweighted data passthrough" design intent, but if
   ported naively to CMS it would mean: any CMS file whose DSID-extraction
   regex fails to match a 6-digit ATLAS-style token (which is *every* CMS
   file — CMS uses record IDs and hash-named ROOT files, not `TeV.410470.`
   tokens) silently gets weight 1.0, with no hard failure — the opposite of
   fork master's own `mc_weights.py` design (§A), which raises loudly rather
   than silently produce a wrong-but-plausible number.
2. **`raw[:, 0]` flattening in `file_parser.py`** (line ~502, confirmed by
   direct diff read): PHYSLITE's `mcEventWeight` branch is `var * float` — a
   **vector per event**, typically length 1, holding alternative weight
   variations — and the code explicitly takes index 0 ("the nominal
   weight") to flatten it to a scalar so it round-trips through
   ROOT/uproot: *"PHYSLITE stores mcEventWeight as var * float (a vector per
   event, typically length 1). Take the nominal weight at index 0..."*
   (comment, verbatim). **CMS's `genWeight` is already a flat scalar
   per event in NanoAOD** (confirmed directly in Task B — no `[:, 0]`
   indexing needed or possible; it isn't jagged). Porting this function
   unmodified onto CMS would be either a no-op (if guarded) or an outright
   crash/wrong-index bug (if applied to a non-jagged array) — not a subtle
   difference, a structurally different branch shape.
3. **Dataset-level `sumOfWeights` vs. sum over processed files**: PR #23's
   `sum_of_weights` comes from a **single number in ATLAS's external
   metadata service** (`atlasopenmagic`), covering the *whole* official
   dataset regardless of which files this particular pipeline run actually
   read. Fork master's own CMS `aggregate_sumw_for_processed_files()` (§A)
   deliberately does the opposite: it sums `Runs`-tree `genEventSumw` only
   over the files this run actually processed, and fails loudly rather than
   letting the numerator/denominator file sets silently diverge. These are
   two incompatible design philosophies, not two implementations of the
   same idea — one leans on an external, whole-dataset authority; the other
   is self-consistent per-run at the cost of requiring every processed
   file's `Runs` tree to be readable.

One additional observation, noted but out of scope to act on: `file_parser.py`'s
diff contains leftover `print(f"[DEBUG MCW] ...")` debug statements and a
large commented-out block of the old (pre-PR) result-building code, left in
place rather than cleaned up — a code-quality note, not a correctness one.

> **Plain-language summary:** PR #23 builds a real, working weighting
> system — but every single piece of it, from where the cross section comes
> from to how the per-event weight is shaped, assumes ATLAS's specific data
> conventions (its DSID naming, its metadata service, its "one weight
> variant per event" branch shape). None of that carries over to CMS
> without real rework, and the two most CMS-relevant differences — how
> "sum of weights" is defined, and whether an unrecognized file fails loudly
> or silently gets weight 1.0 — are exactly the two places fork master's own
> existing CMS code already made the opposite, more conservative choice.

---

## F. Sample subset

Built from `origin/survey/full-inventory`'s `master_table.csv` (read via
`git show`, 29,688 rows, filtered to `type_secondary=="Simulated"` and
`"nanoaodsim"` in `formats` → 10,679 NanoAODSIM rows), with anchored,
exact-title regexes (not substring search — substring search on e.g.
"TTTo2L2Nu" or "ZZTo4L" pulls in >100 unrelated BSM-resonance/Higgs-signal
samples that merely contain that string; every pattern used is anchored to
the start of the title, `^/...`, and every match count was checked to be
exactly 1 before accepting it). Output: `candidate_samples.csv` (35 rows).

**Tier 0**: 67801 TTTo2L2Nu (49 files, 43,546,000 events), 42407
LQToBMu_M-400_pair (12 files, 50,000 events).

**Tier 1** (23 records, one nominal pick per physics process, explicitly
excluding tune variations — `TuneCP5CR1/CR2`, `TuneCH3`, `erdON`,
`TuneCP5up/down` — mass variations (`mtop16*`, `mtop17*`), `hdampUP/DOWN`,
`width×N`, and `_PDFWeights`-tagged duplicate productions):
DYJetsToLL_M-50 (both amcatnloFXFX 35669 and madgraphMLM 35671),
DYJetsToLL_M-10to50 (amcatnloFXFX 35631, madgraphMLM 35633),
TTToSemiLeptonic (67993, excluding 24 tune/mass/hdamp/CR/width/erdON/Vcb/TTbb
variants found and excluded), ST_tW_top/antitop NoFullyHadronicDecays
(64895/64839, excluding DS/CH3/CR1/CR2/PDFWeights/erdON/up/down/mtop/hdamp
variants — 14 excluded per leg), WWTo2L2Nu (72676), WZTo3LNu (72752,
amcatnloFXFX chosen as the nominal NLO pick; 4 variants excluded: the 5f
madgraphMLM version 72744, and 3 alternative-mllmin POWHEG productions
72746/72748/72750), ZZTo4L (75589), ZZTo2L2Nu (75567), GluGluToContinToZZ
(all 7 final states found: 2e2μ/2e2ν/2e2τ/2μ2ν/2μ2τ/4e/4μ/4τ — 8 records,
38428–38442), TTZToLLNuNu_M-10 (68187), TTWJetsToLNu (68073),
GluGluHToZZTo4L_M125 (37728, the plain powheg2+JHUGenV7011 nominal;
excluded: CP5TuneUp/Down, minloHJJ, JHUGenV714, PSw variants),
VBF_HToZZTo4L_M125 (68847).

**Tier 2** (10 records, informational, not folded into Tier 1): DY M-50
HT-binned family (8 bins, 35651–35665) and Zpt-binned BPSFilter family (2
bins, 35673/35675) — combining these with the inclusive M-50 sample
requires **overlap removal (stitching)**: an event passing both the
inclusive sample's phase space and a specific HT/Zpt bin's generator-level
cut would otherwise be double-counted; this pipeline does not currently
implement any such stitching logic, so Tier-2 samples are listed for
completeness but are **not** ready to combine with Tier-1's inclusive DY
samples as-is.

**Cross-section coverage**: Tier-1 = **23/23 (100%)** have a sibling portal
cross section; Tier-0 = 1/2 (only TTTo2L2Nu; leptoquark MiniAODSIM records
carry no `cross_section` block at all); Tier-2 = 10/10.

**QCD and W+jets — kept out, one-line reason each**: QCD multijet production
has a total cross section of order tens of mb–μb at the LHC (many orders of
magnitude above any leptonic-trigger signal), so any leptonic final state
appearing in it is a rare fake/heavy-flavor-decay tail that this pipeline
has no dedicated fake-lepton or QCD-multijet estimation technique to model
correctly. W+jets requires a similarly dedicated, jet-multiplicity- and
missing-transverse-energy-dependent modeling/estimation approach (and is
almost always HT/pT-binned like the excluded Tier-2 DY family, with the same
stitching requirement) that is out of scope here.

> **Plain-language summary:** We now have a clean, deduplicated shortlist of
> 35 specific CMS Monte Carlo samples — the ttbar and leptoquark ones Matan
> named directly, plus one "standard" version of every other background
> process on his list (Drell-Yan, single top, WW/WZ/ZZ, ttZ/ttW, Higgs→ZZ→4l)
> with every tune/mass/systematic-variation duplicate explicitly excluded and
> named. Every single one of the 23 "standard background" samples has a
> usable cross section on the portal. QCD and W+jets were deliberately left
> off this list because they need their own dedicated background-estimation
> techniques that this project doesn't have.

---

## G. MC's role for BumpNet (reading only)

**arXiv:2501.05603** (BumpNet), fetched directly (`arxiv.org/html/2501.05603v1`):
- **§2.2.2**: MC simulation supplies the **background input histograms**
  used to build BumpNet's training/testing data — specifically samples
  generated for the Dark Machines initiative ("simulated data produced for
  the Dark Machines initiative... is used"), emulating **10 fb⁻¹** of 13 TeV
  pp collisions, generated with MadGraph + Pythia + Delphes3 detector
  simulation.
- **§4.2**: MC-simulated BSM signals are then **injected** into those
  background histograms ("Each of the BSM signals... has been added either
  to the DM channels 2b or 3") to test the network's sensitivity to
  specific bump shapes.
- **§2.1**: both signal and background histograms are explicitly
  **Poisson-fluctuated bin by bin** before being used as network
  input/training data — i.e. the paper's own inputs are deliberately built
  to look like real (counting) data, not like a raw weighted MC expectation.

**arXiv:2107.11573** (the earlier, referenced precursor method), fetched
directly (`arxiv.org/html/2107.11573`):
- **Introduction**: explicitly states *"Like in [4], no Monte-Carlo (MC)
  simulation is used"* for building its own training data — background
  shapes are smoothly-falling **analytic functions** with an injected
  Gaussian signal, each bin given an explicit Poisson fluctuation.
- **Discussion**: MC is reserved for **post-hoc interpretation** of a found
  excess — *"Bumps originating from systematic uncertainties due to
  detector effects... should appear in Monte Carlo simulations as well and
  can be ruled out."*

**Questions for Maryna** (not decided here, just listed per the task):
- Are MC histograms actually consumed as **BumpNet training/testing
  inputs** (as in 2501.05603 §2.2.2/§4.2), or only used for **signal
  injection** on top of real/pseudo-data backgrounds, or only for **post-hoc
  interpretation** of an already-found bump (as in 2107.11573's Discussion)?
  These are three different roles with different weight-normalization
  requirements.
- If MC histograms feed the network directly: are they always
  Poisson-fluctuated first (as both papers do), given that a **genWeight-**
  or cross-section-**weighted** histogram is not Poisson-distributed bin by
  bin (its variance depends on the weight distribution, not just the bin
  count) — so any "treat this weighted MC histogram like real/pseudo-data"
  step should go through an explicit pseudo-data generation step (e.g. draw
  a Poisson count around the weighted expectation) rather than feeding the
  weighted bin contents straight in?
- Which specific background/signal MC samples (if any) has Maryna actually
  used for the CMS side of this work so far, and at what luminosity target?

> **Plain-language summary:** In both papers, simulation plays one of two
> narrow, well-defined roles — either as the background shape BumpNet is
> trained on (with signals injected and Poisson noise added on top), or as a
> way to double-check a found bump isn't just a detector artifact — never as
> a stand-in for real data fed straight through. The open question for
> Maryna is which of these (if either) describes how she's actually using
> CMS MC, because a cross-section-weighted histogram doesn't behave like
> real counting data unless it's deliberately turned into pseudo-data first.

---

## H. Not-applied corrections

| Correction | Ingredients available to us? | Typical size (sourced) |
|---|---|---|
| Pileup reweighting | MC truth `Pileup_nTrueInt` present in every file checked (§B); data-side `PV_npvsGood` present too; **no ready-made data pileup profile file found on the portal** (searched the portal API directly; found only simulation/config records, no measured 2016 minbias-derived profile) — would have to be built from the recommended minbias cross section | Recommended inelastic-pp cross section **69.2 mb**, uncertainty **±4.6%**, applied by reweighting simulation to match the estimated data pileup distribution (sourced from published CMS analysis papers found via search, e.g. arXiv:2208.06485 and the JINST "Pileup mitigation at CMS in 13 TeV data" paper, arXiv:2003.00503 — not independently opened as a primary CMS POG page in this session, since the CMS-authenticated TWiki redirected to CERN SSO and could not be fetched) |
| L1 ECAL prefiring | `L1PreFiringWeight_Nom/Up/Dn` present in every file checked (§B) — the correction weight itself is directly available, no computation needed | **~2–3%** typical correction size for 2016/2017 (from search results referencing CMS documentation/analysis notes; the official TWiki recipe page requires CERN SSO login and could not be opened directly in this session — this figure is therefore from secondary citation, not a primary page read) |
| Muon ID/isolation/trigger scale factors | Not present as a ready weight in NanoAOD; would need the official per-muon SF files/JSONs, not checked for portal availability in this session | Individual SFs typically very close to 1.0 (e.g. Loose ID SF = 0.998 ± 0.001 for \|η\|<0.9, from a CMS tag-and-probe reference found via search) — the **combined** ID×iso×trigger product per event is the physically relevant number and was not separately quantified here |
| B-tag scale factors | Not present as a ready weight in NanoAOD; would need official per-jet-flavor SF files | **UNVERIFIED in this session** — no primary CMS BTV source with an explicit typical-magnitude number was successfully opened (searches returned only descriptions of the method, not a quoted percentage); do not treat any recalled b-tag SF magnitude as sourced |
| Jet energy resolution smearing | Raw jet `pt`/`eta` present in NanoAOD; no pre-computed smearing factor | Nominal JER itself: **~15–20% at 30 GeV, ~10% at 100 GeV, ~5% at 1 TeV** jet pT (from search results citing CMS JME performance papers). JER *uncertainty* is applied as an additional ±2.5–5% (eta-dependent) shift on top of the nominal smearing. **Effect on a resonance/dijet mass peak specifically**: search results (citing a CMS dijet-resonance search) report the JER-uncertainty-driven mass-peak-width change is of order **±10%** on the width itself, and up to **±1.4%** on the peak position/scale — i.e. JER predominantly **widens or narrows the mass peak**, with a smaller effect on where the peak sits |
| Muon momentum (Rochester) corrections | Raw muon `pt` present; no correction applied | A specific numeric dimuon-mass-resolution improvement was **not found** in this session's searches (only qualitative descriptions of the correction's components were found — a 1/pT-linear term plus global "T/Δ/SF/G" terms tuned to match the Z-peak position and width in data) — **UNVERIFIED**, do not treat any recalled percentage as sourced |

> **Plain-language summary:** Of the six standard corrections checked, two
> have everything we need already sitting in the files we read (L1
> prefiring — the weight itself is right there; pileup truth information,
> though not yet a ready-to-use reweighting profile). The other four
> (muon SFs, b-tagging, jet-energy smearing, muon momentum corrections)
> would require additional official CMS correction files that weren't
> checked for portal availability in this session, and for two of them
> (b-tag size, muon-momentum-correction size) no reliable sourced number
> was found at all — those should be treated as open questions, not
> assumed small.

---

## Deliverables in this branch

- `studies/cms_mc_weights/INVESTIGATION.md` — this file.
- `studies/cms_mc_weights/candidate_samples.csv` — 35-row Task F table.
- `studies/cms_mc_weights/evidence/` — raw portal JSON (gzipped), the two
  luminosity `.txt` files, and small per-file JSON readouts from the one
  cluster job.
- `studies/cms_mc_weights/plots/genweight_<recid>.png` — 3 PNGs, one per
  Task B sample.
