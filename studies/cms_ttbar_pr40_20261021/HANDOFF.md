# HANDOFF — CMS ttbar with the PR #40 multiplicity rule (21 Oct 2026)

**Current step: 3 done (code + local checks). Next: step 4, cluster production of 67801.**
A TEST for Maryna, not a delivery. Nothing merged; nothing sent; nothing upstream.

- Branch: `study/cms-ttbar-pr40-20261021` (origin only), from
  `origin/feature/cms-mc-btag-singleelectron-20261020` @ `cd22aa2`.
- Upstream PR #40 fetched (only) as `refs/remotes/upstream-pr/40` =
  `c2488b77e497813bba2da4a46d411d1f834e69f9` (two commits on top of #35:
  3b42195, c2488b7). The CMS production code is unchanged.
- Upstream base of the branch (gate): `7f2da5d`. Upstream master is at `9af30d2` (#39, not synced).

## Step 1: what the code does (plain words)

- **Per-file outputs.** Each MC file gives one database (`dataset_shard_rare4_inclusive.sqlite`).
  Each event gets one *exact* label, e.g. `0e_1m_5j_0b` (counts of electrons, muons, light jets
  and b-jets; the CMS code rejects events with leptons + b-jets > 4). For every label the code
  stores every one of the 186 mass combinations the label contains, e.g. `m0j0j1j2` =
  leading muon + the three leading light jets (the number is the pT rank). The rows are named
  `MC_record<r>_file<i>_FS_<label>_IM_<combination>`, and each comes with its per-event
  siblings (`_mcraw_genw`, `_mcraw_l1pf`, `_mcraw_acc`, …). A table `final_state_counts` holds
  the number of events per label.
- **Builder** (`build_mc_delivery.py`). It copies the shards to scratch and writes each entry's
  MC weight `_mcw` (genWeight × L1 prefiring × σ·L/Σw). Then it applies the ≥100-raw-events
  rule once (counted from `final_state_counts`), using `cms_shard_pruning.py`. That file is
  upstream's pruning function plus one change: it deletes a removed final state's sibling
  rows too, and never counts them as events. The builder then groups by histogram name, keeps
  the events in the five-flag union, and applies to masses and weights together: the Z cut,
  the max-mass cut, peak removal and the outlier split. Finally it writes TH1D + Sumw2.
- **Checked on real 17 Oct 67801 shards (files 0 and 7), VERIFIED BY RUNNING:**
  - Every label stores exactly the combinations it allows: 0 mismatches over 161 and 192 labels.
  - The label counts add up to the kept events (78,384 and 532,684), so each event is in exactly one label.
  - Every combination holds one entry per event of its label (0 exceptions over 3,369 and 4,393 signatures).
  - In all 49 17 Oct files: 0 capped signatures (largest 5,600 entries; the cap is 500,000) and no skipped combinations.
  - **Conclusion:** merging at build time gives exactly the entries #40 would store. The one
    difference is the *order* of entries inside a merged array (exact labels in ascending
    multiplicity, then file order). That can move a weighted bin sum by float64 round-off,
    the known sparse-peak-tie effect accepted on 17 Oct (`FINDING_PEAK_TIES.md`).

## Step 2: code (all CMS-only files; none exists upstream, checked with `git ls-tree`)

- NEW `studies/cms_mc_weights_v3/deliver/multiplicity_pr40.py`:
  - `cap_label` (#40's logic, c2488b7);
  - `combination_allowed`;
  - `apply_pr40_to_shard` (renames, drops and merges rows and their siblings in place, keeping
    the payload bytes unchanged; refuses a capped signature);
  - `final_state_population` (read-only report numbers).
- `build_mc_delivery.py`: adds `--multiplicity-rule {exact,pr40}` (default `exact`), which runs
  just before the ≥100 rule. The report also gains `final_state_population_before_prune`, in
  both modes. With `exact` the shards are not touched.
- NEW `studies/cms_mc_weights_v3/tests/test_multiplicity_pr40.py`
- NEW in `studies/cms_ttbar_pr40_20261021/`: `check_oracle.py`, `audit_production.py`,
  `compare_builds.py`, `rule_check.py`, `cluster/pbs_post.sh`

## Step 3: local checks (Mac), VERIFIED BY RUNNING

- Oracle (c2488b7 extracted with `git archive` into the scratchpad, outside the repo; run in a
  separate process): `cap_label` agrees with `limit_particles_in_fs(label, 4)` on **455/455**
  grid labels, and `combination_allowed` agrees with `is_finalstate_contain_combination` on
  **84,630/84,630** grid label × 186-combination pairs. (`evidence/local_oracle_grid.json`)
- `test_multiplicity_pr40.py`: **19/19** pass, including on a copy of real file 7: 194 exact
  labels → 51 final states, events conserved (532,684). (`evidence/local_test_multiplicity_pr40.txt`)
- The existing tests pass: end-to-end, SingleElectron flag, peak scope, selfchecks, #35 drift, pruning drift.
- 2-file local trial (17 Oct files 0 and 7, metadata patched locally so the builder accepts
  them; NOT a result). Exact vs the unmodified cd22aa2 builder: **bit-identical**, 1,525
  histograms. The pr40 build has 174 histograms, and R1–R7 all pass. (`evidence/local_trial_2files.json`)
- The oracle on the trial's production labels: 197/197 labels and 4,455/4,455 stored pairs agree.

## Plan for the cluster (steps 4–6)

Checkouts: `/storage/agrp/berkom/atlas-utilization/checkouts/ttbar_pr40_20261021/{repo,base}`.
Work: `/storage/agrp/berkom/atlas-utilization/work/ttbar_pr40_20261021/{mappings,runs,logs,evidence}`.
Production uses `cluster/pbs_mc_pilot.sh` (MEM=6gb, walltime 02:00:00, io=25), then
`cluster/pbs_post.sh` with WHAT=audit, build_exact, build_pr40, build_base, compare and rulecheck.

## How to resume

1. `/opt/pbs/bin/qstat -u berkom -t`. Never resubmit an array that is queued, running or finished.
2. Read the latest section of this file for job IDs and the next step.
