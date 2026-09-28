# The ceiling: how many BumpNet-ready histograms can CMS Open Data give?

**This is a menu, not a delivery.** Nothing here is a finished BumpNet
dataset — every number below comes from ONE file per dataset (same files,
same triggers, same electron/muon/jet/b-jet definitions as the committed
`studies/cms_coverage/per_dataset/triggered/TRIGGERED_YIELD.md` run), and
exists to show how the distinct-histogram count grows as the restrictions
inherited from ATLAS's `config.yaml` (4 object types, max 4 objects per
combination, no MET) are lifted, and what each step costs.

## Headline table

| Config | Object types | Max objects/combo | Combination patterns | Distinct **data** | Distinct **MC** | **Combined** | Worst-case cost per file (wall time / peak RSS) | Est. full-run CPU-time* |
|---|---|---|---:|---:|---:|---:|---|---|
| **C1** | Electrons, Muons, Jets, BJets | 4 | 186 | 339 | 682 | **709** | 12.3 min / not captured† (SingleMuon) | ~59 CPU-hr (13 datasets) |
| **C2** | + Photons, Taus | 4 | 853 | 373 | 803 | **829** | 35.1 min / 3.21 GB (Tau) | ~136 CPU-hr (15 datasets) |
| **C3** | + Photons, Taus | 5 | 1,975 | 401 | 865 | **898** | 36.5 min / 3.17 GB (Tau) | ~155 CPU-hr |
| **C4** | + Photons, Taus | 6 | 3,904 | 408 | 881 | **916** | 35.7 min / 3.21 GB (Tau) | ~162 CPU-hr |
| **C5** | C4 + MET variants | 6 (+MET) | 7,808 | 865 | 1,779 | **1,856** | 42.1 min / 3.26 GB (Tau) | ~215 CPU-hr |

\* Sum over every file of the Run2016G record used for each dataset
(`studies/cms_coverage/ceiling/cluster/datasets.tsv`), i.e. "if you ran
every file of these 13/15 datasets once through this exact pipeline,
serially, on one CPU." Trivially parallelizable (one job per file, exactly
how this task's own PBS array ran); wall-clock with enough parallel slots
is close to the single-largest-file time in the row above.  **Does not**
include the Run2016H record that exists for the 6 original data datasets
(the triggered run used G+H; this ceiling grid, per its own file-count
budget, used G only) — a full delivery would need to add that, roughly
doubling the data-side file count and cost. † C1 predates the
`/usr/bin/time` cost-capture fix added to `pbs_ceiling.sh` after the C1
submission (see that file's own comment on why); C1's memory is not
separately captured but C1 is a strict subset of C2's object handling and
C2's peak RSS (3.21 GB) is well under the 12 GB cap, so C1's is expected to
be lower still.

**C1 self-check: PASSED.** Every per-dataset stage-d count and the union
(339 / 682 / 709) reproduce the committed triggered-run numbers exactly —
see `assets_raw/C1/union_C1.json` and the commit message on this branch.
No file needed cost-capping; nothing was stopped early.

## Where does 3,000 fall?

**It doesn't — not anywhere in this grid.** The largest configuration
tested, C5, reaches **1,856** BumpNet-ready distinct histograms combined —
62% of the way to 3,000, at a cost of ~215 CPU-hours for one full pass over
these 15 datasets' G-record files. Going from C1 to C5 (4→6 object types,
max 4→6 objects/combo, plus MET) multiplies the combination-pattern count
by 42× (186→7,808) but the **distinct BumpNet-ready histogram count** only
2.6× (709→1,856) — the >=100-events/>30-bins gate absorbs almost all of
that combinatorial growth. At the pre-final-cut stage (b, before the
Z-peak/max-mass/bin-count pruning — not "BumpNet-ready" by this task's own
definition), C5 reaches 3,450 combined names, which is over 3,000, but that
number is not comparable to 339/682/709/etc. and is not the criterion this
whole survey has used throughout; it is reported here only to show where
the raw pre-cut menu already exceeds 3,000 while the BumpNet-ready count
does not.

