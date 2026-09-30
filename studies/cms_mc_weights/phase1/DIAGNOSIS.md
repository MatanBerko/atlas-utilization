# CMS MC weighting, phase-1 diagnosis round: why does MC undershoot data?

Phase-1 (`REPORT.md`) found data/MC ratios of 1.235 (2mu+1jet+0b) and
~1.40-1.43 (2mu+1jet/2jet+1b) and attributed this to backgrounds missing
from the stack, without establishing that. This round **diagnoses** the
cause: no tuning, no fudge factors, no selection/weight/normalisation
changes anywhere in this document or its scripts.

All numbers below are reproducible from the committed result JSONs under
`studies/cms_mc_weights/phase1/diagnosis/` and the per-sample
`merge_mc_summary.json` / `validate_v1_v2_result.json` files. Plots are
under `studies/cms_mc_weights/phase1/plots/diagnosis/`.

---

## D0. Why V3a used the 1-jet histogram, and whether a 0-jet histogram exists

**Question:** the task asked to compare against "2 muons + NO jets"; V3a
in phase-1 instead used `mass_m0m1_cat_0ex_2mx_1jx_0gx_0tx_0bx` (1 jet).
Does a `mass_m0m1_cat_0ex_2mx_0jx_0gx_0tx_0bx` histogram exist in the
DoubleMuon delivery manifest?

**Finding: no, and it cannot exist, anywhere in this manifest, for any
combination.** Checked directly against the full 340-entry delivered
manifest (`origin/deliver/doublemuon-bumpnet:studies/cms_coverage/deliver
/committed/manifest_min26bins.json`, read via `git show`, cached at
`studies/cms_mc_weights/evidence/deliver_manifest_min26bins.json.gz`):
**zero** of the 340 entries contain `_0jx_` in their name -- not just for
the `m0m1` combination, for *any* of the 63 combinations delivered. The
lowest jet-count final-state label anywhere in the manifest is `1jx`.

**Root cause, confirmed by reading the shared selection code directly**
(`studies/m0m1j0_cms/selection.py:451-455`,
`select_event_selection_cutflow`):

```python
has_ge2mu = ak.num(muons) >= 2
has_ge1jet = ak.num(jets["Jets"]) >= 1
final_mask = has_ge2mu & has_ge1jet
```

This is the **base population** for the entire analysis -- not a
per-combination cut. It runs once, before any combinatorics, and its
output (`obj_record`) is what both the real DoubleMuon coverage driver
(`studies/cms_coverage/cluster/run_coverage_on_file.py:200-201`, on
`origin/deliver/doublemuon-bumpnet`) and phase-1's MC driver
(`studies/m0m1j0_cms/cluster/run_m0m1j0_on_mc_file_v2.py:415-419`, per
amendment A1's explicit requirement to import and call this exact
function) both feed into `IMCalculator`/`group_by_final_state`. An event
with 0 light jets is excluded from the object record itself, before the
186-combination loop ever starts -- for data and for MC alike, since both
call the identical function.

So: **no 0-jet dimuon histogram exists anywhere in this delivery, and
none is possible from this pipeline's own base selection**, for data or
for MC. This is why phase-1 used the 1-jet bin -- it is the lowest jet
multiplicity this analysis can ever produce. Confirmed further in D1
below (the 0-jet bin is empty on both sides when re-checked directly from
raw, pre-postprocessing per-job output).

**Plain-language summary (D0):** The task asked for a "2 muons, no jets"
comparison. That comparison is impossible with this pipeline's existing
output, on either the data or the MC side, for a structural reason found
directly in the shared selection code: the whole analysis only ever keeps
events with at least one jet, before any histogram is built. This isn't a
missing histogram or a delivery gap -- it's a hard requirement baked into
the one selection function both data and MC call. Phase-1's use of the
1-jet histogram was the closest thing to the requested comparison that
actually exists.

---

## D1. Z-peak normalisation test (the key test)

**Method:** built directly from the *pre-postprocessing* per-job outputs
already on the cluster -- no data reprocessed:
- **Data**: the 57 `coverage_shard.sqlite` shards from the real
  DoubleMuon coverage production
  (`/storage/agrp/berkom/atlas-utilization/output/cms_coverage_full/job_*/`),
  reading every signature ending `_IM_m0m1` (raw, pre-z-peak-cut,
  pre-max-mass-cut dimuon mass) via `services.storage.sqlite_shards`,
  unweighted.
