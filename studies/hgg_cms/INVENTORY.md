# Phase 2.1 — CMS H→γγ data/simulation inventory (read-only)

This is a **read-only inventory**: what exists on the CERN Open Data portal,
what the NanoAOD files actually contain, and what the pipeline on `master`
can already do with them. No event selection, no histograms, no fits were
run. Every factual claim below is cited to a portal record URL, a file's
own branch metadata, or a named external document. Anything that could not
be pinned to a source is marked **UNVERIFIED**.

All portal queries and file reads were done from a git worktree on branch
`study/hgg-cms-inventory` (created from `master` at `8cf737e1acf0fa736b78864e631dc6cc98e05772`).
Remote file reads used `uproot` over plain HTTPS range requests (the portal's
files support `Accept-Ranges: bytes`, confirmed directly) — no whole file
was downloaded; at most 1,000 events were read from each of 2 files.

---

## Part A — Collision data

### A.1 — DoubleEG NanoAOD records

| Run | recid | Dataset | NanoAOD ver. | Files | Total size | Events | Source |
|---|---|---|---|---|---|---|---|
| Run2016G | **30521** | `/DoubleEG/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` | v9 (UL) | 47 | 75,705,443,664 B (≈70.5 GiB) | 78,797,031 | [record/30521](https://opendata.cern.ch/record/30521) |
| Run2016H | **30554** | `/DoubleEG/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` | v9 (UL) | 86 | 83,808,508,571 B (≈78.1 GiB) | 85,388,673 | [record/30554](https://opendata.cern.ch/record/30554) |
| **Total** | | | | **133** | **159,513,952,235 B (≈148.6 GiB)** | **164,185,704** | |

The "file index" for each record is the record's own JSON API endpoint
(`https://opendata.cern.ch/api/records/<recid>`), which lists every
constituent file's XRootD/HTTPS URI, size and checksum under
`metadata._file_indices`. There is no separate downloadable index file for
these two records.

**Earlier 2016 runs (B–F): NOT on the portal as DoubleEG NanoAOD.** A full
search of every portal record whose title contains "DoubleEG" (`q=DoubleEG`,
18 hits total, verified 2026-09-15) returns only Run2016G and Run2016H
(as MiniAOD *and* NanoAOD), plus unrelated Run2015D and NANO/PAT
*configuration-file* records for G/H. No B, C, D, E, or F record exists for
this primary dataset in any format on this portal. Source: search results
captured in this session (see `records.json`; the search itself is not
re-runnable as a "record" but the resulting recid list is reproducible via
`https://opendata.cern.ch/api/records/?q=DoubleEG`).

*Aside, not used:* recid 31304, "DoubleEG dataset in NanoAOD format
enhanced with Particle Flow candidates from RunG of 2016", is a distinct,
non-standard derived format — out of scope here.

### A.2 — Integrated luminosity

Source: [record/1059, "CMS luminosity information for 13TeV proton-proton collision data taken in 2016"](https://opendata.cern.ch/record/1059).

| Run | Delivered (/fb) | **Recorded (/fb)** | Source file |
|---|---|---|---|
| Run2016G | 8.013877685 | **7.653261227** | `Run2016Glumi.txt` (downloaded, 84 lines, `brilcalc` summary table) |
| Run2016H | 9.155092544 | **8.740119304** | `Run2016Hlumi.txt` (downloaded, 100 lines) |
| **G+H total** | 17.169 | **16.393380531** | sum of the above |

**Uncertainty: 1.2%** (relative), stated verbatim on record 1059:
> "The uncertainty in the luminosity measurement of 2016 data should be
> considered as 1.2% (reference [Precision luminosity measurement in
> proton-proton collisions at √s = 13 TeV in 2015 and 2016 at CMS](https://cds.cern.ch/record/2759951))."

**How the portal says to compute luminosity for a subset of runs**, quoted
verbatim from the same record: the *recorded* per-run tables above are
already restricted to certified-good runs and lumisections (see A.3). For
a run/lumisection-level subset (e.g. after a data-quality or trigger cut),
the portal directs users to the finer-grained `pp_2016lumibyls.csv` (per
lumisection, 21.1 MB — not downloaded, linked only) and says explicitly:
"In your estimate for the integrated luminosity, check for which runs the
trigger you have selected is active and sum the values for those runs. For
prescaled triggers, the change of prescales ... is recorded in
`prescale_pp2016.csv`." A `normtag_PHYSICS_pp_2016.json` normtag file
(85.5 KB) records which luminometer/algorithm is authoritative per
lumisection.

### A.3 — Validated runs ("golden JSON")

Record **14220**: [`CMS list of validated runs Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`](https://opendata.cern.ch/record/14220), file
`Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt` (11,686 B).
Its own abstract states: "Run2016G is between run numbers 278820 and
280385. Run2016H is between run numbers 280919 and 284044." This matches
exactly the run-number ranges printed in `Run2016Glumi.txt` (first run
278820, last 280385) and `Run2016Hlumi.txt` (last run 284044) — **confirmed
consistent**, not assumed. Record 14221 is the same list further restricted
to runs with good muon reconstruction (`..._JSON_MuonPhys.txt`) — not
needed for a photon analysis, listed in `records.json` for completeness
only.

### A.4 — Trigger

**Exact name confirmed by direct evidence, not just the physics paper:**
reading the branch list of an actual Run2016G data file (see Part C) shows
the branch
**`HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90`**
(`typename=bool`, title `"Trigger/flag bit (process: HLT)"`) present and
readable. This is the strongest possible confirmation: the literal trigger
bit exists in the DoubleEG NanoAOD file.

**Physics description, from a CMS publication** (not the portal): CMS's
H→γγ properties measurement using the full 2016 dataset,
[arXiv:1804.02716](https://arxiv.org/abs/1804.02716) (CMS-HIG-17-015),
Section 4: "The events used in this analysis were selected by diphoton
triggers with asymmetric transverse energy (ET) thresholds of 30 and 18
GeV. The trigger selection requires a loose calorimetric identification
using the shape of the electromagnetic showers, a loose isolation
requirement, and a selection on the ratio of the HCAL and ECAL deposits of
the photon candidates. The R9 shower shape variable is used in the
trigger to identify photons that convert to an e+e− pair..." This
description (ET 30/18, calo ID "R9Id", isolation, H/E cut, R9-based
conversion tag) matches the literal trigger name's components exactly.
Note: that paper uses the **full 2016 dataset** (35.9 fb⁻¹, Run2016B–H),
not just G+H — our subset is smaller by construction, since only G/H are
on this portal (A.1).

**Is it in the DoubleEG primary dataset?** Yes — read directly from the
file (see Part C.2): of the first 1,000 events in the Run2016G file, 24.6%
have this bit set to `True`, confirming the trigger fires within this
dataset (as expected: DoubleEG carries multiple diphoton/dielectron
triggers, not only this one).

**Is it prescaled?** **UNVERIFIED.** The portal's `prescale_pp2016.csv`
(downloaded, 1,040 lines) records only `(run, lumisection, prescale-index)`
triples — it does not name which HLT path each index refers to, and no
other portal document maps trigger names to prescale-index tables. The
portal therefore does not document this, so per the task's evidence
standard this is left UNVERIFIED rather than asserted from general
knowledge.

---

## Part B — Simulation

All samples below were required to be `RunIISummer20UL16NanoAODv9` **without**
"APV" in the processing tag, and independently confirmed **postVFP** by
reading each record's own `run_period` field, which explicitly lists
`["Run2016G", "Run2016H"]` (verified for every record in this section —
not inferred from the naming convention alone).

### B.1–B.3 — Samples found (mH = 125 GeV unless noted)

| Mode | recid | Dataset (short) | Generator | Events | Files | Size | postVFP confirmed |
|---|---|---|---|---|---|---|---|
| ggH | **37350** | `GluGluHToGG_M-125_TuneCP5...powheg-pythia8` | POWHEG+Pythia8 | 540,000 | 3 | 643 MB | ✅ run_period G+H |
| VBF | **68497** | `VBFHToGG_M125_TuneCP5...amcatnlo-pythia8` | aMC@NLO+Pythia8 | 2,000,000 | 13 | 2.97 GB | ✅ |
| W⁺H | **71013** | `WplusH_HToGG_WToAll_M125...powheg-pythia8` | POWHEG+Pythia8 | 162,000 | 4 | 277 MB | ✅ |
| W⁻H | **70173** | `WminusH_HToGG_WToAll_M125...powheg-pythia8` | POWHEG+Pythia8 | 147,484 | 15 | 284 MB | ✅ |
| ZH (qq̄) | **74132** | `ZH_HToGG_ZToAll_M125...powheg-pythia8` | POWHEG+Pythia8 | 151,002 | 20 | 305 MB | ✅ |
| ggZH (gg, 3 Z-decay modes) | **36617/36623/36611** | `ggZH_HToGG_ZTo{NuNu,QQ,LL}_M125` | POWHEG+Pythia8 | 160,000/157,576/160,000 | 6/9/10 | 243/313/352 MB | ✅ |
| ttH | **67611** | `ttHJetToGG_M125_TuneCP5...amcatnloFXFX-madspin-pythia8` | aMC@NLO FXFX+madspin+Pythia8 | 433,412 | 16 | 1.26 GB | ✅ |
| *(alt.)* combined VH | **69361** | `VHToGG_M125_TuneCP5...amcatnloFXFX-madspin-pythia8` | aMC@NLO+madspin+Pythia8 | 459,295 | 15 | 813 MB | ✅ — **do not use alongside W±H/ZH above, it is an alternative combined sample, not an addition** |

Full metadata (event/file/size counts, DOIs, source URLs) for every record
is in `records.json`.

**All five requested production modes exist in postVFP UL16 NanoAODv9.**
No production mode found here exists *only* as preVFP — the postVFP
version was located for every mode searched (ggH, VBF, WH split by charge,
ZH, ttH, plus the gg-induced ZH component and an alternative combined-VH
sample).

**Consequential naming note:** for W H and Z H, CMS/the portal provide
*both* an inclusive `VHToGG` sample (V → any decay, one combined process)
*and* separate `WplusH_HToGG_WToAll` / `WminusH_HToGG_WToAll` /
`ZH_HToGG_ZToAll` samples. These are two different ways of covering the
same physics — mixing both in one fit would double-count associated
production. This inventory lists the split-by-charge/boson set as the
default recommendation (matches how cross sections are quoted per-mode in
B.4), with the combined `VHToGG` record flagged as the alternative.

### B.3 — Background simulation: what's missing

| Sample | UL16 postVFP NanoAODv9? | recid |
|---|---|---|
| DiPhotonJetsBox, M(γγ)>80 GeV | ✅ | 34121 |
| DiPhotonJetsBox1BJet / 2BJets, M(γγ)>80 GeV | ✅ | 34115 / 34117 |
| GJet, Pt-15to6000 flat (inclusive) | ✅ | 36933 |
| GJet, Pt-20to40, double-EM-enriched, M(γγ)80-Inf | ✅ | 36935 |
| GJet, Pt-20toInf, double-EM-enriched, M(γγ)40-80 | ✅ | 36937 |
| **GJet, Pt-40toInf, double-EM-enriched, M(γγ)>80** | **❌ NOT FOUND in UL16.** Only exists as an older 76X/2015-era MiniAOD sample (recid 16781/16782). | — |
| QCD, Pt-30to40, double-EM-enriched, M(γγ)>80 | ✅ | 63200 |
| QCD, Pt-30toInf, double-EM-enriched, M(γγ)40-80 | ✅ | 63210 |
| **QCD, Pt-40toInf, double-EM-enriched, M(γγ)>80** | **❌ NOT FOUND in UL16.** Only the old 76X sample exists (recid 18346/18347). | — |

Searched with the portal's wildcard search (`q=*<term>*`); absence was
checked by an explicit dedicated search for each missing Pt bin, not
inferred from a partial listing. **Gap:** the highest-Pt GJet/QCD bins used
in some CMS-internal background training sets are not available in UL16 on
this portal; the lower-Pt bins plus the inclusive `GJet_Pt-15To6000-Flat`
sample partially cover the same phase space but not identically.

### B.4 — Cross sections, branching ratio, and events produced

**Source: the official LHC Higgs Cross Section Working Group spreadsheet**
[`Higgs_XSBR_YR4_update.xlsx`](https://twiki.cern.ch/twiki/pub/LHCPhysics/LHCHWG/Higgs_XSBR_YR4_update.xlsx),
linked from the working group's own 13 TeV cross-section page
([CERNYellowReportPageAt13TeV](https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageAt13TeV)).
Downloaded directly (1.1 MB) and read with `openpyxl`; values below are
read from sheet `YR4 SM 13TeV` (production) and `YR4 SM BR` (decay), row
**mH = 125.0 GeV** exactly (not the 125.09 GeV row, to match the round
number most commonly quoted; the 125.09 GeV row differs by <1%).

| Mode | σ [pb] at 13 TeV, mH=125 GeV | Scale uncert. |
|---|---|---|
| ggH (N³LO QCD + NLO EW) | **48.58** | +4.56% / −6.72% |
| VBF | **3.782** | +0.4% / −0.3% |
| WH (total) | **1.3728** | — |
| — W⁺H | 0.8400 | — |
| — W⁻H | 0.5328 | — |
| ZH (incl. gg→ZH = 0.1227 pb) | **0.8839** | +3.8% / −3.1% |
| ttH | **0.5071** | +5.8% / −9.2% |

**BR(H→γγ) = 0.00227** (0.227%) at mH=125.0 GeV, THU uncertainty
+1.73%/−1.72% (sheet `YR4 SM BR`, column ` H → γγ`).

**Number of H→γγ events PRODUCED in Run2016G+H, before any selection
efficiency** (N = σ × BR × L, L = 16.393380531 fb⁻¹ recorded, A.2):

| Mode | N produced (before selection) |
|---|---|
| ggH | **1,808** |
| VBF | **141** |
| WH (W⁺+W⁻) | **51** |
| ZH | **33** |
| ttH | **19** |
| **Total** | **≈ 2,051** |

This is the number of real H→γγ decays that occurred in the recorded
Run2016G+H dataset — not the number that would survive any trigger,
reconstruction, or analysis selection, which is always a further, much
smaller fraction (typically a few tens of percent for a well-designed
H→γγ selection, but that number is not computed here — computing it is
exactly Phase 2.2's job).

### B.5 — Pileup profile

**No dedicated portal record exists.** The portal's own guide,
[`cms-guide-pileup-simulation`](https://opendata.cern.ch/docs/cms-guide-pileup-simulation)
("CMS Pile-up simulation"), states that the **measured-from-data** pileup
distribution is available on an external CMS TWiki page
([`LumiPublicResults`](https://twiki.cern.ch/twiki/bin/view/CMSPublic/LumiPublicResults))
and the **Monte-Carlo generation scenario** numbers on a different external
TWiki page
([`Pileup_MC_Gen_Scenarios`](https://twiki.cern.ch/twiki/bin/view/CMSPublic/Pileup_MC_Gen_Scenarios)) —
neither is hosted as a downloadable portal record with a recid. The usable
substitute confirmed directly in Part C.3: every simulated NanoAOD file
carries its own **`Pileup_nTrueInt`** branch per event (the simulated true
mean number of interactions), which is the quantity actually needed to
reweight simulation to data — read in the signal file, range 5–45, mean
≈21.5 over the sampled 1,000 events.

---

## Part C — What the files actually contain

Two files opened remotely via `uproot` + HTTPS range requests (no full
download): one Run2016G data file
(`.../Run2016G/DoubleEG/.../11DA657F-5262-BD4A-AD1E-8E53BE62A601.root`,
2,014,154 events in the tree, only 1,000 read) and one postVFP ggH signal
file (`.../GluGluHToGG_M-125.../3231834B-7A6E-4840-8627-C97FDCF67268.root`,
533,000 events in the tree, only 1,000 read). Scripts:
`studies/hgg_cms/explore_data_file.py`, `explore_signal_file.py`.

### C.1 — Photon branches (from the data file; identical schema in the signal file)

**Energy corrections — `Photon_eCorr` exists.** Its title, quoted exactly:
> "ratio of the calibrated energy/miniaod energy"

Read over 1,000 events: min 0.983, max 1.027, mean 1.005 — i.e. a few
per-mille to few-percent correction factor centered near 1. **Conclusion:
"corrected".** By NanoAOD convention (and consistent with this title's
wording, "ratio of the calibrated / miniaod energy") `Photon_pt` already
has the calibration applied; `Photon_eCorr` is stored so the correction
can be *undone* if needed, not so it can be applied. This file also has
`Photon_dEscaleUp`/`Photon_dEscaleUp` ("ecal energy scale shifted 1 sigma
up/down") — the data-side scale-uncertainty variation branches — present
in this **data** file, and `Photon_dEsigmaUp`/`Photon_dEsigmaDown` ("ecal
energy smearing value shifted 1 sigma up", both titled "up" verbatim in
the file — likely a copy-paste artifact in the original NanoAOD production,
noted rather than corrected) which are the **MC**-side smearing-uncertainty
variations, also present in this data file (the branches are defined by
the common NanoAOD schema regardless of sample type; their values were not
separately checked for triviality in the data file).

**Identification.** `Photon_cutBased`, title quoted exactly: "cut-based ID
bitmap, Fall17V2, (0:fail, 1:loose, 2:medium, 3:tight)" — an ordinal
integer, not a bitmask despite the name (values 0–3 seen directly: in the
first 1,000 events' photons, counts were `{0: 1721, 1: 112, 2: 43, 3:
310}`). `Photon_mvaID` (float, "MVA ID score, Fall17V2") plus **boolean**
`Photon_mvaID_WP80` and `Photon_mvaID_WP90` flags both exist directly —
no manual score cut needed to use the standard working points.

**Electron veto.** `Photon_electronVeto` (bool, "pass electron veto") and
`Photon_pixelSeed` (bool, "has pixel seed") both exist.

**Shower shape and position.** `Photon_r9` ("R9 of the supercluster,
calculated with full 5x5 region"), `Photon_sieie` ("sigma_IetaIeta ...
full 5x5 region"), `Photon_hoe` ("H over E") all exist. The barrel–endcap
gap is directly resolvable without computing supercluster η by hand:
**`Photon_isScEtaEB`** ("is supercluster eta within barrel acceptance")
and **`Photon_isScEtaEE`** ("is supercluster eta within endcap
acceptance") are both present as ready-made booleans.

**Isolation.** `Photon_pfRelIso03_all` ("PF relative isolation dR=0.3,
total, with rho*EA PU corrections") and `Photon_pfRelIso03_chg` (same,
charged component only) — note the cone size is **dR=0.3** for photons
(distinct from the dR=0.4 muon isolation convention noted elsewhere on
this project).

Full branch-by-branch dump (40 `Photon_*` branches with titles): see
`explore_data_file.py`'s output, reproduced in the commit.

### C.2 — Trigger branches

All `HLT_Diphoton*`/`HLT_DoublePhoton*` branches present in the file:
`HLT_DoublePhoton60`, `HLT_DoublePhoton85`,
`HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90`,
`HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_DoublePixelSeedMatch_Mass70`,
`HLT_Diphoton30PV_18PV_R9Id_AND_IsoCaloId_AND_HE_R9Id_DoublePixelVeto_Mass55`,
`HLT_Diphoton30_18_Solid_R9Id_AND_IsoCaloId_AND_HE_R9Id_Mass55`,
`HLT_Diphoton30EB_18EB_R9Id_OR_IsoCaloId_AND_HE_R9Id_DoublePixelVeto_Mass55`.
**24.6%** of the sampled 1,000 events pass
`HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90` (see A.4).

### C.3 — Signal-file simulation branches

- **`genWeight`**: NOT simple ±1. Values seen: a fixed magnitude of
  **21.6956**, sign-flipped for 3 of the sampled 1,000 events (0.3%
  negative) — the expected pattern for a NLO (POWHEG) generator with a
  small negative-weight fraction.
- **`Pileup_nTrueInt`**: present, title "the true mean number of the
  poisson distribution for this event from which the number of
  interactions each bunch crossing has been sampled"; range 5–45, mean
  ≈21.5 over the sample.
- **LHE/PS weight branches, all present**: `LHEWeight_originalXWGTUP`,
  `LHEScaleWeight` (9 renorm./fact. scale variations, documented per-index
  in the title), `LHEPdfWeight` (103 NNPDF3.0 variations, "LHA IDs 306000 -
  306102"), `PSWeight` (4 ISR/FSR variations).
- **`GenPart_*`**: present (`pt`, `eta`, `phi`, `mass`, `pdgId`, `status`,
  `genPartIdxMother`, `statusFlags` with a documented bit meaning) —
  sufficient in principle to match reconstructed photons to true
  Higgs-decay photons (pdgId 22, mother pdgId 25), though that matching
  itself was not performed here (out of scope: no analysis code).
- **`run`/`luminosityBlock`/`event`**: present, same names/types as in
  data.

### C.4 — Sanity check (not a measurement)

Leading two photons (by `Photon_pt`) in the 1,000 sampled ggH events,
**requiring only ≥2 reconstructed photons and nothing else** (no ID, no
isolation, no trigger, no pT cut): 778/1,000 events had ≥2 photons; their
invariant mass has **mean 124.6 GeV, RMS 27.3 GeV**. The large RMS is
expected and not a problem — with zero selection, this includes photons
from jets, low-pT photons, and wrong pairings; the point of this check is
only that the mean lands close to 125 GeV, confirming the file really
contains H→γγ decays and that the branches used here (`Photon_pt/eta/phi/mass`)
combine correctly into a sensible mass. This is explicitly **not** a
resolution or signal-model measurement.

---

## Part D — What the pipeline on `master` can already do (read-only)

### D.1 — Photon schema in `services/parsing/schemas.py`

Yes, a CMS NanoAOD photon collection is defined, in the `"cms-nanoaod"`
schema entry (`services/parsing/schemas.py:109-130`):
```python
"objects": {
    ...
    "Photons": ["pt", "eta", "phi", "mass"],  # NanoAOD includes Photon_mass
    ...
}
```
**Only 4 fields are read: `pt`, `eta`, `phi`, `mass`.** Every field listed
in Part C.1 as needed for a real selection is **missing** from this
schema: `eCorr`, `cutBased`, `mvaID`/`mvaID_WP80`/`mvaID_WP90`,
`electronVeto`, `pixelSeed`, `r9`, `sieie`, `hoe`, `isScEtaEB`/`isScEtaEE`,
`pfRelIso03_all`/`pfRelIso03_chg`. No trigger (`HLT_*`) branches are read
anywhere in the schema either.

### D.2 — Selection capabilities

A repository-wide search (`grep -rli`, all `.py` files) for each capability
found **zero matches** outside the files written for this inventory:

| Capability | Found? | Evidence |
|---|---|---|
| (a) Golden-JSON / validated-runs filter | **No** | No occurrence of "golden", "validated run(s)", "certified", "Cert_" anywhere in the codebase. |
| (b) Require specific HLT trigger bits | **No** | No occurrence of `HLT_` anywhere in the codebase outside this inventory's own scripts. `NANOAOD_EVENT_ID_BRANCHES` (`schemas.py:45-49`) reads only `run`/`luminosityBlock`/`event`, no trigger branch. |
| (c) Read simulation / keep `genWeight`, pileup | **No** | No occurrence of `genWeight` or `Pileup` anywhere in the codebase outside this inventory's own scripts. |
| (d) Handle the photon barrel–endcap η gap | **No** | No occurrence of `isScEta`, or of the standard EB/EE η boundary values, anywhere in the codebase. |

`services/parsing/event_deduplication.py` does handle a *different* kind
of "trigger" concept — de-duplicating events that fired both an electron
and a muon *primary dataset stream* when combining datasets — this is
unrelated to per-event HLT bit selection and does not provide any of (a)-(d).

### D.3 — Histogram binning: fixed range, configurable width

The histogram range is **hard-coded**, not configurable, in
`services/pipelines/histograms_pipeline.py:22-23`:
```python
FIXED_MASS_MIN_GEV = 0.0
FIXED_MASS_MAX_GEV = 10000.0
```
with the module's own comment explaining why: "Fixed histogram range
eliminates the range pre-scan and ensures that all independently produced
batch histograms have merge-compatible bin edges." The bin **width** is
configurable (`histograms_config["bin_width_gev"]`, default `10.0`,
`domain/config.py:208`, validated only to be `> 0`) and every histogram is
built as `nbins = ceil((10000-0)/bin_width)` (`histograms_pipeline.py:342`,
`379`, `519`, `649`).

**Direct answer:** a fine bin width (e.g. 0.5 or 1 GeV) can be set through
config alone — no code change needed for that. A histogram *restricted* to
100–180 GeV **cannot** be produced through config alone: the range is a
module constant, not read from `histograms_config` or `domain/config.py`
at all. Setting `bin_width_gev=0.5` today would produce a 20,000-bin
histogram spanning the full 0–10,000 GeV range (which contains the 100–180
GeV region as a slice, but is not the same as a purpose-built histogram,
and is 100× larger than necessary for this analysis).

### D.4 — GeV/MeV handling and mass constants

`schema_needs_mev_to_gev_conversion()` (`schemas.py:604-622`) skips the
historical MeV→GeV ×10⁻³ conversion **only** when the schema's
`native_pt_unit` is exactly `"gev"` (case-insensitive). The `"cms-nanoaod"`
schema declares `"native_pt_unit": "GeV"` (`schemas.py:111`) — so **CMS
photons are correctly treated as already-GeV, no incorrect rescaling is
applied.** This was also confirmed independently in Part C: real
`Photon_pt` values read directly from both files are in the 10–800 GeV
range, consistent with GeV, not MeV.

`services/calculations/consts.py` `KNOWN_MASSES`, confirmed unchanged:
```python
KNOWN_MASSES = {
    "Muons": 0.105,
    "Photons": 0.0,
    "Electrons": 0.000511,
    ...
}
```
Muons = 0.105 GeV and Electrons = 0.000511 GeV, as expected. **A photon
mass constant does exist, `"Photons": 0.0`** — correct, since photons are
massless; this is consistent with NanoAOD's own `Photon_mass` branch,
which is included in the same photon schema (D.1) as a formality (its
physical value is 0, or a tiny numerical placeholder) rather than a real
degree of freedom.

---

## Consequential or ambiguous points

1. **Photon energy corrections: `Photon_pt` is corrected, not raw** — the
   single most important finding for the physics result. If this is
   ever second-guessed and someone re-applies `Photon_eCorr` on top of
   `Photon_pt`, every mass and every efficiency number in the analysis
   would be silently wrong. Evidence: `Photon_eCorr`'s own title, "ratio
   of the calibrated energy/miniaod energy" (C.1), and the standard
   NanoAOD convention that `pt`/`mass` branches are the calibrated,
   analysis-ready quantities. **What's still unknown:** whether the exact
   size and direction of this correction (few-per-mille to ~3%, seen
   directly) matches CMS's published photon energy scale/smearing
   corrections for 2016 UL — not cross-checked against a CMS calibration
   document here, out of scope for a read-only inventory.
2. **preVFP/postVFP: not a problem for the 5 requested signal modes** — all
   were found in postVFP UL16 NanoAODv9, confirmed via each record's own
   `run_period: ["Run2016G","Run2016H"]` field, not just inferred from the
   absence of "APV" in the dataset name (B.1–B.2). **What's still
   unknown:** whether every background sample category CMS's own H→γγ
   analyses use (beyond DiPhotonJetsBox/GJet/QCD) is similarly complete —
   only the three families explicitly asked for were checked.
3. **Trigger exists and is directly confirmed in-file**, but its prescale
   status in 2016G/H is UNVERIFIED from portal documentation (A.4). If it
   turns out to have been prescaled in part of Run2016G or H, the
   luminosity actually usable with this trigger is smaller than the raw
   16.39 fb⁻¹ recorded value, and the events-produced number in B.4 would
   need to be scaled down for anything computed *after* the trigger
   requirement (not relevant to the before-selection number reported
   here, which is trigger-independent by construction).
4. **Only G+H is available, not the full 2016 dataset.** The CMS paper
   used as the trigger's physics citation (arXiv:1804.02716) analyzed
   35.9 fb⁻¹ (all of Run2016B–H); this portal only has 16.39 fb⁻¹ (G+H) of
   DoubleEG NanoAOD (A.1). Any comparison to that paper's absolute yields
   or significances must account for this ~2.2× smaller dataset.
5. **`VHToGG` vs. separate `WplusH`/`WminusH`/`ZH_HToGG` samples (B.1)**:
   using both would double-count associated production. This choice has
   not been made yet — it belongs to Phase 2.2.

---

## Gaps

What `master`'s pipeline cannot yet do for this analysis, with a rough size
of the work needed:

| Gap | Size | Notes |
|---|---|---|
| Read the CMS photon ID/isolation/correction branches (D.1) | **Small** | Extend the `"cms-nanoaod"` schema's `"Photons"` field list in `schemas.py`; the fields already exist in the files (C.1), this is a config/schema change, not new parsing logic. |
| Golden-JSON / validated-runs filtering (D.2a) | **Medium** | No existing concept of a run/lumisection filter anywhere in the pipeline; needs a new filter stage reading `Cert_271036-284044_..._JSON.txt` (or an equivalent run/LS range check) before event selection. |
| HLT trigger-bit requirement (D.2b) | **Small–Medium** | The event record already carries `run`/`luminosityBlock`/`event`; adding one more scalar branch (the HLT bool) to the schema and a selection cut is straightforward, but there is currently no "selection cut on a scalar branch" concept at all to hook into — depends on how `event_selection.py` is structured. |
| Keep `genWeight` / `Pileup_nTrueInt` for simulation (D.2c) | **Medium** | Requires the parser to read per-event weights through the whole pipeline (accumulation, histogram filling with weights, not just unweighted counts) — histogramming code was not checked for weight support in this read-only pass, only for range/binning (D.3). |
| Photon barrel–endcap η handling (D.2d) | **Small** | `Photon_isScEtaEB`/`isScEtaEE` already exist as ready-made booleans in the files (C.1); just needs to be added to the schema and used in a selection cut. |
| Fine-binned, restricted-range (100–180 GeV) histogram (D.3) | **Medium** | Requires making `FIXED_MASS_MIN_GEV`/`FIXED_MASS_MAX_GEV` configurable (currently hard-coded module constants), plus deciding how that interacts with the documented cross-batch merge-compatibility guarantee those constants exist to protect. |

---

*Generated for Phase 2.1. Next step (not started here): Phase 2.2 — design
the event selection and the specific pipeline changes above.*
