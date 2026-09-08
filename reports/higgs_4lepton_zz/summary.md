# H -> ZZ -> 4 leptons rediscovery exercise: full-scale results

Branch: `analysis/higgs-4lepton-zz`, off `analysis/higgs-diphoton-stage2-fullscale`
(inherits the `ThreadedFileProcessor` memory-leak fix, `7f91a1b`). Not merged
into master; no Stage 0/1/2/3 branch touched; Stage 2's parsed diphoton
output (`output/cms_higgs_diphoton_stage2_20260907_201708`) was never
touched by this work.

**Why 4-lepton instead of diphoton**: per the supervisor's stated goal, this
channel lets the Higgs bump be visible in the raw invariant-mass
distribution itself, without background subtraction — unlike diphoton,
where the bump only appears after a background fit.

## Step 1: the six records, verified individually against opendata.cern.ch

None assumed — every ID looked up directly, including the one given as
"believed" (DoubleMuon Run2016H):

| Record | Dataset | Files | Events | Size |
|---|---|---:|---:|---:|
| 30521 | /DoubleEG/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD | 47 | 78,797,031 | 70.5 GiB |
| 30554 | /DoubleEG/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD | 86 | 85,388,673 | 78.1 GiB |
| 30522 | /DoubleMuon/Run2016G-UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD | 29 | 45,235,604 | 39.3 GiB |
| **30555** | /DoubleMuon/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD | 28 | 48,912,812 | 42.9 GiB |
| 30528 | /MuonEG/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD | 29 | 33,854,612 | 33.2 GiB |
| 30561 | /MuonEG/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD | 19 | 29,236,516 | 29.9 GiB |
| **Total** | | **238** | **321,425,248** | **293.9 GiB (~316 GB)** |

30555 (the "believed" ID) checked out exactly as given. The full-run parsing
log's own totals — **238/238 files, 321,425,248 events** — match this table
exactly, an end-to-end cross-check that nothing was mis-scoped.

## Step 2: schema additions, and the electron cutBased scheme confirmed on real data

Added to `services/parsing/schemas.py`'s `cms-nanoaod` schema: Muons gained
`charge`, `pfRelIso04_all`, `looseId`; Electrons gained `charge`,
`pfRelIso03_all`, `cutBased`.

**Before hardcoding any threshold**, `Electron_cutBased`'s meaning was
checked directly on a real file (record 30521) via its own ROOT branch
title:

> `"cut-based ID Fall17 V2 (0:fail, 1:veto, 2:loose, 3:medium, 4:tight)"`

This is a **5-tier** scheme with a veto tier — confirmed different from the
photon `cutBased` scheme already used elsewhere in this project (Fall17V2,
**4-tier**, 0:fail/1:loose/2:medium/3:tight, no veto tier). **"cutBased >=
loose" for electrons therefore means `>= 2`, not `>= 1`** — using the photon
convention here would have silently included the weaker "veto" tier as if
it were "loose". Observed value counts on a real sample: fail 180,217,
veto 15,072, loose 10,072, medium 6,980, tight 25,631 (200k-event sample).

## Step 3: parse-time selection, and a real bug the validation pass caught

**Parse-time cuts** (loose only): muon pT>5 GeV/|eta|<2.4, electron pT>7
GeV/|eta|<2.5 — no isolation, no ID, no charge requirement yet. A new,
additive function, `physics_calcs.filter_events_by_combined_particle_count`
(wired through `event_selection.apply_parsing_event_selection`'s new
`combined_particle_counts` parameter and the parsing handler's
`record_combined_counts`), then requires the **combined** Electrons+Muons
count (after those cuts) to be **>= 4** — inclusive, not "exactly 4", so
5+-loose-lepton events aren't lost before the real quality cuts run. The
existing `particle_counts` mechanism could not express this: it only checks
each collection's count independently (AND semantics), never a
cross-collection sum, and a real 4l event can be 4e, 4mu, or 2e2mu.

**`selection_by_record`** was populated identically for all six records —
not because their selection differs, but because de-duplication only
switches on when it's non-empty, and de-dup is essential this time (see
Step 6).