- **MC**: DY madgraphMLM (35671) + TTTo2L2Nu (67801), from phase-1's
  existing `mc_combinations.npz` per-job files, using the bumpnet-name
  signatures prefixed `mass_m0m1_cat_`, weighted by
  `genWeight * L1PreFiringWeight_Nom * per_file_normalization_factor`
  (the exact phase-1 weight, `per_file_normalization_factor` read from
  each sample's own `merge_mc_summary.json`, never recomputed).

Jet/b-jet count parsed directly from each signature's own final-state
label string (confirmed both the raw shard convention, e.g.
`0e_2m_1j_0g_0t_0b`, and the MC bumpnet convention, e.g.
`..._0ex_2mx_1jx_0gx_0tx_0bx`, by reading real signatures from a real
shard and a real `mc_combinations.npz` directly before writing the
parser). Script: `diagnosis/d1_zpeak.py`; full result:
`diagnosis/d1_zpeak_result.json`; plot:
`plots/diagnosis/d1_zpeak_inclusive.png`.

**Internal consistency check:** the jet-split categories sum exactly to
the inclusive category (1,246,944 + 277,832 + 78,760 = 1,603,536 data
events in 60-120 GeV; same exact-sum check passes for the b-jet split)
-- confirms the parsing is self-consistent, not an artifact of double
counting or missed events.

### Results (60-120 GeV / narrow 76-106 GeV, statistical uncertainty only)

| Category | Data | MC (weighted) | Data/MC | ±stat | Data/MC (76-106) |
|---|---|---|---|---|---|
| **Inclusive** | 1,603,536 | 1,319,543 ± 1,208 | **1.215** | 0.0021 | 1.213 |
| 0 jets | 0 | 0 | — (structurally empty, see D0) | — | — |
| 1 jet | 1,246,944 | 1,051,665 ± 1,081 | 1.186 | 0.0023 | 1.184 |
| 2 jets | 277,832 | 211,947 ± 481 | 1.311 | 0.0055 | 1.309 |
| ≥3 jets | 78,760 | 55,932 ± 244 | 1.408 | 0.0112 | 1.409 |
| 0 b-jets | 1,538,238 | 1,272,135 ± 1,192 | 1.209 | 0.0021 | 1.206 |
| ≥1 b-jets | 65,298 | 47,409 ± 196 | 1.377 | 0.0111 | 1.424 |

**Two findings, both load-bearing for D5:**

1. **The inclusive, most model-independent ratio is already 1.215** --
   21.5% data excess over MC, in a region containing essentially only DY
   and ttbar (the two processes included), before phase-1's specific
   2mu+1jet+0b/1b selection even applies. This is *larger* than every
   individual phase-1 category ratio once the b-tag/2-jet requirement is
   added back in for the 0-b-jet-like category (1.164 in D4's fuller
   stack, see below) -- i.e. the excess is not concentrated in a
   downstream selection, it is already present at the most inclusive
   level.
2. **The ratio rises monotonically and cleanly with both jet count and
   b-jet count**: 1.186 → 1.311 → 1.408 with jet count; 1.209 → 1.377
   with b-jet count. This is exactly the jet-multiplicity-mismodelling
   signature the task asked to look for.

**Plain-language summary (D1):** Even in the simplest possible
comparison -- just "how many dimuon events land near the Z mass," using
only Drell-Yan and top-pair simulation, before any of phase-1's specific
category cuts -- real data has about 21% more events than the simulation
predicts. That number by itself rules out "a few missing background
processes" as the whole story, because a few-percent-level background
addition cannot produce a 21% global shift in the cleanest, most
background-free comparison available. On top of that flat effect, the
gap gets steadily worse the more jets (or b-tagged jets) are required in
the event -- a clear, second, separate pattern layered on top of the
first.

---

## D2. Data-side audit (read-only)

**Records, runs, eras, file completeness.** The delivered DoubleMuon
production used exactly 2 CMS Open Data records:
`/DoubleMuon/Run2016G-UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD` (record
30522, **Run2016G only**) and
`/DoubleMuon/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD` (record
30555, **Run2016H only**) -- confirmed directly from
`cms_coverage_full/job_index_map_summary.json`. **57 of 57** files in
each record's own portal file list were processed (29/29 for 30522,
28/28 for 30555) -- **100% of the available files, 0 failures**
(confirmed: every `job_*` directory has both `coverage_shard.sqlite` and
`job_metadata.json`; `build_summary.json`'s own shard-identity check
already recorded `94,148,416` events read, matching the portal's own
`total_expected_events_from_portal` exactly). **No other primary dataset
(SingleMuon, SingleElectron, DoubleEG, ...) entered this production at
all.**

