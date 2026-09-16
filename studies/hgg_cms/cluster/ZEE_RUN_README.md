# Z->e+e- control-region run: what it is, what it costs, how to launch it

**Implementation task 6, Part 4 -- REVISED TWICE, 16 Sep 2026. NOT
SUBMITTED. This task does not run `submit_zee.sh` -- prepared only.**

## Revision 1: Mass90 trigger sculpting the Z peak

The original design filtered BOTH configs on ONLY
`HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90`. That trigger's
own online **Mass90** requirement cuts straight through the Z peak
(91.19 GeV) -- it sculpts the LOWER half of the peak, and there is no
guarantee simulation's own trigger emulation reproduces the real
hardware's turn-on shape there precisely. That would have biased exactly
the peak-position/width comparison this sample exists to make, silently.

**Fix**: filter on EITHER trigger firing, and store BOTH trigger bits per
selected event, so three non-overlapping sub-samples can be carved out
OFFLINE (analysis code, not separate cluster runs) from ONE stored table.

## Revision 2: DoubleEG doesn't contain HLT_Ele27_WPTight_Gsf as its own trigger

`config.cms_hgg_zee_data.yaml` still read DoubleEG (records 30521,
30554) -- the SAME records the main H->gamma-gamma analysis reads. In
DoubleEG, an event is present ONLY if it fired one of DoubleEG's OWN
streaming triggers. **`HLT_Ele27_WPTight_Gsf` is not one of them** --
verified directly against the CERN Open Data portal's own record
metadata (16 Sep 2026, no contradiction found):

| record | dataset | unique `HLT_*` paths | has `HLT_Ele27_WPTight_Gsf` | has the diphoton Mass90 path |
|---|---|---:|:---:|:---:|
| 30521 / 30554 | DoubleEG G/H | 41 | **NO** | YES |
| 30529 / 30562 | SingleElectron G/H | 50 | **YES** | NO |

So "Ele27 fired" events found *within DoubleEG* are not an unbiased
single-electron-triggered sample -- they are conditioned on ALSO having
fired a DoubleEG streaming trigger (very plausibly the diphoton path
itself, for many of them). That biases the trigger-efficiency measurement
upward, and could still leave Mass90 sculpting in the "energy scale"
sample despite Revision 1's fix. Full evidence (portal HLT-path lists,
direct file-level branch checks, certified-run-coverage comparison):
`studies/hgg_cms/impl_checks/mapping_check/
zee_trigger_stream_verification.md`.

**Fix**: the data config now reads **SingleElectron** (30529 Run2016G +
30562 Run2016H, 151 files) instead of DoubleEG, and filters on
`HLT_Ele27_WPTight_Gsf` ALONE -- an unbiased single-electron sample by
construction, since this IS the dataset that trigger defines. The
diphoton bit is still recorded (via `extra_scalar_branches`, never
filtering on it).

**Certified-run coverage matches DoubleEG exactly** (due diligence, not
because this task's own formulas need SingleElectron's luminosity --
see below): every one of the 70 (G) / 86 (H) golden-certified runs is
present in BOTH datasets' own run lists, zero missing either direction.

**Overlap note (stated explicitly, as asked)**: SingleElectron and
DoubleEG are not mutually exclusive at the event level in general -- the
same real collision event could in principle appear in both primary
datasets' own files. This does not matter here: the Z->ee study is an
entirely separate sample from the H->gamma-gamma main analysis (which
never reads SingleElectron at all), so there is no double-counting risk
within either analysis.

## What this measures

Validates the photon-energy modeling used everywhere in the H->gamma-gamma
analysis, by reconstructing Z->e+e- decays THROUGH THE SAME photon object
collection -- the identical method the reference paper itself uses
(arXiv:1804.02716, Table 2): take the normal photon selection, but invert
the electron veto (`Photon_electronVeto == False`), keep the same
trigger-mimicking cuts, and look for a pair mass near the Z boson
(91.19 GeV, PDG) instead of the Higgs.

**PRE-SET agreement criteria (stated here BEFORE any pilot has run --
do not change after seeing results)**, per category (EBEB / notEBEB):
- **Peak position**: data vs DY within **0.5% relative**.
- **sigma_eff68 (width)**: data vs DY within **10% relative**.

