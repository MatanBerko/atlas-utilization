# HANDOFF — cms-mc-weights-v3, implementation round

Everything needed to pick this up without re-deriving anything.
The design round's own handoff is `HANDOFF.md`; this file covers the
implementation (DESIGN.md Steps 1–5, Parts B/C/D of the implementation prompt).

**Branch:** `feature/cms-mc-weights-v3`, pushed to `origin`
(`https://github.com/MatanBerko/atlas-utilization`), branched from
`design/cms-mc-weights-v3` = `8b17e28`.
**Date:** 2026-10-11 (cluster work 2026-10-10 IDT).
**Scope delivered:** `--is-mc` mode, sibling storage, the prune fix, the
registry, the MC delivery builder, the data-path regression, ONE single-file
MC smoke test, and the test suites.
**Not done, by instruction:** the 98-file pilot, any other MC file, any full
MC production, any delivery to Maryna.

---

## Commits

| Commit | What |
|---|---|
| `5f9faba` | The implementation: `--is-mc`, siblings in the funnel, the prune fix, the registry + generator, the MC builder, the weighted-histogram module, both test suites. |
| `6b02224` | Part B plumbing: the mapping generator, and job-dir naming that lines up with the delivered production. |
| `ceda81e` | Part C plots: show the 4-lepton spectrum before post-processing as well as the delivered bins. |
| `e48032d` | Emit `mc_diagnostics` only under `--is-mc` (see "the one difference the first regression found"). |
| `3c47315` | `MCV3_EVIDENCE_DIR`, so a cluster test run cannot dirty a pinned checkout. |
| `cd67372` | Part B: compare against the REAL old prune code loaded from git history, not a monkeypatched regex. |
| `343c946` | Part C: show the Z cut acting on the same-flavour dilepton mass. |
| *(final)* | Evidence, plots and this handoff. |

## What changed, and where

```
services/storage/sqlite_shards.py                     <- the ONLY services/ change
studies/cms_datasets/cluster/run_dataset_on_file.py   <- --is-mc, all of it guarded
studies/cms_mc_weights_v3/
    cms_mc_normalisation_v3.json      <- 13 records, generated
    build_registry.py                 <- its generator; --check proves they match
    sources/                          <- the v2 inputs, copied verbatim, read-only
    deliver/build_mc_delivery.py      <- the MC delivery builder
    deliver/weighted_histograms.py    <- TH1D + Sumw2 fill, write and read-back
    deliver/plot_smoke_test.py        <- Part C plots and the closure check
    cluster/pbs_data_regression.sh    <- Part B jobs
    cluster/pbs_mc_smoke.sh           <- Part C job
    cluster/make_data_regression_mapping.py
    cluster/compare_data_regression.py
    cluster/check_prune_regex_data_neutral.py
    tests/test_mc_weights_v3.py       <- 46 self-checks
    tests/test_builder_end_to_end.py  <- 20 end-to-end checks on a synthetic job
    evidence/, plots/
```

Nothing else in the repository was modified.

## Cluster

Reached over `ssh wipp-home` (`wipp-campus` timed out, as in the design round).
Work directory, created new for this round and the only place written:

```
/storage/agrp/berkom/atlas-utilization/work/cms_mc_v3_impl_20261011/
    repo/                     pinned checkout
    data_files.txt            the Part B mapping (8 files)
    data_regression/          first regression run   (superseded)
    data_regression2/         second regression run  (the reported one)
    mc_smoke/                 first smoke run        (superseded)
    mc_smoke2/                second smoke run       (the reported one)
    final/delivery/           MC build, real >=100 rule
    final/diagnostic/         MC build, only --min-events-per-fs relaxed to 1
    final/plots_delivery/     the delivered plots
    final/plots_diagnostic/   the 4-lepton plot
    prune_scratch/            copies for the prune-neutrality check
    evidence/                 the two Part B reports
    logs/                     job logs (see the caveat below)
```

`conda` is activated through `/usr/wipp/conda/24.5.0/etc/profile.d/conda.sh`
inside the PBS scripts; interactive work uses the env's interpreter by
absolute path, because `conda` is not on a non-interactive shell's PATH.
`qsub`/`qstat` are at `/opt/pbs/bin/`, also not on that PATH.

### Jobs

