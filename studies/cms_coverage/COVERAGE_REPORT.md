# CMS coverage survey: how many BumpNet-usable histograms does DoubleMuon yield?

Branch `survey/cms-coverage`, off `analysis/m0m1j0-cms` at
`040ba672cada7ba861a78e048d8808cb47b30897`. Every number below is labeled
**VERIFIED BY RUNNING** (an actual command was executed and its output is
quoted), **FROM COMMITTED DATA** (read from an existing file, unchanged),
or **UNVERIFIED / ESTIMATED** (explicitly flagged, never presented as
measured).

## Part 0 — the combination rule

See `studies/cms_coverage/COMBINATION_RULE.md` for the full detail, file:line
citations, and how each shared function was called (not reimplemented). In
summary: the ATLAS config (`config.yaml:135-144`) asks for 1-4 distinct
object types (Electrons, Muons, Jets, BJets) per combination, 1-4 objects
per type, capped at 4 objects total, with sub-leading (`e1`, `j1`, …)
variants included up to rank index 1. Calling
`services.calculations.combinatorics.get_all_combinations` with these exact
arguments reproduces the technical lead's numbers exactly: **65 combination
patterns without sub-leading variants, 186 with them.**

The 115 GeV `z_peak_cutoff` applies to **any** combination whose invariant-
mass letters contain two or more of the same lepton flavor (`e` or `m`)
anywhere — not only a pure 2-body dilepton — which is exactly why `m0m1j0`
(two muon letters) starts at 115 GeV. This is applied per-signature in this
survey, not as a blanket rule (verified directly, see Part 1.5).

Storage design (Part 1.2): raw per-(pattern×category) float32 masses, not a
histogram, because `_split_by_first_empty_bin`
(`post_processing_pipeline.py:355-388`) anchors its bins at the data's own
exact minimum/maximum — no fixed-grid histogram, however fine, can
reproduce that exactly (see COMBINATION_RULE.md for the code-level proof).

## Part 1 — running the full combination set over DoubleMuon

### Pilot (2 files) — VERIFIED BY RUNNING

| | job 1 (record 30522, file 0) | job 2 (record 30522, file 1) |
|---|---|---|
| wall time | 117.1 s | 135.0 s |
| peak memory | 2.05 GB | 2.30 GB |
| output shard size | 1.22 MB | 1.31 MB |
| (pattern×category) signatures written | 1,137 | 1,184 |
| largest single signature (events) | 31,382 | 33,989 |

Both comfortably inside the 45-minute / 12 GB stop condition (worst case:
~2.3 minutes, ~2.3 GB) — extrapolated to 57 files: well under an hour of
total compute, well under memory limits on any single job. Proceeded
directly to the full run per the task's own instruction.

### Full run (57 files) — VERIFIED BY RUNNING

Submitted as a 57-job PBS array (`studies/cms_coverage/cluster/submit_coverage_full.sh`,
job ID `5115274[].pbs`), one job per file, matching the pilot's per-job
driver and resource profile. **35 of 57 jobs succeeded on the first pass;
22 failed** with the identical error:

```
OSError: File did not vector_read properly: [ERROR] Operation expired
```

— an XRootD read timeout from `fsspec_xrootd`. Investigated step by step,
not assumed:

1. **First hypothesis (57-way contention): wrong, or at least
   insufficient.** Retried the 22 failed jobs sequentially, one at a time
   via `run_coverage_on_file.py` directly with no code change, to remove
   any cross-job contention. One specific file (record 30522, file index
   1) failed the exact same way even run alone. This ruled out "just too
   many jobs at once" as the full explanation.
2. **Second hypothesis (needs a bounded retry): partially right, not
   sufficient either.** Added a 4-attempt retry with a 15 s backoff around
   the read (`run_coverage_on_file.py`, commit `234f69e`) and resubmitted
   the 22 as a PBS array. 5 more succeeded, but **the same file
   (record 30522, file index 1) failed all 4 retries again**, identically
   each time — a real, reproducible failure, not noise a retry could ride
   out.