**The single biggest lever, by far, is MET.** C1→C4 (adding photons, taus,
and raising the per-combination cap to 6) adds 207 combined histograms
over 3 steps. C4→C5 (adding MET variants alone, one more step) adds 940 —
more than doubling C4's own count, for a combinatorial-pattern doubling
(3,904→7,808) that cost only 6% more wall time on the worst-case dataset.
This is because MET is present in essentially 100% of events (unlike
photons/taus, which pass selection in a small minority), so a "+MET"
variant of a combination that already survives the BumpNet thresholds
survives at nearly the same rate. `met_variant` is 940 of C5's 1,856
combined names (50.6%) — see `assets_raw/C5/union_C5.json`'s
`combined_union_by_content`.

**To get further toward 3,000** would need either (a) a materially larger
combinatorial menu than tested here (more object types, or MET combined
with photons/taus in the same combination rather than only as an additive
+MET augmentation of the existing menu, or a smaller minimum-bin-width so
more mass ranges clear >30 bins), or (b) accepting that BumpNet's own
acceptance thresholds are the actual ceiling, not the object menu — this
survey's earlier finding that the count **saturates with statistics**
(TRIGGERED_YIELD.md; 1,000× more data adds only a handful of names) means
running more files of the same datasets is unlikely to close much of the
remaining gap either. Neither of those is in this task's scope to explore
further; both are flagged as the logical next question.

## Photon and tau definitions used (full detail: `DEFINITIONS.md`)

**Photons** — reused **verbatim** from this codebase's own already-verified
H→γγ production recipe (`config.cms_hgg_data.yaml:279-284`), not invented
for this task: pT > 20 GeV, `bool_require: [electronVeto, mvaID_WP90]`,
`bool_any_of: [isScEtaEB, isScEtaEE]` (the real, CMS-standard
supercluster-eta barrel/endcap acceptance gap, already measured on real
files in `docs/CMS_KNOWN_LIMITATIONS.md`). Real branch titles quoted:
`Photon_mvaID_WP90` = *"MVA ID WP90, Fall17V2"*, `Photon_electronVeto` =
*"pass electron veto"*.