| Job ID | What | Output |
|---|---|---|
| `5208245[1-8]` | Part B regression, first run, at `6b02224` | `data_regression/` — **superseded** |
| `5208246` | MC smoke test, first run, at `6b02224` | `mc_smoke/` — **superseded** |
| `5208272[1-8]` | Part B regression, the reported run | `data_regression2/` |
| `5208273` | MC smoke test, the reported run | `mc_smoke2/` |

Queue `N` (ran in `shortE`), `#PBS -m n`, 1 cpu, 8 GB, 2 h walltime,
`-l io=25`. No job was submitted beyond the 8 data files and the 1 MC file
this round allows.

**Two process caveats, recorded because they affect how the evidence reads:**

1. **The pinned checkout was changed while `5208272[]` was running.** It
   should not have been. The jobs' own metadata records what each actually
   ran: **1 job at `3c47315`, 7 at `cd67372`**. The result is unaffected, and
   this is checkable rather than asserted —
   `git diff 3c47315 cd67372 -- studies/cms_datasets/ studies/m0m1j0_cms/ services/`
   is **empty**; the only files differing between those commits are
   `check_prune_regex_data_neutral.py` and `plot_smoke_test.py`, neither of
   which the driver imports or runs. Next time: one checkout per in-flight
   array, or a separate checkout per job.
2. **`5208272[]`'s logs were discarded.** Its `-o`/`-e` directory
   (`logs/data_regression2/`) was never created, so PBS had nowhere to deliver
   them. The jobs themselves are fine — all 8 wrote a complete
   `job_metadata.json`, which the driver writes only as its last step — and
   each job's commit, inputs and counts are recoverable from that file, which
   is where the table above comes from. Next time: `mkdir -p` the log
   directory before `qsub`, not after.

---

## Results

Every number below is **VERIFIED BY RUNNING**.

### Part B — the data path is unchanged

`evidence/data_regression.json`. 8 data files, 2 per dataset, each pair the
lowest and highest job index the delivered production has — which also puts
the two in different run eras (G and H).

| | |
|---|---:|
| jobs compared | 8 |
| shard files compared | 64 |
| signatures compared | 34,079 |
| array entries compared | 19,715,117 |
| arrays bit-identical | 34,079 (all) |
| shard files **byte**-identical | **64 of 64** |
| `final_state_counts` rows differing | 0 |
| `shard_metadata` values differing | 0 |
| `job_metadata.json` keys compared | 31 per job |
| **total differences** | **0** |

Keys excluded from the `job_metadata.json` comparison, as legitimately
different between two runs of the same code: `created_utc`, `git_commit`,
`elapsed_sec`, `inclusive_shard_size_mb`, `exclusive_shard_size_mb`. The two
size keys were in fact equal in every job; they are excluded on principle
because SQLite page layout need not be.

The delivered production is opened `mode=ro&immutable=1`, so the comparison
*cannot* write to it.

**The one difference the first regression found.** Run `5208245[]` reported
exactly one difference per job: the data path's `job_metadata.json` had gained
a `"mc_diagnostics": null` key. All 56 shards were already byte-identical and
all 25,719 signatures / 12,315,185 entries bit-identical, so nothing physical
had changed — but a new key is still a difference. `e48032d` moved that key
inside the existing `if args.is_mc` block, and the re-run came back with zero
differences of any kind.

### Part B, second check — the `services/` change is data-neutral

`evidence/prune_regex_data_neutral.json`. The pre-change
`services/storage/sqlite_shards.py` is loaded **out of git history at
`db1bd32`** and executed, so "the old behaviour" is the real old code, not a
transcription. Both versions prune independent scratch copies of the same 8
delivered shards.

| | |
|---|---:|
| shards | 8 |
| signatures before prune | 7,532 |
| signatures after prune | 2,310 |
| entries before / after | 2,752,801 / 2,713,962 |
| final states removed, **new** code | 88 |
| final states removed, **old** code | 88 |
| differences | **0** |

A first attempt swapped only the compiled pattern and died with a
`ValueError`, because the new body unpacks three groups and the old pattern
has two. That is why the check loads the whole old module instead; it also
refuses to report a pass if the module it loaded does not carry the
pre-change pattern.

### Part C — the single-file MC smoke test