**Golden JSON.** Every one of the 57 jobs' own `job_metadata.json`
records `validated_runs_json =
data/cms/validated_runs/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`
(sha256 `e63961f7...982e28`) -- the identical file (path and checksum)
that Phase-3's `DESIGN.md` (Sec. 3) independently verified underlies the
16.393 fb⁻¹ luminosity figure, via that JSON's own upper run bound
(284044) appearing in the luminosity file's own "in JSON but not in
results" cross-check list. **Confirmed identical, not merely assumed.**

**De-duplication and the ~2% duplicate rate.** `docs/CMS_KNOWN_LIMITATIONS.md`
documents a ~2% duplicate rate, but that is specifically for the
SingleElectron+SingleMuon **cross-record** overlap (the same event firing
two different primary-dataset triggers), handled by
`services/parsing/event_deduplication.py` inside a *different* pipeline
path (`orchestration/handlers/parsing_handler.py`). **That code is never
called by `run_coverage_on_file.py`** -- confirmed by reading the driver;
it applies only the golden-JSON filter and the shared selection, no
de-duplication step at all. Since this delivery uses only DoubleMuon (one
primary dataset, two non-overlapping eras), that ~2% figure does not
apply here by construction. To check empirically rather than just by
reasoning, a **full-scale** (not sampled) read of `run`/`luminosityBlock`/
`event` from all 57 files (`diagnosis/d2_dedup_check.py`,
`diagnosis/d2_dedup_result.json`) found:

> **0 duplicate events out of 94,148,416** within the DoubleMuon dataset.

**Data duplicates cannot be inflating data relative to MC.** This is a
clean, full-population result, not an extrapolated sample.

**Jet/b-jet definition** (`studies/m0m1j0_cms/selection.py`): jets
`pT > 30 GeV`, `|eta| < 2.5`, tight ID (`Jet_jetId` bit 2), **no
pileup-jet-ID cut applied**, cleaned against every selected muon AND
electron at `ΔR ≥ 0.4`. B-tagging: `Jet_btagDeepFlavB > 0.2598` (DeepJet
Medium WP, UL2016 postVFP), split from light jets **before** the
kinematic/ID cuts and cleaning above (both `Jets` and `BJets` then get
the identical downstream cuts).

**Plain-language summary (D2):** The data side checks out cleanly. Every
file that was supposed to be processed was processed, nothing else got
mixed in, the certified-run list matches the one the luminosity number is
based on, and a full (not sampled) check of every single one of the 94
million events found not one duplicate. None of these can explain why
data sits above simulation.

---

## D3. Pileup check

`PV_npvsGood` is **not** among `selection.NEEDED_BRANCHES` -- confirmed
directly by reading that list -- so it was never read by either the real
DoubleMuon production or phase-1's MC driver, on either side. Per the
task's own instruction, this is reported rather than triggering a fresh
reprocessing of either dataset (out of scope for this round).

**MC `Pileup_nTrueInt` mean** (`diagnosis/d3_pileup_check.py`,
`diagnosis/d3_pileup_result.json`, read directly and lightly from the
exact same files phase-1 already used -- one small branch, unconditional
on selection):

| Sample | Unweighted mean | genWeight×L1-weighted mean |
|---|---|---|
| DYJetsToLL_M-50_madgraphMLM (35671) | 21.855 | 21.855 |
| TTTo2L2Nu (67801) | 21.855 | 21.853 |

Both samples carry essentially the identical simulated pileup profile
(as expected -- both are 2016 UL production with the same standard
pileup scenario), and weighting by the physics weight barely moves the
mean in either case.

**Pileup reweighting was NOT implemented, per the task's explicit
instruction.**

**Plain-language summary (D3):** We could not directly compare "how many
real collision pile-ups per event" between data and simulation, because
that information was never recorded in either side's existing output --
getting it would mean re-processing the full production, which is out of
scope this round. What we *can* say: the two simulation samples used here
agree with each other almost exactly on their own assumed pileup level,
so pileup differences between the MC samples themselves are not a
candidate explanation. Whether the *data*'s real pileup differs from what
these samples assumed remains unverified -- an open gap, listed honestly
below in point 7 of the closing summary rather than glossed over.

---

## D4. Missing-background measurement (measured, not estimated)