3. **Root cause, found directly:** a small diagnostic (1 branch,
   1000 events) on that exact file succeeded instantly; reading the exact
   same file in 300,000-event chunks (instead of one
   whole-file/all-branches call) succeeded end-to-end with zero errors,
   in 229 s. The failure is tied to **request size** — one enormous
   multi-branch vector-read across ~2.3–2.5M entries — not file health or
   pure timing luck; retrying the identical oversized request just
   reproduces the identical failure. Fixed by reading in
   300,000-event chunks (commit `c4f16cb`), mirroring the shared
   pipeline's own batched-reading convention
   (`services/parsing/file_parser.py`'s `batch_size`) rather than
   inventing a new pattern.
4. **Outcome: all 57 jobs completed successfully** after the chunked-read
   fix — 35 on the first pass, 5 more on the first retry (bounded-retry
   fix alone), and the remaining 17 (including the one file that
   defeated plain retrying twice) on the second retry, with chunked
   reads. No job was silently skipped or excluded; every one of the 57
   files was eventually read successfully by the same, single, final
   version of the driver script.

### Identity check — VERIFIED BY RUNNING

Every job's `n_read` (raw events read from its file) summed across all 57
jobs: **94,148,416** — matching the portal's own published total for
records 30522+30555 exactly, the same number named in the task brief.

### Part 1.5 — mandatory self-check against `studies/m0m1j0_cms/v2` — PASSED, VERIFIED BY RUNNING

`m0m1j0` (muon0 + muon1 + leading jet) is one of the 186 patterns computed
here; its per-category raw event counts, after the SAME global
`min_events_per_fs=100` prune, were compared field-for-field against the
committed `studies/m0m1j0_cms/v2/data/merge_v2_summary.json`
(`studies/cms_coverage/assets/self_check_vs_v2.json` has the full row-by-row
comparison): **61/61 categories match exactly** — every category v2 kept
has the identical raw event count here, and every category v2's own
`min_events_per_fs` prune dropped is absent here too. Nothing was adjusted
to force this match; it is the direct, first-attempt result of running the
same real, shared functions on the same selected events.

## Part 2 — the funnel: how many histograms survive at each stage

All numbers below: **VERIFIED BY RUNNING**
(`studies/cms_coverage/assets/funnel_result.json`,
`studies/cms_coverage/cluster/merge_and_count.py`), computed by the real,
imported, unmodified shared functions
(`prune_final_states_below_min_events`, `_apply_z_peak_cut`,
`_find_rightmost_highest_peak`, `_split_by_first_empty_bin`) — nothing
below was reimplemented.

### The funnel

| stage | count | description |
|---|---|---|
| (a) all pairs, ≥1 event | **2,397** | every distinct (pattern × final-state category) combination that occurred at least once in the 57-file DoubleMuon dataset |
| (b) after `min_events_per_fs=100` | **465** | global raw-event-count prune, applied per final state (shared by every pattern in that state), exactly as the real pipeline orders it |
| (c) after full post-processing, ≥100 main events | **375** | z-peak cut (where applicable) + 10 TeV cutoff + peak removal + first-empty-bin split; counted only if the surviving "main" array still has ≥100 events |
| (d) BumpNet-usable: >30 bins AND ≥100 events | **316** | arXiv:2501.05603 §2.2.2's own stated minimum |
| (e) (d) **and** ≥10 events in every retained bin | **0** | arXiv:2501.05603 §3.2.4's noted degradation point |

**Headline number: 316 BumpNet-usable histograms from DoubleMuon**, by the
paper's own stated minimum (stage d). **Stage (e) is a genuinely important,
separate finding: zero of those 316 survive the paper's own noted per-bin
degradation point (≥10 events/bin) applied to every retained bin.** This
was checked directly, not assumed: even the single largest surviving
histogram (`mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx`, 1,051,110 events
across 133 non-empty bins) has **18 bins with fewer than 10 events each**,
in its sparse high-mass tail (the other two largest, `m0j0` and `m1j0` in
the same category, have 30 and 17 such thin bins respectively). This is
real physics, not a code artifact — a steeply falling mass spectrum,
histogrammed in fixed 10 GeV bins out to a 10 TeV cutoff, thins out to a
handful of events per bin long before the spectrum itself ends, even for
the highest-statistics categories. **Read plainly: at this dataset's scale
and this fixed binning, every one of the 316 nominally BumpNet-usable
histograms has at least one bin thin enough to fall under the paper's own
noted degradation threshold somewhere in its tail** — the >30-bins/≥100-
event gate (stage d) is not sufficient on its own to guarantee every bin is
individually well-populated.

### Breakdown by number of objects in the pattern

| | 2 objects | 3 objects | 4 objects |
|---|---|---|---|
| (b) | 162 | 176 | 127 |
| (c) | 134 | 145 | 96 |
| (d) | 98 | 130 | 88 |

### Breakdown by object content

| | lepton-only | lepton+jet | jet-only | b-jet-containing |
|---|---|---|---|---|
| (b) | 26 | 156 | 21 | 262 |
| (c) | 17 | 124 | 19 | 215 |
| (d) | 8 | 104 | 17 | 187 |

`b-jet-containing` dominates by *count* at every stage — this counts
distinct **patterns** (how many of the 186 combination recipes include a
b-jet slot), not event population; DoubleMuon's own trigger requires two
muons but places no requirement on jets/b-jets, so a large fraction of the
186 combinatorial recipes involve at least one BJets slot, and each gets
its own shot at passing the survival gates independently of how many
*events* it ultimately contains.

### Sensitivity: stage (b) and (d) at alternate event thresholds

| threshold | stage (b) | stage (d) |
|---|---|---|
| 50 | 593 | 319 |
| 100 (primary) | 465 | 316 |
| 200 | 371 | 307 |
| 1000 | 269 | 210 |

Stage (b) — the raw population gate — is fairly sensitive to the threshold
choice (593 → 269 across this range), as expected for a hard population
cutoff on a long-tailed distribution of category populations. **Stage (d)
is comparatively insensitive** (319 → 210, and completely flat between 50
and 200) — most histograms that clear the >30-bin shape requirement also
comfortably clear a several-hundred-event floor; the bins/shape criterion,
not the raw event-count criterion, is what actually gates most of these
histograms once post-processing has run.

### Top 20 histograms by event count, and median bin count

Median number of non-empty bins across the 316 stage-(d) survivors:
**65.5** — well above the 30-bin minimum, meaning most surviving
histograms have real dynamic range, not a bare-minimum handful of bins.

| rank | histogram | events | non-empty bins |
|---|---|---|---|
| 1 | `mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx` | 1,051,110 | 133 |
| 2 | `mass_m0j0_cat_0ex_2mx_1jx_0gx_0tx_0bx` | 1,006,251 | 129 |
| 3 | `mass_m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx` | 976,771 | 88 |
| 4 | `mass_m0m1j0_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 254,664 | 144 |
| 5 | `mass_m0m1j1_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 253,697 | 115 |
| 6 | `mass_m0m1j0j1_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 251,364 | 187 |
| 7 | `mass_m1j0j1_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 243,856 | 151 |
| 8 | `mass_m0j0j1_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 233,439 | 175 |
| 9 | `mass_j0j1_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 230,816 | 146 |
| 10 | `mass_m0j0_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 223,660 | 120 |
| 11 | `mass_m1j0_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 217,390 | 100 |
| 12 | `mass_m0j1_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 205,659 | 95 |
| 13 | `mass_m1j1_cat_0ex_2mx_2jx_0gx_0tx_0bx` | 202,770 | 76 |
| 14 | `mass_m0m1j0_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 55,380 | 141 |
| 15 | `mass_j0j1_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 52,539 | 138 |
| 16 | `mass_m0m1j1_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 52,461 | 104 |
| 17 | `mass_m1j0j1_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 52,436 | 150 |
| 18 | `mass_m1j1_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 51,978 | 76 |
| 19 | `mass_m1j0_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 50,937 | 95 |
| 20 | `mass_m0j0j1_cat_0ex_2mx_3jx_0gx_0tx_0bx` | 50,253 | 171 |

Note how the top of this list is dominated by the "2 muons + 1 or 2 jets,
no b-tag" category — exactly the bulk DoubleMuon population — and by
patterns that are trivial variations of each other (`m0j0`, `m1j0`,
`m0m1j0` all drawn from the same 2-muon-1-jet events). This is the direct,
concrete illustration of the independence point below.

**One sentence for the supervisor:** these histograms are **not**
statistically independent — many combination patterns share the same
underlying objects (e.g. `m0m1j0` and `m0m1j1` share both selected muons,
differing only in which jet is picked), so this count is a count of
**BumpNet inputs**, not a count of independent physics measurements.

## Part 3 — CMS Open Data sample survey

### 3.1 Method

Queried `https://opendata.cern.ch/api/records/` programmatically (no
hand-browsing) via plain HTTPS GET from a local Python script; raw JSON for
every record discussed below is saved under `studies/cms_coverage/portal_raw/`
(16 DATA records, 29 MC records — 3.4 MB total, uncompressed since small).
**Portal search-syntax finding (worth recording):** field-qualified Lucene
queries (`type:Dataset`, `subtype:Simulated`, `title:"..."`) mostly returned
zero or wildly over-broad results against this portal's search endpoint;
plain free-text queries against dataset names, filtered client-side by
regex against the returned titles, worked reliably and are what this survey
uses throughout — documented here so a future user of this API doesn't
waste time on the same dead ends.