Record **37728** (`GluGluHToZZTo4L_M125`), portal file index 0, 4,000 events,
175 s wall. `evidence/mc_smoke_job_metadata.json`.

*Driver:*

| | |
|---|---:|
| events read | 4,000 |
| simulation assertion | passed; golden-JSON filter skipped |
| after the 7-path trigger OR | 2,550 |
| **stored** | **2,076** |
| DoubleMuon / SingleMuon / DoubleEG / MuonEG accepted | 587 / 1,230 / 307 / 101 |
| Ele27 candidate accepted | 889 |
| **stored by the Ele27 candidate ONLY** | **534** (25.7% of stored) |
| Σ(genWeight) vs `Runs.genEventSumw` | rel. diff **2.3e-9** (tolerance 1e-6) — passes |
| event count vs `genEventCount` | 4,000 = 4,000 |
| `_mcRunNumber` distinct values | `[1]` — confirms it carries no information |
| TrigObj bit-2 title assertion | passed |
| Version B kept / rejected | 2,073 / 3 |
| sibling writes (rare4) | 4,450 = 890 signatures × 5 siblings |
| coverage cap triggered | 0 signatures (4,000 events is far below 500,000) |

The 534 figure is the direct justification for storing the SingleElectron
candidate: a quarter of the stored events would not exist without it.

*Builder (delivery build, the real ≥100 rule):*

| | |
|---|---:|
| Σw over surviving files | 1.15813237e5 (1 file in, 0 excluded) |
| normalisation factor | 1.9033806e-3 |
| final states removed by the ≥100 rule | 63 |
| orphan sibling rows after the prune | **0** |
| entries dropped by the event union (Ele27-only) | 242 |
| histograms delivered | 4 (TH1D + Sumw2, all read-back assertions passed) |

Raw and weighted yields per final state:

| final state | raw entries | weighted |
|---|---:|---:|
| `0e_2m_1j_0b` | 520 | 28.194 |
| `0e_2m_0j_0b` | 336 | 18.190 |
| `2e_0m_0j_0b` | 191 | 10.456 |
| `0e_1m_1j_0b` | 187 | 10.211 |

*Closure check:* the sum of the delivered histograms' integrals is
**19.7724059113188**, and `sigma_eff × 1000 × L_fb × (Σ(genWeight·L1prefire)
over the delivered entries / Σw)` recomputed independently gives
**19.772405911318803** — a relative difference of **1.8e-16**, i.e. float64
round-off. The normalisation is applied once, consistently, and nothing is
lost between the weight arrays and the histograms.

*Negative/empty-bin inventory:*

| build | histograms | bins ≤ 0 in the filled range | of those, bins that were FILLED and still ≤ 0 |
|---|---:|---:|---:|
| delivery (≥100) | 4 | **0** | 0 |
| diagnostic (≥1) | 752 | 4,301 | **7** (all strictly < 0) |

The split matters: 4,294 of those are bins that were never filled at all — a
statistics problem — and only 7 are genuine negative-weight cancellations.
This sample is powheg with a 0.38% negative-weight fraction; the NLO samples
(DY 16.3%, WZ 17.0%, TTW 21.9%, TTZ 24.8%, all measured in the design round)
will be far worse, which is what the open question for Maryna is about.

**This is a smoke test, not a physics result.** Σw comes from one file, so
every weight is normalised as if that file were the whole 8-file sample. The
vertical scale of every plot is therefore meaningless as physics. The build
report carries this warning in its own `SMOKE_TEST_WARNING` field.

### Part C plots

`plots/smoke_4lepton_mass.png` — 4mu, 4e and 2e2mu. **Every 4-lepton entry in
the file lands in the 125 GeV bin**, in all three channels, which is exactly
where a ggH→ZZ→4l sample should put them. There are only 5 / 2 / 3 raw
entries respectively, so there is a spike and no shape. Each panel shows both
the spectrum before post-processing and the bins the delivery keeps.

No 4-lepton category survives the ≥100-entries rule on one 4,000-event file,
so this plot comes from the **diagnostic** build, which relaxes *only*
`--min-events-per-fs` (1 instead of 100) and changes nothing else. The
delivery build keeps the rule unchanged.

