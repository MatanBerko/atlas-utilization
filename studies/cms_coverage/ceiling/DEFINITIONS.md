# Ceiling task — new object/dataset definitions

New files only, under `studies/cms_coverage/ceiling/`. This document records
every definition this task adds (photons, taus, MET) that did not exist in
`studies/m0m1j0_cms/selection.py`, with its source and the real branch
evidence behind it. **None of this has supervisor sign-off yet** — that is
explicit throughout, per the task's own instruction.

Everything else (electron/muon/jet/b-jet definitions, golden JSON, each
dataset's trigger, the 10 GeV/0-10 TeV grid, post-processing, BumpNet's
`>=100 events`/`>30 bins` thresholds) is unchanged from
`studies/cms_coverage/per_dataset/triggered/` and is not re-derived here.

## Photons

**Definition reused verbatim from this codebase's own H→γγ production
recipe** (`config.cms_hgg_data.yaml:279-284`, byte-identical blocks also in
every `config.cms_hgg_signal*.yaml`), not invented fresh for this task:

```yaml
kinematic_cuts:
  photons:
    pt: {min: 20.0}
    bool_require: [electronVeto, mvaID_WP90]
    bool_any_of: [isScEtaEB, isScEtaEE]
```

- **pT > 20 GeV.**
- **`Photon_mvaID_WP90`** — real branch title, quoted verbatim from a real
  2016G DoubleMuon NanoAOD file (this task, 2026-09-26):
  *"MVA ID WP90, Fall17V2"*. Cut-based `Photon_cutBased` exists too
  (*"cut-based ID bitmap, Fall17V2, (0:fail, 1:loose, 2:medium, 3:tight)"*)
  but the MVA WP90 working point is what the team's own hgg pipeline
  already chose and verified — reused here for consistency rather than
  picking a different, unverified cut-based WP myself.
- **`Photon_electronVeto`** — real branch title: *"pass electron veto"*.
  Rejects electrons misreconstructed as photons.
- **Barrel/endcap gap**: `bool_any_of: [isScEtaEB, isScEtaEE]`, NOT a plain
  `|eta|` window. `docs/CMS_KNOWN_LIMITATIONS.md` ("The CMS barrel/endcap
  acceptance gap") already measured, on real files, that this pair of flags
  enforces CMS's true supercluster-eta acceptance (barrel OR endcap, gap and
  outer edge both excluded) and that a plain momentum-`eta` cut would be
  wrong for this purpose. Reused directly rather than re-measured.
- **Implementation**: `select_photons_precleaning` in `objects.py` builds a
  `{"Photons": ...}`-wrapped record from the real branches and calls the
  real, unmodified `services.calculations.physics_calcs.filter_events_by_kinematics`
  with exactly this `kinematic_cuts` block — the same shared function this
  config already exercises in production, not a re-implementation.

**Needs supervisor confirmation**: reusing the hgg pipeline's photon
definition for a BumpNet-menu context is a reasonable default (it is the
only vetted CMS photon recipe already in this codebase) but was not chosen
*for* BumpNet — flagging explicitly, per the task's instruction.

### Photon-jet (and photon-lepton) overlap — the artifact this task was asked to measure

