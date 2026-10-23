# HANDOFF — the #40 multiplicity rule as the default in both CMS builders (23 Oct 2026)

**Current step: 1 DONE (data branch committed and pushed). Next: step 2 (MC branch).**
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

## How to resume

1. `git fetch origin`; the branches above; this file's "Current step" line.
2. On the cluster: `/opt/pbs/bin/qstat -u berkom -t`. Never resubmit a job that is queued, running or finished.