`plots/smoke_dilepton_mass.png` — the same-flavour dilepton mass with the
110 GeV Z cut drawn on it. mumu peaks at 95 GeV, ee at 85 GeV, and **neither
reaches the delivery**: in a ggH→ZZ→4l sample the same-flavour pairs sit at or
below the Z mass, so the Z cut removes them entirely. The third panel is the
muon+jet mass, which does survive.

### Part D — tests

| suite | checks | pass | fail |
|---|---:|---:|---:|
| `tests/test_mc_weights_v3.py` | 46 | 46 | 0 |
| `tests/test_builder_end_to_end.py` | 20 | 20 | 0 |
| **total** | **66** | **66** | **0** |

Run on Windows and again on the cluster, same result. Covered: alignment
property tests over 200 random mask chains through the whole chain; the
orphan-sibling regression (zero orphans where there were four) and its
data-neutrality; Sumw2 read-back including a negative weight, plus an absent
Sumw2 failing the build; registry closure, the k/eps pinning, 37728's BR, and
the committed JSON matching its generator; the campaign guard accepting
postVFP and rejecting APV/preVFP; and parity of every v3 mirror against the
shared data-side function at unit weights.

The repo's own `tests/test_global_final_state_threshold.py`, which exercises
the pruning function directly, passes **5/5** on the cluster. It cannot run on
Windows: the shared `prune_final_states_below_min_events` opens its SQLite
connections with `with sqlite3.connect(...)`, which commits but does not
close, so the temp files stay locked. That is pre-existing behaviour in
`services/`, out of scope for this round's one-line change, and worth fixing
when `services/` is next touched.

`studies/cms_datasets/tests/test_electron_datasets.py` reports 109 checks,
1 failure. That failure is **pre-existing**: it reproduces identically at the
base commit `8b17e28` in a throwaway worktree, with the same message. It is a
"NOTED" observation about upstream's one-digit capping, not a regression.

---

## Decisions taken inside this round

* **The funnel is shared with the data path**, not duplicated for MC. The
  prompt asked that every new statement sit behind `if args.is_mc`;
  `run_combination_funnel` has no access to `args`, so its guard is
  `mc_siblings is not None` — the same condition one call-frame up. DESIGN.md
  D1 requires MC to use the identical selection code path, and a second copy
  of those ~90 lines could drift from the delivered one, which would be a
  physics bug. Part B proves the data output is unchanged.
* **A sixth acceptance bit** (32) records the bare `HLT_Ele27_WPTight_Gsf`
  fire decision. DESIGN.md D3 left this as a one-line choice; it is taken,
  because an un-matched fire is otherwise indistinguishable from no fire at
  all and the Ele27 efficiency cannot be measured without it.
* **`--dataset-label MC`** is a new choice, valid only with `--is-mc`. It
  names the job and the signature prefix and carries no selection meaning.
  Existing data invocations are unaffected.
* **The ≥100 rule is applied once over every sample's shards together**, not
  per sample, so all samples share one surviving final-state set and the
  per-sample and summed files agree on which categories exist.

## Open and unchanged

* Everything in DESIGN.md's **Open questions** (for Yuval and for Maryna) is
  still open. Nothing there was decided.
* `--peak-on`, `--min-events-basis` and the output mode are build-time
  options, so an answer from either of them needs a re-build, not a re-run of
  the MC production.
* **No negative-bin fix** is implemented; only the inventory is reported.
* The b-tag WP stays at `0.2598` on both sides.
* SingleElectron is **stored and ignored**: the builder's event union is the
  four data acceptance flags only.

## How to resume

1. `git fetch origin && git checkout feature/cms-mc-weights-v3`.
2. `python studies/cms_mc_weights_v3/tests/test_mc_weights_v3.py` and
   `..._end_to_end.py` — 66 checks, no cluster needed.
3. Nothing needs cleaning up. No job is running, no production is part-way
   through, nothing under `output/` or in the earlier work directories was
   written to.
4. The next round is the 98-file pilot (67801, 35669, 37728) — **not started,
   and it needs Matan's go-ahead.** Its shape, from this round's measurements:
   one job per file, 98 jobs; the smoke-test file took 175 s for 4,000 events,
   but per-file event counts in these samples run to 1.9 M (design round C5),
   so per-file walltime must be estimated from the delivered data production's
   own timings before submitting. Build with
   `build_mc_delivery.py --runs-dir <pilot runs> --records 67801,35669,37728`,
   then the data/MC comparison plots.