`docs/CMS_KNOWN_LIMITATIONS.md` ("Object overlap") already documents, as of
2026-09-03, that CMS NanoAOD reconstructs the same calorimeter cluster as an
electron, a photon, *and* a jet with no cleaning applied anywhere in this
pipeline, and that adding delta-R cleaning was explicitly left as **"a
future decision"** (tau overlap specifically: discussed with Maryna,
"intentionally deferred"). This task's own instructions require exactly
that: ΔR<0.4 cleaning against selected leptons AND jets, with the fraction
removed measured and reported — i.e., this measurement is what that
deferred decision needs. Overlap removal and its diagnostics are new code
(`objects.py`'s `overlap_removal`), using the same ΔR<0.4 threshold already
established for jet-lepton cleaning
(`studies/m0m1j0_cms/selection.py:JET_LEPTON_CLEAN_DR`). Measured fractions
are reported in `CEILING_REPORT.md`, not asserted here.

## Taus

**No existing CMS recipe in this codebase** (unlike photons) — every
existing `taus:` kinematic-cuts block in this repo is ATLAS-side
(`config.yaml`, `config.atlas_scale_test.yaml`), and CMS's own
`config.yaml:112` sets `particle_counts.taus: {min: 0, max: 0}`, i.e. taus
are switched off entirely, for reasons unrelated to physics (see this
task's own brief). The definition below is proposed fresh for this task,
using standard CMS tau-POG quantities already declared in the CMS schema
(`services/parsing/schemas.py`) and confirmed present in a real file.
**Explicitly flagged as needing supervisor confirmation** — there is no
prior in-repo precedent to defer to, unlike photons.

- **pT > 20 GeV, |eta| < 2.3** (standard CMS PF-tau tracking acceptance;
  the file's own preselection, `nTau`'s doc string, already requires
  `pt > 18`, so this is a small tightening, not a loosening).
- **`Tau_idDeepTau2017v2p1VSjet`**, real branch title (quoted verbatim,
  same file as above): *"byDeepTau2017v2p1VSjet ID working points
  (deepTau2017v2p1): bitmask 1 = VVVLoose, 2 = VVLoose, 4 = VLoose, 8 =
  Loose, 16 = Medium, 32 = Tight, 64 = VTight, 128 = VVTight"*. **Medium**
  WP used (bit 16).
- **`Tau_idDeepTau2017v2p1VSe`** (*"byDeepTau2017v2p1VSe ID working points
  ... same bitmask scale"*): **VVLoose** WP used (bit 2) — the standard
  pairing with a Medium VSjet WP in CMS tau-POG recommendations, loose
  because electron fakes are already suppressed upstream by object
  selection elsewhere in this pipeline.
- **`Tau_idDeepTau2017v2p1VSmu`** (*"byDeepTau2017v2p1VSmu ID working
  points: bitmask 1 = VLoose, 2 = Loose, 4 = Medium, 8 = Tight"*):
  **Tight** WP used (bit 8).
- **`Tau_idDecayModeOldDMs`** (*"tauID('decayModeFinding')"*): required
  `True`. (Note: the file's own preselection already requires
  `decayModeFindingNewDMs` at the `nTau` skim level — see `nTau`'s doc
  string quoted in full below — so this is a second, old-DM decay-mode
  requirement on top of what is already baked in, standard practice when
  combining old+new DM finding.)
- **Overlap removal**: same ΔR<0.4 cleaning against selected leptons and
  jets as photons, same new `overlap_removal` helper, same reason
  (`docs/CMS_KNOWN_LIMITATIONS.md`'s already-flagged, already-discussed
  tau-jet overlap deferral — "taus ARE jets to first order" per this task's
  own brief, so a large fraction is expected here and will be reported
  plainly, not treated as a bug).

Real `nTau` doc string (context for why `pt>18`/NewDMs are already implicit
in every tau read from this file, quoted verbatim): *"slimmedTaus after
basic selection (pt > 18 && tauID('decayModeFindingNewDMs') &&
(tauID('byLooseCombinedIsolationDeltaBetaCorr3Hits') ||
(tauID('chargedIsoPtSumdR03')+max(0.,tauID('neutralIsoPtSumdR03')-0.072*tauID('puCorrPtSum'))<2.5)
|| tauID('byVVVLooseDeepTau2017v2p1VSjet')))"*.

## MET (missing transverse energy) — mass-variant only, not a 7th object type in combinatorics

**From the BumpNet paper** (arXiv:2501.05603, §2.2.2, verbatim, already
established earlier in this task): the paper's "MassMET" variant computes
the same invariant mass as the ordinary combination but including "the
missing transverse energy four-momentum, with the E_T^miss longitudinal
momentum component (p_z) and mass both set to zero."

**From the shared code**: `services.calculations.im_calculator.IMCalculator`
/ `services.calculations.physics_calcs.concat_events` builds each object's
four-vector as `vector.zip({"pt", "phi", "eta", "mass"})` directly from
whatever `pt`/`eta`/`phi`/`mass` fields that object's own array carries (or
`consts.KNOWN_MASSES` for `mass`, only when a `mass` field is genuinely
absent). Representing MET as `{pt: MET_pt, eta: 0.0, phi: MET_phi, mass:
0.0}` therefore needs **zero changes** to `IMCalculator` or the pipeline:
`eta=0` forces `pz = pt*sinh(0) = 0` exactly under this same convention, and
`mass=0` is set directly.

**`services.calculations.combinatorics.get_all_combinations`'s `min_count`/
`max_count` apply globally across all `object_types`**, with no way to cap
one type (MET) at exactly 1 while allowing others up to 4 — so MET cannot
be passed as an ordinary 7th entry in `object_types`. Resolved with new
(not shared) code, `objects.py`'s `build_met_pseudo_object` +
`add_met_variants`: MET is built as a length-1-per-event jagged pseudo-
collection (`METObject`), and for C5 every combination dict already
produced by the real, unmodified `get_all_combinations()` is duplicated
with a `"METObject": (1, 0)` entry appended — both the original and the
+MET variant are kept, through the same unmodified
`prepare_im_combination_name` / `_calculate_combination_invariant_mass` /
`IMCalculator` call path every other combination already uses.

**MET has no mass branch at all** in the real file checked (`MET_pt`,
`MET_phi`, `MET_sumEt`, `MET_significance`, `MET_covXX/XY/YY` — no
`MET_mass`), consistent with treating it as a massless pseudo-object rather
than needing to override a real mass value.

## New datasets: Tau and MET primary datasets

Per this task's instruction to add Tau and MET (one file each) once
taus/MET become meaningful object types. Record IDs (Run2016G, matching the
Run2016G choice already used for all 6 existing datasets), from
`studies/cms_coverage/portal_raw/data_table_raw.json`:

| Dataset | Record ID | Title |
|---|---|---|
| Tau | 30532 | `/Tau/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` |
| MET | 30526 | `/MET/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` |

**Tau PD trigger**: `HLT_DoubleMediumIsoPFTau35_Trk1_eta2p1_Reg` OR
`HLT_DoubleMediumIsoPFTau40_Trk1_eta2p1_Reg` (both real branches, confirmed
present in the file checked). This is the standard CMS Run2016 di-tau
*analysis* trigger (the reference ditau path used across CMS 2016 tau-pair
analyses); OR'ing the 35/40 GeV thresholds mirrors this task's own
established practice of OR'ing two paths across the 2016G/2016H menu
transition (same pattern as SingleMuon/DoubleMuon in the triggered run).
**No prescale information is available from NanoAOD** — this trigger is
*believed* unprescaled by standard CMS-analysis convention, but that is
**UNVERIFIED**, same caveat class this task's brief already applies to
JetHT/MET.

**MET PD trigger**: `HLT_PFMET170_HBHECleaned` OR `HLT_PFMET170_NotCleaned`
(both real branches, confirmed present). ~170 GeV single-MET triggers are
the standard reference unprescaled MET path for 2016 CMS analyses (mono-X,
etc.); OR'ing the two ~170 GeV cleaning variants for the same
menu-robustness reason as above. **Prescale UNVERIFIED from NanoAOD** —
same caveat.

Both choices are reported, not asserted as fact — see `CEILING_REPORT.md`'s
caveats section.