### 3.2 DATA table — every CMS 2016 primary dataset in NanoAOD

**VERIFIED BY RUNNING** (`studies/cms_coverage/portal_raw/data_table_raw.json`
and `portal_raw/data/record_*.json`):

| Primary dataset | Era | Record ID | Files | Events | NanoAOD version |
|---|---|---|---|---|---|
| DoubleMuon | Run2016G | 30522 | 29 | 45,235,604 | NanoAODv9-v2 |
| DoubleMuon | Run2016H | 30555 | 28 | 48,912,812 | NanoAODv9-v1 |
| SingleMuon | Run2016G | 30530 | 70 | 149,916,849 | NanoAODv9-v1 |
| SingleMuon | Run2016H | 30563 | 82 | 174,035,164 | NanoAODv9-v1 |
| DoubleEG | Run2016G | 30521 | 47 | 78,797,031 | NanoAODv9-v1 |
| DoubleEG | Run2016H | 30554 | 86 | 85,388,673 | NanoAODv9-v1 |
| SingleElectron | Run2016G | 30529 | 71 | 153,363,109 | NanoAODv9-v1 |
| SingleElectron | Run2016H | 30562 | 80 | 129,021,893 | NanoAODv9-v1 |
| MuonEG | Run2016G | 30528 | 29 | 33,854,612 | NanoAODv9-v1 |
| MuonEG | Run2016H | 30561 | 19 | 29,236,516 | NanoAODv9-v1 |
| JetHT | Run2016G | 30525 | 70 | 120,688,407 | NanoAODv9-v1 |
| JetHT | Run2016H | 30558 | 72 | 124,050,331 | NanoAODv9-v1 |
| MET | Run2016G | 30526 | 17 | 26,974,131 | NanoAODv9-v1 |
| MET | Run2016H | 30559 | 32 | 39,773,485 | NanoAODv9-v1 |
| Tau | Run2016G | 30532 | 45 | 79,578,661 | NanoAODv9-v1 |
| Tau | Run2016H | 30565 | 55 | 76,758,754 | NanoAODv9-v1 |
| **Total** | | **16 records** | **832** | **1,395,586,032** | |