**A real bug, caught exactly as intended**: the first validation attempt
found 4 of 6 records (everything except the two already-known DoubleEG
records) producing **zero events**, silently, with no exception —
`RECORD_ID_TO_SCHEMA` was simply never updated with the 4 new IDs, so
parsing fell back to auto-detection, which fails for NanoAOD's flat
branch naming. Fixed (all 6 IDs registered); the broken run's output was
deleted; the validation pass was re-run clean. Full detail:
`reports/higgs_4lepton_zz/validation_pass.md`.

## Step 4: validation pass (2 files/record, 12 total) — result: PASS

12/12 files, 100% success, 0 errors. **224 real candidates** from this 5%
subsample (119 4mu, 3 4e, 102 2e2mu). De-duplication: 9,963 duplicates
removed of 1,311,332 seen (0.76%). **Z1/Z2 pairing sanity check: a sharp,
correct peak at the Z mass** — 121/224 candidates (54%) had m_Z1 in
85-95 GeV. Full detail and reasoning in `validation_pass.md`. This cleared
all 5 pre-registered overnight-authorization gates (XRootD confirmed
working, all 6 IDs verified, total volume 293.9 GiB < 800 GB, validation
clean with sane non-zero candidates, 130 GB free vs. ~5 GB projected
output), so the full run proceeded without further sign-off, per the
standing authorization.

## Step 5: the 4-lepton selection and Z1/Z2 pairing logic

Implemented in `scripts/higgs_4lepton_zz_report.py`. Per-lepton "selected"
requirements (pT/eta already enforced at parse time; only ID/isolation
applied here): muons need `looseId` and `pfRelIso04_all < 0.35`; electrons
need `cutBased >= 2` (loose, per the confirmed scheme above) and
`pfRelIso03_all < 0.35`. Event-level: exactly 4 selected leptons (any
flavor mix), total charge 0, leading pT>20 GeV, subleading pT>10 GeV.

**Z1/Z2 pairing** (`find_z1_z2()`): every way to split the 4 leptons into
two opposite-sign-same-flavor (OSSF) pairs is considered; Z1 is whichever
valid OSSF pair's mass is closest to 91.1876 GeV (window 40-120 GeV), Z2 is
the remaining pair, which must **also** be OSSF (window 12-120 GeV); no
valid split rejects the event. Implemented as a plain per-event Python
function (at most 3 partitions x 2 orderings per event), deliberately not
vectorized, since it only ever runs on the small already-filtered survivor
set — chosen for clarity and easy review over cleverness. Verified against
hand-computed, known-mass synthetic constructions
(`scripts/test_higgs_4lepton_synthetic.py`) before ever touching real data:
a clean 2e2mu case, a clean 4mu case, an all-same-charge reject, a
Z2-mass-out-of-window reject, and a structurally-impossible 3e1mu reject —
all pass. Channels are classified as 4mu/4e/2e2mu from the surviving
leptons' flavor composition.

## Step 6: the full run