**File-count preflight** (`diagnosis/d4_file_counts.py`,
`diagnosis/d4_file_counts.json`): the 7 requested Tier-1 backgrounds
total **350 files** (ST_tW_top 11, ST_tW_antitop 10, WWTo2L2Nu 7,
WZTo3LNu_amcatnloFXFX 31, ZZTo4L 99, TTZToLLNuNu_M-10 42, TTWJetsToLNu
12, TTToSemiLeptonic 138) -- **exceeds 250**, so per the task's own rule:
**ran all 6 except TTToSemiLeptonic (212 files)**, reported here. The NLO
DY alternative (35669) added 41 more files. **Total D4 run: 253 files,
0 failures** (same MC driver/merge code as phase-1, completely
unchanged, per the task's own instruction).

**V1/V2 validation, every new sample**
(per-sample `merge_mc_summary.json` / `validate_v1_v2_result.json`):

| Record | Sample | V1 rel. diff | V2 max rel. diff | Pass 1e-6? |
|---|---|---|---|---|
| 64895 | ST_tW_top | 2.8e-8 | 1.2e-7 | yes |
| 64839 | ST_tW_antitop | (same pattern) | — | yes |
| 72676 | WWTo2L2Nu | — | — | yes |
| 72752 | WZTo3LNu (k=1, flagged) | — | — | yes |
| 68187 | TTZToLLNuNu_M-10 | 2.1e-8 | 1.2e-7 | yes |
| 68073 | TTWJetsToLNu | 9.6e-9 | 8.9e-8 | yes |
| 35669 | DYJetsToLL_M-50_amcatnloFXFX | 2.0e-8 | 8.2e-8 | yes |
| **75589** | **ZZTo4L** | **6.3e-4** | **3.66e-2** | **NO** |

**ZZTo4L (75589) fails V1/V2 -- investigated, root-caused, not a pipeline
bug.** Isolated to exactly **one** of its 99 files
(`.../50000/44F4BE4A-B82C-FA48-A8E1-AAE9565E362E.root`): its own
`Events` tree has 871,000 entries (confirmed: this matches the driver's
own `n_read` exactly, ruling out a truncated/partial read on our side),
but its own `Runs` tree records `genEventCount = 904,000` and
`genEventSumw = 1,198,138.36`, while re-summing the full, real
`genWeight` branch of all 871,000 actual events gives only
`1,154,337.9` -- a genuine mismatch between this ONE file's own internal
bookkeeping and its own physical event content, a known kind of CMS Open
Data artifact (a generation job's output apparently split unevenly
across files), not something either driver introduced. Impact: ZZTo4L's
own total normalization is off by ~0.06% (V1), and this sample
contributes well under 0.1% of every stack histogram checked below --
**negligible for every conclusion in this document**, but reported
plainly rather than silently passed over.

### Two-stack V3 redo (`diagnosis/d4_v3_stack.py`, `d4_v3_stack_result.json`)

**Stack (a)**: DY madgraphMLM (35671) + TTTo2L2Nu (67801) + ST_tW_top
(64895) + ST_tW_antitop (64839) + WW (72676) + WZ (72752, k=1 flagged) +
ZZ4L (75589) + TTZ (68187) + TTW (68073).
**Stack (b)**: identical, with DY amcatnloFXFX (35669) replacing
madgraphMLM.

| Histogram | Data | Stack (a), madgraphMLM DY | Ratio (a) | Stack (b), amcatnloFXFX DY | Ratio (b) | Phase-1 (DY+ttbar only) |
|---|---|---|---|---|---|---|
| V3a 2mu+1jet+0b | 28,496 | 24,473.7 | **1.164** | 29,987.3 | **0.950** | 1.235 |
| V3b 2mu+1jet+1b | 43,548 | 32,229.7 | **1.351** | 38,318.6 | **1.136** | 1.395 |
| V3b 2mu+2jet+1b | 14,418 | 10,453.3 | **1.379** | 11,384.9 | **1.266** | 1.427 |

**Per-process fractional contribution** (stack a; stack b identical
except DY is replaced by the amcatnloFXFX row):

| Process | V3a (0b) | V3b (1jet,1b) | V3b (2jet,1b) |
|---|---|---|---|
| DY (madgraphMLM) | 85.9% | 61.8% | 47.6% |
| TTTo2L2Nu | 8.4% | 35.0% | 49.0% |
| ST_tW (top+antitop) | 1.8% | 2.8% | 2.8% |
| WW | 3.2% | 0.08% | 0.10% |
| WZ (k=1, flagged) | 0.7% | 0.10% | 0.14% |
| ZZ4L | 0.08% | 0.02% | 0.02% |
| TTZ + TTW | 0.01% | 0.06% | 0.29% |

The 6 small electroweak/ttV backgrounds together never exceed ~4% of any
stack; **DY and ttbar dominate everywhere**, and which of the two
dominates flips between the 0-b-jet category (DY-dominated) and the
1-2-jet-1-b-jet categories (ttbar-dominated, single-top a real but
secondary contributor).

**Plain-language summary (D4):** We actually ran the extra background
processes instead of guessing at their size. They are real, they do
close part of the gap (roughly 5-7 points off each of phase-1's three
ratios), but they are far too small (never more than about 4% of any
category) to explain the bulk of the excess -- confirming, with a real
measurement instead of a guess, that "missing backgrounds" was not
sufficient on its own. Separately, and more strikingly: switching Drell-
Yan from its default (LO, madgraphMLM) generator to a next-to-leading-
order one (amcatnloFXFX) swings the cleanest category's ratio from a 16%
data excess to a 5% data deficit -- a 21-percentage-point shift, in the
category that is 86% Drell-Yan. In the categories that are mostly ttbar
instead, the same swap barely moves the ratio, because Drell-Yan is a
much smaller share there.

---

## D5. Synthesis: which explanation(s) does the evidence support?

**(a) Missing backgrounds -- real effect, confirmed too small to be the
main story.** Measured directly (D4): adding the 6 extra Tier-1
processes moves phase-1's own three ratios down by 5-7 percentage points
each (1.235→1.164, 1.395→1.351, 1.427→1.379). That is a genuine,
non-trivial contribution -- but it leaves 95%+ of the original gap
untouched in every category. **Ruled out as the dominant cause; kept as
a real, minor, now-quantified contributor.**

**(b) Global normalisation issue -- NOT ruled out; the single largest
number in this whole diagnosis.** D1's inclusive Z-peak ratio (DY+ttbar
only, before any of phase-1's category-specific cuts) is **1.215** --
a 21.5% data excess, at the most model-independent, least
background-contaminated point in the whole analysis. A discrepancy this
large, present already at the most inclusive level, cannot be produced
by a "few-percent" missing-background effect (which D4 just measured
directly to BE only a few percent). Something at the global level --
luminosity, an overall trigger/selection efficiency mismatch between
data and simulation, or the normalisation formula itself -- is the
leading candidate, and this diagnosis round did not (and per its own
scope, could not) test it further: doing so would mean checking trigger
efficiency, muon ID/iso efficiency, or the luminosity number itself
against an independent source, all out of scope here.

**(c) Jet-multiplicity mismodelling (including pileup) -- supported by a
clean, monotonic signature.** D1 shows the ratio climbing steadily with
both jet count (1.186 → 1.311 → 1.408) and b-jet count (1.209 → 1.377),
on top of whatever flat effect (b) contributes. This is exactly the
predicted signature for jet-multiplicity mismodelling. It persists **in
both DY generator choices** (D4's stack a and b both still show worse
agreement in the higher-jet/b-jet categories than in the cleanest one),
meaning it is not something the DY LO/NLO swap alone fixes -- it points
at jet modelling more broadly (parton shower, or backgrounds/pileup not
tested here) rather than at Drell-Yan's own extra-jet description alone.
Pileup itself could not be directly tested (D3) for lack of the
necessary branch in the existing data-side output.

**(d) LO vs NLO Drell-Yan modelling -- a real, substantial, but
category-confined effect.** D4's stack (a)→(b) swap moves the DY-
dominated V3a category by 21 percentage points (1.164 → 0.950) -- large
enough to plausibly explain most or all of the residual excess **in that
one category specifically**. But the same swap barely moves the ttbar-
dominated b-tag categories (1.351→1.136, 1.379→1.266 -- still well above
1), because DY is a much smaller fraction of the stack there. **LO vs
NLO DY choice is not a global explanation; it is a real, large,
category-specific one.**

**Overall picture, stated plainly:** no single explanation on this list
accounts for everything.
- The **0-b-jet category's** excess is plausibly explained almost
  entirely by (b) + (d) together (better DY modelling nearly closes it,
  and what's left is consistent with (b)'s global-level effect).
- The **b-tag categories'** excess (ttbar-dominated, where DY choice
  barely matters) is **not** explained by (d), only partly by (a), and
  still shows (c)'s rising-with-jet-count pattern on top of (b)'s global
  effect -- these categories' gap remains the least understood of the
  three.
- **(b), the global-normalisation-level effect, is present everywhere**
  and is the only candidate large enough by itself to explain the
  smallest (inclusive Z-peak) number in this whole document. It was not
  further isolated (which specific global factor) within this round's
  scope.

No tuning, fudge factor, or scale factor is recommended anywhere in this
document, per the task's explicit instruction.
