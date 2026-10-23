# The #40 multiplicity rule as the default in both CMS builders — report (23 Oct 2026)

**In one line:** both CMS builders now apply upstream #40's max-4-objects rule by default, using
upstream's own functions. The new default reproduces the 21 Oct ttbar #40 test bit for bit. The
`exact` option reproduces the old outputs bit for bit (MC ttbar and the 23 Oct data proof). Every
rule check passes on data and MC. No new production was run; nothing was merged into master or
the existing feature branches; nothing was sent.

Every number below is VERIFIED BY RUNNING unless marked UNVERIFIED.

## What changed

| | |
|---|---|
| Shared module | NEW `studies/cms_datasets/common/multiplicity.py`. `cap_label` = upstream `physics_calcs.limit_particles_in_fs(label, 4)`; `combination_allowed` = upstream `physics_calcs.is_finalstate_contain_combination` on the driver's own combination dict. Both are called, not copied. The regroup/merge helper is ported from the ttbar study. |
| Data builder | `studies/cms_datasets/deliver/build_four_dataset_delivery.py` (the five-dataset matched5 delivery): `--multiplicity-rule {upstream40,exact}`, default `upstream40`. Applied on the scratch copies before the ≥100 rule: labels relabelled, disallowed combinations dropped, arrays merged, event counts summed. Docstring and README text fixed. |
| MC builder | `studies/cms_mc_weights_v3/deliver/build_mc_delivery.py`: the same option and default, at the place the ttbar study proved (after the `_mcw` weights, before the ≥100 rule). `multiplicity_pr40.py` is not carried over, so there is no second copy of the rule. |
| Not changed | The per-file production code, selection, isolation, b-tag 0.2489, overlap removal, triggers, thresholds, binning, peak/outlier cuts, normalisation, cross sections. No upstream file (the gate printed nothing before every push). |

How the rule works on CMS outputs: the per-file outputs keep the EXACT labels (e.g. `0e_1m_5j_0b`).
At build time:
- each label becomes upstream's capped label (`0e_1m_3j_0b`: light jets fill the slots left
  by e + m + b, at most 4 objects);
- any mass combination that uses a jet beyond those slots is dropped (e.g. `j0j1j2j3` under 3 jets);
- the mass arrays (and for MC the weights and every per-event sibling) of exact labels that land
  on the same name are merged;
- the ≥100-events rule then counts the merged final states.

## Proof on the cluster (no new production)

Jobs `5311261`–`5311265` (queue N, io=25), all exit 0. Code: pinned clones
`checkouts/mult40_20261023/data` @ `baf3ff4` and `.../mc` @ `c00d0ab`. Outputs in
`work/mult40_20261023/`. Inputs read-only: `work/ttbar_pr40_20261021/` and `work/sync42_20261023/`.

### Bit-for-bit comparisons

| new build | reference | histograms | result |
|---|---|---|---|
| MC ttbar 67801, **default (upstream40)** | `ttbar_pr40_20261021/build_pr40` | 302 / 302 | **identical** |
| MC ttbar 67801, `--multiplicity-rule exact` | `ttbar_pr40_20261021/build_exact` | 3,606 / 3,606 | **identical** |
| data five files, `--multiplicity-rule exact`, uncropped ROOT | sync42 proof NEW data delivery | 548 / 548 | **identical** |
| data, same, cropped ROOT (the BumpNet file) | sync42 proof NEW data delivery | 548 / 548 | **identical** |

Identical means:
- the same names;
- per histogram, the bin contents and variances (flow bins included) are equal byte for byte;
- the edges, title, entry count and class are identical.

The data manifest is identical too. The data build summary differs by exactly one added key,
`"multiplicity_rule": "exact"`, which is intended (`evidence/cluster/compare_data_exact_vs_sync42_new_delivery.json`).

### Rule checks R1–R7 (upstream40 vs exact, same inputs)

