# HANDOFF — the #40 multiplicity rule as the default in both CMS builders (23 Oct 2026)

**Current step: 3 — proof tools pushed; checkouts and jobs next (see "Step 3").**
Nothing merged into master or the two existing feature branches; nothing sent; nothing upstream.

## Branches (origin only)

| branch | from | purpose |
|---|---|---|
| `feature/cms-data-multiplicity40-20261023` | `origin/feature/cms-btag-singleelectron-20261020` @ `c0e734b` | shared module, data builder option, tests |
| `feature/cms-mc-multiplicity40-20261023` | `origin/feature/cms-mc-btag-singleelectron-20261020` @ `dc760da` + merge of the data branch | MC builder option (step 2) |

## Step 0: preflight (VERIFIED BY RUNNING, 23 Oct)

- `upstream/master` = `29291ae` (nothing new since the sync); data branch = `c0e734b`; MC branch = `dc760da`.
- The source of `physics_calcs.limit_particles_in_fs` and `is_finalstate_contain_combination`
  is identical on both branches, on `upstream/master` and on `5fbf1ef`. Also checked:
  `c2488b7` (the PR #40 commit the ttbar study used) has the same `limit_particles_in_fs`.
  The whole `physics_calcs.py` has no diff between `5fbf1ef` and either branch.

## Step 1: data (all added/changed files are CMS-only; no `studies/` file exists upstream)

- NEW `studies/cms_datasets/common/multiplicity.py`:
  - `cap_label(label)` calls upstream's `physics_calcs.limit_particles_in_fs(label, 4)`;
  - `combination_allowed(capped, im)` calls upstream's `physics_calcs.is_finalstate_contain_combination`
    on the driver's own combination dict for that name (the 186 dicts come from
    `get_all_combinations` with the driver's constants, named with `prepare_im_combination_name`);
  - `regroup_shard`: the ttbar study's `apply_pr40_to_shard`, ported unchanged except for the two calls;
  - the capped-signature refusal, the report helpers, and `final_state_population` (MC report).
- `studies/cms_datasets/deliver/build_four_dataset_delivery.py` (the builder of the five-dataset
  matched5 delivery, used with `--datasets DoubleMuon,SingleMuon,DoubleEG,MuonEG,SingleElectron`):
  - `--multiplicity-rule {upstream40,exact}`, default `upstream40`. With `upstream40`, on the scratch
    copies and before the ≥100 rule, the labels are capped, the disallowed combinations are dropped and
    the arrays are merged. The event counts per final state are summed over the merged labels, so the
    ≥100 rule counts the merged populations. Before that, every pooled job's INCLUSIVE shard is checked
    for coverage-capped signatures that would merge (refused).
  - The output gains `multiplicity_rule_<prefix>.json` (per final state, the event counts before the ≥100
    rule, plus the label map) and one key, `"multiplicity_rule"`, in the build summary. Everything else
    is unchanged.
  - Text only: the docstring and README no longer say "FOUR datasets"; there is a five-dataset usage
    example; the README now gives e–μ overlap removal as dR < 0.12 (the driver's constant; it said 0.05)
    and has a "FINAL STATES" section that states the rule; the name example uses a final state
    that exists under both rules.
  - Not changed: the JSON `"what"` string and the summary file name `build_summary_rare4_four_dataset.json`.
    Other tools read them.
- `studies/cms_datasets/README_REBUILD.md`: to reproduce the 7 Oct delivery you now need
  `--multiplicity-rule exact`. `pbs_delivery.sh` passes no flags, so it now builds with the #40 rule.
- NEW `studies/cms_datasets/tests/test_multiplicity40.py`.

Local checks (Mac), VERIFIED BY RUNNING (`evidence/local_tests_data_branch.txt`):
- `test_multiplicity40.py`: **43/43**. These include:
  - a grid of 455 labels: `cap_label` == upstream == the rule as written, ≤ 4 objects;
  - 84,630 label × combination pairs == upstream == "every rank below the capped count";
  - synthetic data-style and MC-style shards (merge order, dropped combinations, events conserved,
    payloads unchanged, capped refusal);
  - copies of two real ttbar shards (78,384 and 532,684 events conserved; 163 → 49 and 194 → 51 labels).
- All six existing `studies/cms_datasets/tests/` scripts still pass.
- Synthetic five-dataset trial: `--multiplicity-rule exact` vs the unmodified builder at `c0e734b`.
  Both ROOT files are identical, and so is the manifest. The summary differs only by the added
  `"multiplicity_rule": "exact"` key (`evidence/local_synthetic_exact_vs_c0e734b.json`).
  Made-up shards, NOT a result.

## Step 2: MC (branch `feature/cms-mc-multiplicity40-20261023`)

- From `dc760da`, then a plain merge of the data branch (`baf3ff4`) with no conflict (merge `35d3542`).
  The merge also brings in the data branch's own study folder `studies/btag_se_20261020/`
  (documents, evidence and plots of the 20 Oct b-tag checks, no production code). That is
  expected, because the data branch has it.
- `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`: `--multiplicity-rule {upstream40,exact}`,
  default `upstream40`, using the shared module. Same place and logic as the ttbar study's `pr40`:
  per scratch shard, after the `_mcw` siblings exist and before the ≥100 rule. Its report
  gains `multiplicity_rule_upstream40` and, in both modes, `final_state_population_before_prune`.
  `multiplicity_pr40.py` is NOT on this branch (no second copy of the rule).
- `studies/cms_mc_weights_v3/tests/test_builder_end_to_end.py`: now passes `multiplicity_rule="exact"`.
  The test pins the exact-label build, including the coverage-cap path on `0e_2m_2j_1b`. Under the
  #40 default the builder refuses to merge that capped signature, which is correct.
- **Behaviour to know for the full run:** with the default rule, the MC builder (and the data builder)
  STOP if a coverage-capped signature (> 500,000 entries in one file) would be merged.
  The 49 ttbar files had 0 capped signatures. Other samples and data are UNVERIFIED.

Local checks (Mac), VERIFIED BY RUNNING:
- All 6 MC test scripts and `test_multiplicity40.py` pass (`evidence/local_tests_mc_branch.txt`).
- Two-file local MC trial (the ttbar study's local copies of 17 Oct 67801 files 0 and 7; NOT a result),
  compared with the study's own local builds (`evidence/local_mc_trial_2files.json`):
  - new default `upstream40` == the study's `pr40`, **bit for bit, 174/174** histograms;
  - new `exact` == the study's `exact`, **1,525/1,525**.

## Step 3: proof on the cluster (plan; the tools are on the MC branch)

- `studies/multiplicity40_20261023/compare_root.py`: bit-for-bit ROOT comparison, ported unchanged
  from the ttbar study's `compare_builds.py`.
- `studies/multiplicity40_20261023/rule_check.py`: R1–R7 for `--kind data|mc`, adapted from the ttbar
  study. R2 is checked against upstream's `limit_particles_in_fs` itself. Tried locally on the
  synthetic data builds and the two-file MC builds: all pass (NOT results).
- `studies/multiplicity40_20261023/cluster/pbs_proof.sh`, with `WHAT=`:
  - `mc_upstream40`, `mc_exact`: MC builder on `work/ttbar_pr40_20261021/runs` (read-only),
    `--records 67801 --output-mode per-sample`, as in the ttbar study;
  - `data_upstream40`, `data_exact`: data builder on `work/sync42_20261023/runs/new/data`
    (read-only), `--datasets <five> --out-prefix proof`, as in the sync42 proof;
  - `check`: the comparisons and the rule checks.
- Cluster preflight (23 Oct, 22:26 IDT, `wipp-home`; `wipp-campus` timed out once), VERIFIED BY RUNNING:
  - file count **122,878**; nothing queued;
  - every input present; the 10 data rare4 shards have 0 coverage-capped signatures.
- Checkouts: `checkouts/mult40_20261023/{data,mc}`. Work: `work/mult40_20261023/{logs,mc,data,evidence}`.

## How to resume

1. `git fetch origin`; the branches above; this file's "Current step" line.
2. On the cluster: `/opt/pbs/bin/qstat -u berkom -t`. Never resubmit a job that is queued, running or finished.