**Taus** — proposed fresh for this task (no existing CMS tau recipe
anywhere in this codebase to defer to) and **explicitly flagged as needing
supervisor confirmation**: pT > 20 GeV, |eta| < 2.3,
`Tau_idDeepTau2017v2p1VSjet` Medium WP (bit 16 of *"byDeepTau2017v2p1VSjet
ID working points (deepTau2017v2p1): bitmask 1 = VVVLoose, ... 16 =
Medium, ..."*), VSe VVLoose (bit 2), VSmu Tight (bit 8),
`Tau_idDecayModeOldDMs` required True.

Both use ΔR<0.4 overlap removal against selected leptons AND jets — new
code (`objects.py`'s `overlap_removal`), since no shared delta-R-cleaning
helper exists anywhere under `services/`. This directly answers the
"future decision" `docs/CMS_KNOWN_LIMITATIONS.md` flagged on 2026-09-03
("Object overlap" / the Maryna discussion): that overlap removal was never
added, and this task adds it and measures its size for the first time.

### Overlap measurement — pooled over the 8 real data datasets at C4 (real numbers, not MC)

| | Candidates | Overlaps a **lepton** | Overlaps a **jet** | Overlaps **either** |
|---|---:|---:|---:|---:|
| **Photons** | 116,206 | 32.5% | **49.6%** | **82.1%** |
| **Taus** | 132,831 | 3.2% | **89.7%** | **92.9%** |

**This is the single most likely artifact in the whole menu, exactly as
anticipated.** On real data, roughly 4 in 5 candidate photons and roughly
19 in 20 candidate taus are removed by this cleaning step — meaning any
photon- or tau-containing histogram delivered to BumpNet was built from a
small, overlap-cleaned minority of the raw candidates, and (per the
now-implemented cleaning) any photon/tau combination surviving to BumpNet
is NOT contaminated by a self-pairing jet/lepton — but the numbers above
show how large a population that cleaning step discards, and that
discarded population's own properties (was it real physics or
double-counted reconstruction, as already established for the
muon-jet case, DESIGN.md's ~92.66-92.68% figure) has **not** been
investigated here. Per-dataset overlap numbers (data ranges from JetHT's
28.8%/70.8% up to SingleElectron's 83.8%/92.7%) and every MC dataset's own
figures are in each config's `job_metadata/*/job_metadata.json`
(`overlap_diagnostics`).

**A second, non-obvious finding**: widening the object-type set doesn't
only ADD potential histograms — it can also **fragment** an existing
final-state population into finer buckets by photon/tau multiplicity (the
BumpNet name's own `_cat_..._Ngx_Ntx` suffix is more granular once g/t are
tracked), occasionally dropping a *pre-existing, photon/tau-free* histogram
below the >=100-event threshold even though photons/taus play no role in
that combination's own mass calculation. Confirmed directly: DoubleMuon's
traditional (non-photon/tau) histogram count fell from 176 (C1) to 172
(C2) — `b-jet-containing` 87→84, `jet-only` 36→35 — purely from this
fragmentation, not a bug (`assets_raw/{C1,C2}/funnel_DoubleMuon.json`).

## MET finding

**Supported, and measured (C5).** From the BumpNet paper (arXiv:2501.05603
§2.2.2, verbatim): the "MassMET" variant sets MET's four-momentum
longitudinal component and mass to zero. From the shared code: MET
represented as `{pt: MET_pt, eta: 0.0, phi: MET_phi, mass: 0.0}` needs
**zero changes** to `IMCalculator`/`concat_events` — `eta=0` forces `pz=0`
exactly under the same `vector.zip` convention already used for every
other object type. `get_all_combinations`'s global `min_count`/`max_count`
can't cap MET at exactly 1 while allowing others up to 4, so MET variants
are a **new, additive augmentation** (`objects.py`'s `add_met_variants`):
every C4 combination gets a second "+MET" copy, both kept. Result: C5
(C4+MET) = 865/1,779/1,856, roughly double C4 alone — see "Where does
3,000 fall?" above.

## Standing caveats (carried forward, not re-derived here)

- **Saturates with statistics** — 1,000× more data adds only a handful of
  histograms (TRIGGERED_YIELD.md), because ">30 filled bins" is met at
  modest statistics. This grid used one file per dataset throughout, same
  as the triggered run.
- **Triggers reduce counts** — applying each dataset's own trigger cut
  each dataset's histogram count by 24-64% in the triggered run; unchanged
  here (same triggers, same golden JSON for data).
- **Distinct ≠ independent** — many surviving histograms overlap in
  underlying events (shared jets/leptons across combinations); this survey
  counts distinct *names*, not statistically independent measurements.
- **Not the same thing as cross-dataset event de-duplication** — this
  report's "distinct union" is a NAME-level union across datasets' own
  separately-produced histograms; it says nothing about whether the same
  physical event appears in two primary datasets (e.g. DoubleMuon and
  MuonEG can both record one event) — that de-duplication is a different,
  out-of-scope question (`services/parsing/event_deduplication.py` exists
  for it but was not invoked by this task).
- **Prescales unknown for JetHT, MET, and now Tau, from NanoAOD** — none
  of the three trigger choices used here (JetHT's PFHT900/PFJet450, MET's
  PFMET170 pair, Tau's DoubleMediumIsoPFTau pair) can be confirmed
  unprescaled from the file itself; all are standard-convention choices,
  **UNVERIFIED**.
- **Two known DoubleMuon artifacts, not re-investigated**: the muon-jet
  overlap (~92.66-92.68%, DESIGN.md) and an unexplained sub-1 GeV dimuon
  population.

## Evidence map

- `DEFINITIONS.md` — full photon/tau/MET definitions, every branch title
  quoted verbatim, dataset record IDs and trigger choices with citations.
- `objects.py` — new selection/overlap/MET code (read-only imports of
  `studies.m0m1j0_cms.selection` and
  `services.calculations.physics_calcs.filter_events_by_kinematics` for
  everything that function already supported).
- `cluster/run_ceiling_on_file.py`, `cluster/measure_ceiling_funnel.py`,
  `compute_union.py`, `cluster/pbs_ceiling.sh`, `cluster/gen_mapping.py` —
  the generalized driver/funnel/union/submission scripts.
- `assets_raw/C1/` .. `assets_raw/C5/` — per-config: every dataset's full
  stage-b and stage-d BumpNet name lists (with event/bin counts), the
  funnel-stage counts, the union/overlap JSON, and every job's cost
  metadata (`job_metadata/*/job_metadata.json`, including
  `overlap_diagnostics` for C2-C5).
- `cluster/datasets.tsv` — the record-id/trigger choice for every dataset.