| check | data (smoke) | MC ttbar |
|---|---|---|
| R1 ≤ 4 objects per final state | pass (33) | pass (48) |
| R2 labels == upstream `limit_particles_in_fs(x, 4)` (every input label too) | pass (160 labels) | pass (275 labels) |
| R3 no histogram uses a dropped jet | pass (201) | pass (302) |
| R4 every final state ≥ 100 events; removed set == below 100 | pass (min 168) | pass (min 126) |
| R5 name format, class, title, binning as the exact build | pass | pass |
| R6 events conserved before the ≥100 rule, total and per final state | pass: 1,740,044 = 1,740,044 | pass: 25,076,583 = 25,076,583; weighted 805,672.2086 both (relative difference < 1e-12) |
| R7 no NaN/inf, no negative variance | pass | pass |
| final states the rule does not change: histograms identical | 51 / 51 | 67 / 67 |

For data, R4's "removed set" is derived from the event counts, because the data builder does not list
the removed final states. For MC it comes from the build report.

### Counts, exact vs upstream40

| | data smoke (5 files, NOT physics) | MC ttbar 67801 (49 files) |
|---|---|---|
| histograms | 548 → **201** | 3,606 → **302** |
| final states with histograms | 50 → **33** | 169 → **48** |
| labels before the ≥100 rule | 160 exact → 52 | 275 exact → 55 |
| final states removed by the ≥100 rule | 108 → 17 | 104 → 5 |
| events kept after the ≥100 rule | 1,738,270 → 1,739,798 | 25,074,750 → 25,076,525 |
| exact labels below 100 events that survive after merging | 67 labels, 1,528 events | 90 labels, 1,775 events |

The five data files are one file per dataset, a smoke test. The data counts show the machinery
works; they are not the counts a full run will give (UNVERIFIED for the full run).

## Plots (`plots/`, made on the Mac from the rule-check JSONs)

- `data_histograms_per_final_state.png`, `mc_histograms_per_final_state.png`: per #40 final state,
  the number of histograms, exact (summed over the merged labels) vs upstream40.
- `data_merged_example.png`: `m0j0` in `0e_1m_3j_0b`, which merges exact 3j/4j/5j/6j (7j–10j
  have no exact histogram).
- `mc_merged_example.png`: `j0b0b1` in `0e_1m_1j_2b`, which merges exact 1j–8j (9j–11j have no
  exact histogram).
- In both examples, each exact histogram had its own peak cut, so the stack need not equal the merged line.

## Things to know

1. **Coverage-capped signatures.** If a mass list was capped in a file (> 500,000 entries, random
   subsample) and its label would be merged, both builders STOP rather than build. A merged
   subsample cannot equal what #40 would store. The 10 data shards and 49 ttbar files used here have
   0 capped signatures. Whether any full-run file has one is UNVERIFIED, so the full run will tell.
2. **Merge order.** For MC, merged entries are ordered by exact label and then by file. #40 itself
   would store them in file order, which could change a weighted bin sum by float64 round-off
   (the effect accepted on 17 Oct). Data histograms are counts and do not depend on the order.
3. `pbs_delivery.sh` (7 Oct) passes no flags, so it now builds with the #40 rule. To reproduce the
   7 Oct or 23 Oct exact-label deliveries, add `--multiplicity-rule exact` (README_REBUILD.md).
4. One existing MC test (`test_builder_end_to_end.py`) now passes `exact` explicitly. Its synthetic
   capped signature would be merged under #40 (point 1).

## Evidence

- `evidence/cluster/`: the 5 comparison JSONs, `rule_check_data.json`, `rule_check_mc.json`,
  the data upstream40 label map (`data_upstream40_multiplicity_rule_proof.json`), `jobids.txt`.
- `evidence/local_*`: Mac test runs and the local trials (not results).

## Next step

The full data (five datasets, matched5) and MC delivery builds with the new default, from the per-file
outputs of a full run. Watch for the coverage-cap STOP (point 1). Nothing was started; this needs Matan's go-ahead.