**Actual vs. estimated runtime**: original estimate before starting was
**~4-4.5 hours** (scaled from the validation pass's throughput). Actual:
**~3 hours 24 minutes** (true host launch ≈18:01, completion ≈21:25 —
reconstructed from a confirmed, stable ~3h00m clock skew between the
Docker container's internal clock and the host, discovered mid-run when a
chunk's log timestamp and its file's actual host mtime disagreed by exactly
that much; all elapsed-time figures here use host-clock-anchored values,
not the container's own log timestamps).

**Result: 238/238 files, 100% success rate, 0 errors, 321,425,248 raw
events read** — exactly matching the independently-verified Step 1 total.

**Peak memory observed: ~4.14 GiB (55.9%) of the 7.416 GiB container
limit**, from periodic sampling (not continuous instrumentation, so the
true peak could be marginally higher between samples, but every sample
across the whole run stayed under 56%, comfortably below any OOM risk). The
chunk-accumulation mechanism worked exactly as designed: retained events
built up in memory only until crossing the 512 MB chunk threshold, then
flushed to disk and reset — confirmed directly by watching memory dip after
each of the 9 chunk-flush events, never accumulating without bound across
records as initially (and incorrectly) suspected mid-run. No OOM risk
materialized; nothing was stopped.

**De-duplication: 1,138,023 duplicate events removed of 14,717,075 seen
(7.7%)** — non-zero and substantially higher than the validation
subsample's 0.76%, which makes sense: the 2-file validation subsample only
sparsely sampled the full lumi-range, while the full run sees complete
run-range overlap between all three trigger streams. The duplicate count
is spread across ~190 distinct run numbers with counts from single digits
up to ~45,000 in the heaviest-overlapping files (mostly MuonEG-vs-DoubleMuon
overlap, as expected — an event with 2 muons + 1 electron that fires both
triggers is a duplicate almost by construction) — a real, physically
distributed pattern, not a single anomalous run driving the count.

### Full cut-flow (real numbers)

| Stage | 30521 | 30554 | 30522 | 30555 | 30528 | 30561 | **Combined** |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw events (verified, Step 1) | 78,797,031 | 85,388,673 | 45,235,604 | 48,912,812 | 33,854,612 | 29,236,516 | 321,425,248 |
| after parse-time selection (post dedup) | 1,445,300 | 1,665,156 | 3,148,902 | 3,728,038 | 1,711,434 | 1,880,222 | 13,579,052 |
| >=4 quality leptons | 1,328 | 1,552 | 7,546 | 11,503 | 1,150 | 1,174 | 24,253 |
| exactly 4, charge 0 | 809 | 971 | 4,120 | 6,193 | 606 | 566 | 13,265 |
| leading pT>20, sublead pT>10 | 791 | 953 | 2,535 | 3,338 | 333 | 304 | 8,254 |
| **valid Z1/Z2, final candidates** | **286** | **341** | **630** | **890** | **35** | **34** | **2,216** |

Plot: `plots/fullscale_cutflow.png`.

### Final candidates by channel

| Channel | Candidates |
|---|---:|
| 4mu | 1,364 |
| 2e2mu | 694 |
| 4e | 158 |
| **Total** | **2,216** |

Plot: `plots/fullscale_channel_breakdown.png`. Muon-dominated, as expected
given generally higher muon reconstruction/ID efficiency at these loose
working points than electrons; 4e is smallest for the same reason
(requires 4 independently-efficient electron identifications).

### The 91 GeV validation peak: YES, it appears, clearly

**1,255 of 2,216 candidates (56.6%) have m_Z1 in the 85-97 GeV window**,
with a sharp single-bin spike right at the Z pole (the 90-95 GeV bin alone
holds 777 of them). Plot: `plots/fullscale_z1_validation.png`. This is
exactly the intended validation signature — since Z1 is defined as whichever
OSSF pair is closest to 91.1876 GeV, a broken pairing, a charge-reading
bug, or an incorrect mass calculation would not produce a clean physical
peak here; a flat or scattered m_Z1 distribution would instead. Seeing it
land sharply at the real Z mass confirms lepton identification, charge
handling, and the invariant-mass computation are all working correctly.
The overall 4-lepton mass (m4l) spectrum is broader, not sharply peaked at
91 GeV, which is separately expected: m4l also carries Z2's own broad,
mostly-off-shell mass, smearing the total well above 91 GeV even when Z1
alone is genuinely on-shell.

### Mass histograms (70-180 GeV, 3 GeV bins)

37 bins (`(180-70)/37 = 2.973 GeV`, kept fractionally under 3 GeV so the
exact requested 70-180 range stays intact rather than rounding to a
slightly different range).

| Histogram | Entries in [70,180] | Bins | Meets >30 bins? | Meets >=100 entries? |
|---|---:|---:|---|---|
| **Combined** | 1,509 | 37 | **PASS** | **PASS** |
| 4mu | 1,038 | 37 | PASS | PASS |
| 2e2mu | 396 | 37 | PASS | PASS |
| 4e | 75 | 37 | PASS | **FAIL** (< 100) |

Plots: `plots/fullscale_mass_combined.png` (combined),
`plots/fullscale_mass_stacked_by_channel.png` (stacked by channel).
BumpNet-format ROOT files (all four histograms, `mass_l0l1l2l3_cat_..._width_3.0`
naming — the combined file necessarily uses a generic "4l" composition
label since it mixes 4e/2e2mu/4mu events, documented as a deliberate
adaptation of the naming convention rather than a literal per-object-count
application, which has no slot for "mixed flavor composition"):
`histograms/fullscale_4l_combined_bumpnet.root`,
`histograms/fullscale_4l_4mu_bumpnet.root`,
`histograms/fullscale_4l_2e2mu_bumpnet.root`,
`histograms/fullscale_4l_4e_bumpnet.root`.

**The combined histogram DOES meet BumpNet's usability bar** — both the
>30-bin and >=100-entry thresholds. This is the opposite of what Step 8's
framing anticipated ("will very likely NOT meet BumpNet's usability bar"),
and the honest reason is explained below, not glossed over.

### The 115-135 GeV window: 392 candidates — far more than "a few tens"

The full, unabridged list of all 392 candidates in this window (mass,
channel, m_Z1, m_Z2, record, run, luminosity block, event number) is
written to `fullscale_115_135_candidates.csv`. Summary:

- **392 total**: 269 4mu, 106 2e2mu, 17 4e.
- m4l in this window: min 115.03, max 134.99, mean 124.71, median 124.85 GeV.
- Per-1-GeV-bin counts range from 12 to 32, with the single largest 1 GeV
  bin at 125-126 GeV (32 candidates) — stated as a plain count, not as
  evidence of anything.
- In the primary 3 GeV binning, the 123.5-126.5 GeV bin holds 82
  candidates, the single tallest bin in the entire 70-180 GeV combined
  spectrum (visible in `plots/fullscale_mass_combined.png`).

**Why 392, not "a few tens": this selection is much looser than a real
CMS-grade H->ZZ->4l analysis, and admits substantial non-resonant
background.** Real analyses additionally use full lepton-isolation working
points tuned per kinematic bin, FSR photon recovery, lepton-pair deltaR
("ghost removal") cuts, and often multivariate kinematic discriminants —
all explicitly out of scope for this exercise (deferred, per instructions).
Without them, this selection keeps a large population of non-resonant
ZZ*/Z+X continuum and Z-plus-extra-lepton background throughout the whole
70-180 GeV range, not a population dominated by genuine Higgs decays.
**No significance, p-value, or sigma is computed anywhere in this script or
report, and the count above, or the single tallest bin, must not be read
as evidence of a signal** — that determination needs the tighter,
analysis-grade selection this exercise deliberately did not implement, and
even then is not a call this script or visual inspection is positioned to
make. This is a plain count of how many events land where, nothing more.

## Bottom line

The exercise worked exactly as a rediscovery pipeline should at this
scale: a real physical validation signal (the Z1 mass peak) appears
unambiguously in the data, confirming every stage of the new lepton
selection and pairing logic is correct; the parse-time infrastructure
(schema additions, the new combined-lepton-count filter, cross-record
de-duplication) all performed as designed on a real 321-million-event,
294-GiB dataset with no crashes, no OOM, and 100% file success; and the
resulting mass histogram — contrary to the initial expectation — actually
clears BumpNet's usability bar, though for the honest reason that this
loose selection admits a sizeable non-resonant background across the whole
window rather than isolating a small, clean Higgs-only sample. The
392-candidate population near 125 GeV is reported as a plain count, with no
significance claim of any kind; that determination belongs to BumpNet (not
present on this machine, not re-checked here per instruction) or to a
tighter, analysis-grade selection this exercise deliberately deferred.

**Honest next step**: run the combined histogram through BumpNet once
available, and/or tighten the selection (isolation working points, FSR
recovery, ghost removal) to see whether the background-dominated 115-135 GeV
population thins out relative to any residual near-125-GeV structure — both
explicitly out of scope for this exercise and left for a follow-up task.