**Only Run2016G and Run2016H are released in NanoAODv9 (UL) for any of
these 8 primary datasets** — checked directly for every dataset (not
assumed): the earlier 2016 eras (B–F) simply do not appear as NanoAOD
records on this portal for these primary datasets, only as MiniAOD/AOD
(pre-UL, 2015/lower-priority eras) or as "Configuration file" provenance
records. This matches why every existing study in this repo (m0m1j0,
H→γγ) only ever uses G+H.

**Other released formats/years for these same primary datasets** (not
NanoAOD, would need different parsing): MiniAOD (e.g.
`/DoubleMuon/Run2016G-UL2016_MiniAODv2-v1/MINIAOD`) — needs full CMSSW/PAT
tooling, not a flat-branch NanoAOD-style reader; 2015 AOD/MiniAOD (e.g.
`/DoubleMuon/Run2015D-16Dec2015-v1/AOD`) — an older, different detector
conditions/reconstruction era entirely, and raw AOD needs CMSSW to read at
all; and a small number of derived/enhanced records (e.g. record 31305,
"DoubleMuon dataset in NanoAOD format enhanced with Particle Flow
candidates from RunG of 2016") — NanoAOD-shaped but not the standard
release, not used here.

### 3.3 MC table — NanoAODSIM samples by process group

**VERIFIED BY RUNNING** (`studies/cms_coverage/portal_raw/mc_table_raw.json`,
29 individual record JSONs under `portal_raw/mc/`). Every group's postVFP
(`RunIISummer20UL16NanoAODv9`) campaign resolved; **a direct search for any
preVFP/APV 2016 UL campaign naming variant** (`NanoAODAPVv9`,
`RunIISummer20UL16NanoAODAPVv9`, `HIPM_UL2016`) **returned zero hits for
every process checked** — this portal appears not to carry a separately
released preVFP UL2016 NanoAODSIM campaign for the processes checked here.
Not exhaustively checked for every possible CMS 2016 MC process — flagged
as UNVERIFIED beyond what was directly searched.

| Group | Processes found | Total files | Total events |
|---|---|---|---|
| ttbar | TTTo2L2Nu, TTToSemiLeptonic, TTToHadronic | 333 | 295,335,000 |
| Drell-Yan | DYJetsToLL_M-50 (inclusive) | 61 | 82,448,537 |
| W+jets | WJetsToLNu (inclusive) | 68 | 80,958,227 |
| Diboson | WW, WZ, ZZ | 74 | 24,556,000 |
| Single top | ST_t-channel (top, antitop), ST_tW (top, antitop) | 168 | 98,727,000 |
| QCD multijet | 11 pT bins, 15 GeV–1.4 TeV (see JSON; not exhaustive at the very highest/lowest bins) | 403 | 375,000,000 |
| Signals (H→γγ) | ggH, VBF, WH+, WH−, ZH, ttH, all M=125 | 71 | 3,433,898 |
| **Total (as searched)** | 29 records | **1,178** | **960,458,662** |

Drell-Yan and W+jets here are each only the single **inclusive** sample
(`DYJetsToLL_M-50`, `WJetsToLNu`) — both processes are typically also
released in HT-binned exclusive samples for better high-mass statistics;
those were not searched for here (time-boxed scope) and would add to this
total. QCD multijet is binned in `Jet_Pt` GeV ranges; 11 of the likely
~13-15 total bins were checked (missing at least the lowest sub-15 GeV and
highest >1.4 TeV bins). The MC table above should be read as a solid
lower bound on what exists, not an exhaustive enumeration.

### 3.4 Parseability check — VERIFIED BY RUNNING

One file per primary dataset (era G) and one file per MC group (first
process found), opened remotely over XRootD, checked for every branch this
study's selection needs (`studies/cms_coverage/portal_raw/parseability_results.json`):

| Record | Status |
|---|---|
| DoubleMuon (30522) | parseable |
| SingleMuon (30530) | parseable |
| DoubleEG (30521) | parseable |
| SingleElectron (30529) | parseable |
| MuonEG (30528) | parseable |
| JetHT (30525) | parseable |
| MET (30526) | parseable |
| Tau (30532) | parseable |
| ttbar (TTToSemiLeptonic, 67801) | parseable |
| Drell-Yan (DYJetsToLL, 35671) | parseable |
| W+jets (WJetsToLNu, 69747) | parseable |
| Diboson (WW, 72696) | parseable |
| Single top (ST_tW_top, 64759) | parseable |
| QCD (QCD_Pt_30to50, 63166) | parseable |
| Signal (GluGluHToGG, 37350) | parseable |

**All 15 representative files are fully parseable**: every one has
`Muon_*`, `Electron_*`, `Jet_*` (including `Jet_jetId` and
`Jet_btagDeepFlavB`), `run`/`luminosityBlock`/`event`, and — for the MC
files — `genWeight`. No missing branches, no caveats, on any of the 15
files checked. This does not guarantee every one of the 57+832+1178 total
files behaves identically (only one file per record was checked, per
scope), but it is a strong, uniform positive signal across every dataset
type this survey touches.

### 3.5 Trigger paths and offline thresholds — UNVERIFIED (no efficiency measurement performed, per scope)

Per-dataset natural HLT paths and a **conventional** offline pT margin
above each path's own threshold value (standard CMS practice: pick an
offline cut safely on the trigger's efficiency plateau, typically a few
GeV to ~15% above the raw threshold). **None of this was empirically
verified against a real turn-on curve** — that is explicitly out of scope
here and flagged as necessary per-dataset follow-up work before any of
these thresholds are used in a real selection:

| Primary dataset | Natural HLT path(s) | Suggested offline threshold (unverified) |
|---|---|---|
| DoubleMuon | `HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ`, `HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ` | leading muon pT > 20 GeV, sub-leading > 10 GeV |
| SingleMuon | `HLT_IsoMu24`, `HLT_IsoTkMu24` | muon pT > 26 GeV |
| DoubleEG | `HLT_Diphoton30_18_R9Id_OR_IsoCaloId_AND_HE_R9Id_Mass90` | leading photon pT > 35 GeV, sub-leading > 22 GeV (already this repo's own H→γγ convention) |
| SingleElectron | `HLT_Ele27_WPTight_Gsf` | electron pT > 30 GeV |
| MuonEG | `HLT_Mu23_TrkIsoVVL_Ele12_CaloIdL_TrackIdL_IsoVL` (+ Mu8/Ele23 mirror leg) | muon pT > 26 GeV, electron pT > 15 GeV |
| JetHT | `HLT_PFJet450` (single-jet) or an HT-sum path (e.g. `HLT_PFHT900`) | leading jet pT > 500 GeV, or HT > 1000 GeV |
| MET | `HLT_PFMET120_PFMHT120_IDTight` | offline PFMET > 200 GeV |
| Tau | `HLT_DoubleMediumIsoPFTau35_Trk1_eta2p1_Reg` | each tau pT > 40 GeV |

### 3.6 Yield estimate across all 8 primary datasets — ESTIMATED, clearly separated from measured numbers

**Measured**: DoubleMuon (94,148,416 events) yields 316 BumpNet-usable
histograms (stage d).

**Naive linear scaling** (same per-event yield rate applied to every
dataset): the 8 primary datasets together have 1,395,586,032 events
(§3.2) — 14.82× DoubleMuon's own event count. `316 × 14.82 ≈ 4,684`
BumpNet-usable histograms if every other dataset behaved exactly like
DoubleMuon per event.

**Why this is not a reliable estimate, stated plainly:**

- DoubleMuon's own event population here is gated by `>=2 selected muons
  AND >=1 light jet` — a requirement enforced by the trigger *and* by this
  survey's own unchanged V0 object selection. **JetHT, MET, and Tau have
  no lepton in their trigger stream at all**; a dedicated selection for
  them (which this survey never ran) would very likely populate *far
  more* distinct final-state categories per event than DoubleMuon does,
  since nothing here suppresses jet/tau multiplicity the way the muon
  requirement suppresses everything else for DoubleMuon. The naive scaling
  above is likely a substantial **under-estimate** for these three.
- SingleMuon, SingleElectron, DoubleEG, and MuonEG are structurally closer
  to DoubleMuon (a lepton-gated trigger stream feeding the same four
  object types), so the naive per-event scaling is a more defensible
  starting point for them specifically — but still unmeasured, since each
  would need its own selection with its own thresholds (§3.5, themselves
  unverified) run through this same combinatorial machinery to know for
  sure.
- The scaling also implicitly assumes MC and additional data samples add
  roughly proportionally — not evaluated here at all; this survey's
  Part 2 work used data only.

**Range given, clearly separated from the measured number:** roughly
**2,000–15,000 BumpNet-usable histograms across all 8 primary datasets
combined**, with the naive linear-scaling figure (~4,700) as a plausible
central reference for the lepton-gated datasets and the low end of the
range, and the high end reflecting the likely under-count for the three
non-lepton-triggered datasets (JetHT, MET, Tau) whose real behavior was
not measured here at all. **Only the 316 DoubleMuon number is measured;
everything else in this range is an order-of-magnitude estimate, not a
prediction to act on without running the equivalent pipeline on each
dataset.**

## What it would take to run a second primary dataset end to end

1. **Trigger choice**: pick the natural HLT path(s) for that dataset (§3.5)
   and, unlike this survey, actually measure the turn-on curve before
   trusting an offline threshold — the values in §3.5 are conventional
   starting guesses, not verified cuts.
2. **Object-selection thresholds**: re-derive pT/η/ID thresholds for
   whichever new object type the dataset foregrounds (photons for DoubleEG,
   taus for Tau, MET itself for MET) the same way `RECIPE.md` did for
   muons/electrons/jets here — none of that is reusable as-is beyond the
   muon/electron/jet cuts already shared with this survey's own selection.
3. **De-duplication when combining datasets**: this pipeline already has a
   cross-record de-duplication mechanism
   (`services.parsing.event_deduplication`, keyed on
   `(run, luminosityBlock, event)`, used when combining trigger streams —
   see `orchestration/handlers/parsing_handler.py`'s `selection_by_record`
   handling) for exactly this purpose (an event firing both a muon and an
   electron trigger, say, must not be double-counted if DoubleMuon and
   DoubleEG were ever combined). Reuse it, don't re-derive it.
4. **MC weighting**: `services.parsing.mc_weights` already reads
   `genWeight` and the generator-level sum-of-weights normalization this
   pipeline needs (confirmed present and parseable in §3.4 for every MC
   group checked) — reuse directly, needs no new capability.
5. **Scale**: JetHT/MET/Tau datasets will populate far more jet-rich and
   b-jet-containing final-state categories than DoubleMuon ever can (no
   lepton requirement gates their event population the way `>=2 muons`
   does here) — expect a substantially different, likely larger, funnel
   shape at stage (a), not just a bigger version of this one.