(These are the values used by `studies/hgg_cms/validation/zee/common.py`'s
`PEAK_POSITION_AGREEMENT_REL_TOL` / `SIGMA_EFF_AGREEMENT_REL_TOL`
constants -- the analysis code and this document are kept in sync by
definition, not by hand.)

## The three offline sub-samples

| sub-sample | cut | dataset(s) | purpose |
|---|---|---|---|
| (a) energy scale | Ele27 fired, 70-110 GeV | data + DY | peak/width, unbiased by construction |
| (b) trigger efficiency | Ele27 fired, m_ee > 95 GeV | data + DY | diphoton-bit-fired fraction, per category |
| (c) sculpting demo | diphoton fired, Ele27 NOT fired, 70-110 GeV | **DY only** | shows the Revision-1 bug directly, not a pass/fail check |

**Why (c) is DY-only**: data's own config filters on `HLT_Ele27_WPTight_Gsf`
ALONE, so by construction EVERY stored data event already has Ele27
fired -- there is no "diphoton fired, Ele27 NOT fired" data population
left at all. DY's config deliberately keeps the BROADER "either trigger"
filter (simulation has no dataset-streaming bias to worry about, so
there was never a reason to narrow it there -- see
`config.cms_hgg_zee_dy.yaml`'s own comment), so DY alone retains both
populations this demonstration needs.

## The stored mass window: 60-180 GeV, justified

One stored window covers sub-samples (a)/(b) from a single parsing pass
-- see `studies/hgg_cms/zee_selection.py`'s own module docstring for the
full reasoning; summary:
- **Lower bound (60 GeV)**: comfortably below the Z lineshape's own tail,
  standard for a Z-window control sample.
- **Upper bound (180 GeV)**: matches the main H->gamma-gamma analysis's
  own upper mass edge -- wide enough to see the FULL shape of the Mass90
  -sculpting demonstration (undepleted spectrum well above the ~90 GeV
  depletion region, DY-only, see above) and to let this sample's
  high-mass tail be compared against the main analysis's own 135-180 GeV
  sideband background composition, useful context for the electron-veto
  -leakage estimate below. No task need here goes above 180 GeV.

**No H->gamma-gamma blinding exposure -- stated explicitly**: the 60-180
GeV window numerically overlaps the H->gamma-gamma blind window
(115-135 GeV), but this is NOT the H->gamma-gamma signal region. This
sample's leading pair is built from `electronVeto == False` photons; the
main analysis's own diphoton candidate requires `electronVeto == True`.
A photon cannot satisfy both simultaneously, so these are two
disjoint-by-construction candidate objects. The stored field is named
`m_ee`, never `m_gg`, specifically so this sample can never be confused
with (or accidentally read by tooling expecting) H->gamma-gamma
signal-region data.

## The electron-veto leakage estimate (item 3)

**Question**: how many real Z->e+e- events could leak into the
H->gamma-gamma sample's flagged 100-105 / 105-115 GeV excess (Part B of
`VALIDATION_REPORT_1.md`, ~1,604 events in 100-105 vs. the power-law
extrapolation) via electron-veto INEFFICIENCY -- i.e. a real electron
that, despite being a real electron, happens to pass `electronVeto ==
True` and sneaks into the main analysis's own selection? DY simulation
(`DYJetsToLL_M-50`, generated at parton level with M>50 GeV, no upper
cut) genuinely contains real electron pairs with true mass well above
the Z pole via the off-shell Drell-Yan continuum tail -- a real,
calculable background source, not just a mismeasurement of the on-peak
sample. Unaffected by Revision 2 (this estimate is entirely DY-side).

**Design choice: one pass, not a second job.** This needs
veto-**passing** (`electronVeto == True`) DY events run through the REAL
main H->gamma-gamma selection -- the opposite subset from this sample's
own Z->ee output. Two ways to get this:
  (A) a completely separate DY-only cluster job applying
      config.cms_hgg_signal-style settings to record 35669, or
  (B) compute it in the SAME pass as the Z->ee job, since
      `config.cms_hgg_zee_dy.yaml` already reads `electronVeto` on every
      photon and does NOT filter on it at parsing time -- both subsets
      (`==True` and `==False`) are already sitting in memory for every
      chunk.

