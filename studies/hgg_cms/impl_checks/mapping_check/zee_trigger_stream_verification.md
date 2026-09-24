# Z->ee trigger-efficiency probe: which primary dataset does HLT_Ele27_WPTight_Gsf belong to?

**Implementation task 6, Part 4 (second revision, 16 Sep 2026).**

## The problem

`config.cms_hgg_zee_data.yaml` read the DoubleEG primary dataset (records
30521, 30554). In DoubleEG, an event is present ONLY if it fired one of
DoubleEG's own streaming triggers -- so "HLT_Ele27_WPTight_Gsf fired"
events within DoubleEG are not a fair, unbiased single-electron-triggered
sample: they are conditioned on ALSO having fired a DoubleEG streaming
trigger (very plausibly the diphoton path itself, for many of them).
That would bias the trigger-efficiency measurement upward (since a
diphoton-fired event automatically "counts" once found in this subset)
and could still leave Mass90 sculpting in the "energy scale" sample,
since DoubleEG-resident Ele27 events would disproportionately include
ones that ALSO passed the diphoton path.

## Evidence: which HLT paths define which primary dataset (2016, UL16 NanoAODv9)

**Source**: the CERN Open Data Portal's own record API metadata
(`https://opendata.cern.ch/api/records/<id>`) for each of the four
records this task uses -- every `HLT_*` token appearing anywhere in a
record's own metadata was extracted and counted (16 Sep 2026):

| record | dataset | unique HLT_ tokens | has `HLT_Ele27_WPTight_Gsf` | has `HLT_Diphoton30_18_..._Mass90` |
|---|---|---:|:---:|:---:|
| 30521 | `/DoubleEG/Run2016G-.../NANOAOD` | 41 | **NO** | YES |
| 30554 | `/DoubleEG/Run2016H-.../NANOAOD` | 41 | **NO** | YES |
| 30529 | `/SingleElectron/Run2016G-.../NANOAOD` | 50 | **YES** | NO |
| 30562 | `/SingleElectron/Run2016H-.../NANOAOD` | 50 | **YES** | NO |

The full 41-path DoubleEG list (record 30521) is dominated by diphoton,
double-electron, and photon paths -- e.g. `HLT_Diphoton30_18_R9Id_OR_
IsoCaloId_AND_HE_R9Id_Mass90`, `HLT_DoubleEle33_CaloIdL`,
`HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL`, `HLT_DoublePhoton60` -- plus a
handful of single-electron-PLUS-jet compound paths (e.g.
`HLT_Ele12_CaloIdL_TrackIdL_IsoVL_PFJet30`) and one single-electron-plus
-mass path (`HLT_Ele27_HighEta_Ele20_Mass55`) -- but never the bare
`HLT_Ele27_WPTight_Gsf`. The portal's own record page states plainly:
"Events stored in this primary dataset were selected because of the
presence of different combinations of energetic photons, electrons
and/or jets" (record 30521's own description text).

**Conclusion, matching the task's own claim exactly, no contradiction
found**: `HLT_Ele27_WPTight_Gsf` belongs to the SingleElectron primary
dataset in 2016, not DoubleEG; DoubleEG is defined by diphoton/double
-electron/photon paths (never bare single-electron paths).

## File-level confirmation (metadata-only reads, not just portal documentation)

Opened one real file from each of 30529 and 30562 directly (via HTTPS,
`Events` tree branch listing only -- no event data read):

| record | file | branches | `HLT_Ele27_WPTight_Gsf` | diphoton Mass90 branch | `Photon_electronVeto` |
|---|---|---:|:---:|:---:|:---:|
| 30529 (SingleElectron G) | `43B00DA0-....root` | 1,339 | present | present | present |
| 30562 (SingleElectron H) | `02A9B576-....root` | 1,347 | present | present | present |

Both trigger bits AND `Photon_electronVeto` exist as branches in
SingleElectron's own files (NanoAOD's HLT branch menu is centrally
defined across primary datasets sharing the same production campaign --
branch PRESENCE does not depend on which trigger(s) actually streamed a
given event into a given PD; only which EVENTS are present does). This
is what makes the fix work: SingleElectron's Ele27-fired subset is an
unbiased single-electron-triggered sample, and the diphoton bit -- read
here via `extra_scalar_branches`, not `trigger_requirements` -- is
available to check (never to filter on) for every one of those events.

## File counts, event totals, dataset names (portal API, 16 Sep 2026)

| record | dataset | NanoAOD version | files | events |
|---|---|---|---:|---:|
| 30529 | `/SingleElectron/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` | UL2016_MiniAODv2_NanoAODv9-v1 (same as DoubleEG) | 71 | 153,363,109 |
| 30562 | `/SingleElectron/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` | UL2016_MiniAODv2_NanoAODv9-v1 (same as DoubleEG) | 80 | 129,021,893 |
| **Total** | | | **151** | **282,385,002** |

Frozen file lists (same pattern as `cms_hgg_data_file_lists.json`):
`cms_zee_singleelectron_data_file_lists.json`.

## Certified-run coverage: does SingleElectron match DoubleEG?

Compared each record's own `run_numbers` metadata field against the
golden JSON (`Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`),
restricted to the G (278820-280385) and H (280919-284044) run-number
ranges:

| era | golden-certified runs | in DoubleEG | in SingleElectron | missing from either |
|---|---:|---:|---:|---|
| G | 70 | 70/70 | 70/70 | none |
| H | 86 | 86/86 | 86/86 | none |

**Every golden-certified run in both eras is present in BOTH datasets'
raw run lists -- identical certified-run coverage.** (SingleElectron-H's
raw run list has 2 extra runs, 283675/283676, that DoubleEG-H's does not
-- but neither is golden-certified, so this doesn't affect the certified
-run comparison at all; noted for completeness.) The luminosity total
this task otherwise uses (16.393380531 fb⁻¹) is DoubleEG's own recorded
luminosity and is NOT reused for anything computed from SingleElectron in
this task's actual analysis code -- the energy-scale and trigger
-efficiency checks are shape/fraction comparisons, needing no absolute
luminosity; only the (separate, DY-simulation-based) electron-veto
-leakage estimate uses 16.393380531 fb⁻¹, and that normalizes against
DoubleEG's own luminosity as before, unaffected by this change. This
run-coverage check is therefore reported for due diligence (confirming
`validated_runs_json` behaves consistently across both datasets), not
because a SingleElectron-specific luminosity number is needed anywhere.

## Overlap note (task's item 5)

SingleElectron and DoubleEG are NOT mutually exclusive at the event
level in general -- a real event that fires both an Ele27-class trigger
AND a DoubleEG streaming trigger could, in principle, appear in both
primary datasets' own recorded files (CMS's streaming is "OR of this
PD's triggers", not partitioned). **This does not matter for this task**:
the Z->ee control-region study (this file) is an entirely separate
sample from the H->gamma-gamma main analysis (which never reads
SingleElectron at all), so there is no double-counting risk within
either analysis. Stated here explicitly, as asked, not because it
changes anything in this task's own design.