**Chose (B)** -- `run_zee_selection_on_chunks.py`'s
`compute_hgg_veto_leakage()` filters photons to `electronVeto == True`,
swaps them in for `Photons` (`ak.with_field`), and calls
`studies.hgg_cms.selection.select_diphoton_events` UNMODIFIED (the exact
same function real H->gamma-gamma signal jobs call) on the SAME
already-parsed chunk. Justification: (i) zero additional cluster jobs,
files, or network reads -- the same 41 DY files are already being read
once for the Z->ee output; (ii) `electronVeto` is already a parsed field
in these chunks precisely because it's NOT filtered at parsing time here;
(iii) a separate DY-only job would re-download and re-parse the same 41
files a second time for a result computable for free from data already
in memory. The per-window cutflow (`sum_genWeight_100_105`/`105_115`) is
written into each DY job's own `job_metadata.json` under
`hgg_veto_leakage_estimate`, summed across all 41 job directories by
`studies/hgg_cms/validation/zee/hgg_leakage_estimate.py`, and normalized
as:

```
N_expected = DY_CROSS_SECTION_PB * 1000 (pb->fb) * L_fb=16.393380531 *
             (sum_genWeight_selected_in_window / genEventSumw_over_processed_DY_files)
```

(no branching-ratio factor -- `DYJetsToLL_M-50` is the full leptonic
process already, unlike H->gamma-gamma's BR(H->gg)=0.00227 factor).

**DY cross section: 6077.22 pb, cited, not independently re-derived.**
The standard NNLO cross section widely used across public CMS Run 2 Ultra
Legacy analysis frameworks for exactly this dataset name
(`DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8`, record 35669) --
confirmed via the PocketCoffea analysis framework's own dataset
cross-section table (pocketcoffea.readthedocs.io/en/stable/datasets.html),
cross-checked for consistency against the (older-tune, same process)
RazorAnalyzer public `xSections.dat` value (1921.8*3 = 5765.4 pb -- same
order of magnitude; tune does not change the hard-process cross section).
**The CERN Open Data portal's own record 35669 metadata does NOT state a
cross section** (checked directly, both the record's own `metadata`
object and its McM generator-fragment reference,
`EGM-RunIISummer20UL16wmLHEGEN-00003` -- neither has one). This value is
therefore UNVERIFIED beyond the citation above -- not re-derived from a
first-principles NNLO/FEWZ calculation in this task.

## What the shared pipeline supports here, without any shared-code change

- **Electron-veto inversion**: `kinematic_cuts.bool_require` only
  supports "must be True"; `electronVeto` is simply omitted from it, and
  `studies/hgg_cms/zee_selection.py` applies the inversion at the
  analysis layer.
- **Recording the diphoton bit without filtering on it (data, and DY's
  own parity choice re: this mechanism)**: `parsing_task_config.
  extra_scalar_branches` (an existing, generic "attach this branch,
  don't filter on it" mechanism, `domain/config.py`) -- used by the data
  config, since its `trigger_requirements` now filters on Ele27 alone.
- **Storing both trigger bits when BOTH are meant to filter (DY only)**:
  DY's config instead lists both paths directly under
  `trigger_requirements.paths` (`mode: any`) -- `services/parsing/
  trigger_requirements.py`'s own "Trigger" scalar-branch-group mechanism
  attaches every listed path as an output field regardless of which one
  contributed to an event passing the "any" filter. DY needs this
  broader filter (not just the attachment) to retain the "diphoton
  fired, Ele27 not fired" population sub-sample (c) needs -- see "Revision
  2" and `config.cms_hgg_zee_dy.yaml`'s own comment.
- **cern_input_files logging** (task 1's fact-5 improvement): unchanged,
  via `studies.hgg_cms.output.write_metadata`'s optional parameter.

**Nothing here needed a shared-pipeline change.**

## Job counts (REVISED: SingleElectron, not DoubleEG)

| variant | dataset | files |
|---|---|---:|
| `data_<mode>` | SingleElectron (30529 G + 30562 H) | **151** |
| `dy_<mode>` | DYJetsToLL_M-50 (record 35669) | 41 |

`--pilot`: 2 data + 2 DY subjobs = **4 total**.
`--full`: 151 + 41 = **192 total**.

Frozen expected file list (same pattern as the main run's own
`cms_hgg_data_file_lists.json`): `studies/hgg_cms/impl_checks/
mapping_check/cms_zee_singleelectron_data_file_lists.json`.

## Resource estimate (UNVERIFIED -- no Z->ee-specific pilot has run)

`pbs_hgg_zee_array.sh` reuses the main run's own MEASURED DoubleEG
per-file numbers (mem=5gb, walltime=01:00:00 -- worst observed ~3 min
wall / 2.37 GB peak on a ~2,014,154-event file). SingleElectron's own
average per-file event count is somewhat HIGHER than DoubleEG's:
282,385,002 events / 151 files ~= 1.87M/file vs. DoubleEG's
164,185,704 / 133 ~= 1.23M/file (**~52% more per file on average**,
portal API numbers, 16 Sep 2026) -- still the same order of magnitude as
the single file the mem/walltime numbers were measured on, kept as-is,
but flagged explicitly rather than silently assumed to have enough
margin. DY's own per-file event count (~1.75M average, record 35669) is
unaffected by this revision. The only extra per-file work is the DY-only
electron-veto-leakage computation (a second application of the same
formulas to data already in memory, not a second file read).
**Strongly recommend `--pilot` first** (4 subjobs) and re-check real
`qstat -fx` numbers before `--full`.

**Runtime**: with enough free `shortE`-queue slots to run most of the 192
subjobs concurrently, wall-clock completion in well under an hour is
plausible; if queue-limited, up to ~192 x 3 min = ~9.6 hours of
CUMULATIVE compute (not necessarily wall-clock) in the worst case.

**Output size**: same rough, UNVERIFIED order-of-magnitude reasoning as
before (a few hundred MB, well under any quota) -- SingleElectron's
somewhat larger per-file event count (above) could push this up
mildly, but not by an order of magnitude; re-check against the pilot's
own real numbers before trusting it for the full submission.

## Launch steps (when you decide to actually run this)

```bash
ssh wipp-home
cd ~/atlas-utilization
git fetch origin && git checkout feature/hgg-selection-and-output && git pull

# 1. Pilot first (4 subjobs) -- strongly recommended before --full.
bash studies/hgg_cms/cluster/submit_zee.sh --pilot
bash studies/hgg_cms/cluster/status_zee.sh --mode pilot
# once both show finished_ok: inspect real walltime/mem with
#   qstat -fx <jobid> for a couple of the pilot subjobs
# and re-check pbs_hgg_zee_array.sh's mem/walltime against them.

# 2. The real run (192 subjobs) -- only after the pilot looks right.
bash studies/hgg_cms/cluster/submit_zee.sh --full
bash studies/hgg_cms/cluster/status_zee.sh --mode full

# 3. Merge both variants (once status_zee.sh shows everything finished OK):
mkdir -p /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged
python studies/hgg_cms/cluster/merge_zee_outputs.py \
    --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/data_full \
    --total-batches 151 \
    --expected-json studies/hgg_cms/impl_checks/mapping_check/cms_zee_singleelectron_data_file_lists.json \
    --merged-out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/zee_data.root \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/merge_summary_zee_data.json

python studies/hgg_cms/cluster/merge_zee_outputs.py \
    --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/dy_full \
    --total-batches 41 \
    --expected-json studies/hgg_cms/impl_checks/mapping_check/cms_zee_dy_file_list.json \
    --merged-out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/zee_dy.root \
    --out /storage/agrp/berkom/atlas-utilization/output/hgg_zee/merged/merge_summary_zee_dy.json

# 4. Copy zee_data.root + zee_dy.root + both merge_summary_*.json to your
#    laptop (same scp pattern as the full run's own handover), set
#    HGG_ZEE_MERGED_DIR to that folder, then:
python -m studies.hgg_cms.validation.zee.energy_scale
python -m studies.hgg_cms.validation.zee.trigger_efficiency
python -m studies.hgg_cms.validation.zee.mass90_sculpting_demo
python studies/hgg_cms/validation/zee/hgg_leakage_estimate.py \
    --dy-jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_zee/dy_full
#    (hgg_leakage_estimate.py reads each DY job's own job_metadata.json
#    directly -- run it on the cluster, or against a local copy of
#    dy_full/ if you'd rather not re-download 41 jobs' worth of logs.)
```

DRY_RUN=1 works the same way as `submit_full.sh` (prints every `qsub`
command instead of submitting) for either `--pilot` or `--full`.
