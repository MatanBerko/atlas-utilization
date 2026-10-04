# Step 2 - combination counts per category: ours vs upstream PR #31

Produced by RUNNING both codebases (`step2_enumerate.py` once per repo, then
`step2_compare.py`). Each side used its OWN `get_all_combinations` and its own
final-state containment function; nothing was shared between the two runs.

* our checkout head: `4e9e0892e629bfd96edb90105f18d90816d3aa17`
* PR #31 head: `81dd40aa6a0713088e811ae2732558766d854691` (upstream `refs/pull/31/head`, read-only)

## Totals

| quantity | ours | PR #31 |
|---|---:|---:|
| combination patterns generated | 186 | 186 |
| categories enumerated | 170 | 170 |
| sum over categories of combinations allowed | 3258 | 3258 |
| categories whose combination set differs | 0 | 0 |

Combination pattern sets identical: **True**.  
Combinatorics configs identical: **True**.

Config actually used by each side:

| parameter | ours | PR #31 |
|---|---|---|
| `include_subleading` | `True` | `True` |
| `max_count` | `4` | `4` |
| `max_particles` | `4` | `4` |
| `max_subleading_index` | `1` | `1` |
| `max_total_particles` | `4` | `4` |
| `min_count` | `1` | `1` |
| `min_particles` | `1` | `1` |
| `object_types` | `['Electrons', 'Muons', 'Jets', 'BJets']` | `['Electrons', 'Muons', 'Jets', 'BJets']` |

* ours config read from: studies/cms_datasets/cluster/run_dataset_on_file.py module constants
* PR #31 config read from: PR #31 config.yaml mass_calculation_task_config
* ours containment: `services.calculations.physics_calcs.is_finalstate_contain_combination`
* PR #31 containment: `services.calculations.im_calculator.IMCalculator.does_final_state_contain_combination`
* final-state label shape, 1e/2mu/3j/1b: ours `1e_2m_3j_0g_0t_1b`, PR #31 `1e_2m_3j_1b`

## Categories where the combination sets differ

**None.** Every one of the 170 categories allowed by the rule gets exactly the same set of
invariant-mass combinations from both codebases.

## Per-category combination counts (all 170 categories)

`j` is the LIGHT-jet count. For PR #31 `4j` means exactly 4; for us `4j` is the
display-capped label for 4 OR MORE light jets. That difference changes which
EVENTS land in the category, not which combinations the category allows.

| category (e_m_j_b) | combinations ours | combinations PR #31 | same set |
|---|---:|---:|:---:|
| `0e_0m_0j_2b` | 1 | 1 | yes |
| `0e_0m_0j_3b` | 2 | 2 | yes |
| `0e_0m_0j_4b` | 3 | 3 | yes |
| `0e_0m_1j_1b` | 1 | 1 | yes |
| `0e_0m_1j_2b` | 4 | 4 | yes |
| `0e_0m_1j_3b` | 6 | 6 | yes |
| `0e_0m_1j_4b` | 7 | 7 | yes |
| `0e_0m_2j_0b` | 1 | 1 | yes |
| `0e_0m_2j_1b` | 4 | 4 | yes |
| `0e_0m_2j_2b` | 11 | 11 | yes |
| `0e_0m_2j_3b` | 14 | 14 | yes |
| `0e_0m_2j_4b` | 15 | 15 | yes |
| `0e_0m_3j_0b` | 2 | 2 | yes |
| `0e_0m_3j_1b` | 6 | 6 | yes |
| `0e_0m_3j_2b` | 14 | 14 | yes |
| `0e_0m_3j_3b` | 17 | 17 | yes |
| `0e_0m_3j_4b` | 18 | 18 | yes |
| `0e_0m_4j_0b` | 3 | 3 | yes |
| `0e_0m_4j_1b` | 7 | 7 | yes |
| `0e_0m_4j_2b` | 15 | 15 | yes |
| `0e_0m_4j_3b` | 18 | 18 | yes |
| `0e_0m_4j_4b` | 19 | 19 | yes |
| `0e_1m_0j_1b` | 1 | 1 | yes |
| `0e_1m_0j_2b` | 4 | 4 | yes |
| `0e_1m_0j_3b` | 6 | 6 | yes |
| `0e_1m_1j_0b` | 1 | 1 | yes |
| `0e_1m_1j_1b` | 4 | 4 | yes |
| `0e_1m_1j_2b` | 11 | 11 | yes |
| `0e_1m_1j_3b` | 14 | 14 | yes |
| `0e_1m_2j_0b` | 4 | 4 | yes |
| `0e_1m_2j_1b` | 11 | 11 | yes |
| `0e_1m_2j_2b` | 25 | 25 | yes |
| `0e_1m_2j_3b` | 29 | 29 | yes |
| `0e_1m_3j_0b` | 6 | 6 | yes |
| `0e_1m_3j_1b` | 14 | 14 | yes |
| `0e_1m_3j_2b` | 29 | 29 | yes |
| `0e_1m_3j_3b` | 33 | 33 | yes |
| `0e_1m_4j_0b` | 7 | 7 | yes |
| `0e_1m_4j_1b` | 15 | 15 | yes |
| `0e_1m_4j_2b` | 30 | 30 | yes |
| `0e_1m_4j_3b` | 34 | 34 | yes |
| `0e_2m_0j_0b` | 1 | 1 | yes |
| `0e_2m_0j_1b` | 4 | 4 | yes |
| `0e_2m_0j_2b` | 11 | 11 | yes |
| `0e_2m_1j_0b` | 4 | 4 | yes |
| `0e_2m_1j_1b` | 11 | 11 | yes |
| `0e_2m_1j_2b` | 25 | 25 | yes |
| `0e_2m_2j_0b` | 11 | 11 | yes |
| `0e_2m_2j_1b` | 25 | 25 | yes |
| `0e_2m_2j_2b` | 50 | 50 | yes |
| `0e_2m_3j_0b` | 14 | 14 | yes |
| `0e_2m_3j_1b` | 29 | 29 | yes |
| `0e_2m_3j_2b` | 55 | 55 | yes |
| `0e_2m_4j_0b` | 15 | 15 | yes |
| `0e_2m_4j_1b` | 30 | 30 | yes |
| `0e_2m_4j_2b` | 56 | 56 | yes |
| `0e_3m_0j_0b` | 2 | 2 | yes |
| `0e_3m_0j_1b` | 6 | 6 | yes |
| `0e_3m_1j_0b` | 6 | 6 | yes |
| `0e_3m_1j_1b` | 14 | 14 | yes |
| `0e_3m_2j_0b` | 14 | 14 | yes |
| `0e_3m_2j_1b` | 29 | 29 | yes |
| `0e_3m_3j_0b` | 17 | 17 | yes |
| `0e_3m_3j_1b` | 33 | 33 | yes |
| `0e_3m_4j_0b` | 18 | 18 | yes |
| `0e_3m_4j_1b` | 34 | 34 | yes |
| `0e_4m_0j_0b` | 3 | 3 | yes |
| `0e_4m_1j_0b` | 7 | 7 | yes |
| `0e_4m_2j_0b` | 15 | 15 | yes |
| `0e_4m_3j_0b` | 18 | 18 | yes |
| `0e_4m_4j_0b` | 19 | 19 | yes |
| `1e_0m_0j_1b` | 1 | 1 | yes |
| `1e_0m_0j_2b` | 4 | 4 | yes |
| `1e_0m_0j_3b` | 6 | 6 | yes |
| `1e_0m_1j_0b` | 1 | 1 | yes |
| `1e_0m_1j_1b` | 4 | 4 | yes |
| `1e_0m_1j_2b` | 11 | 11 | yes |
| `1e_0m_1j_3b` | 14 | 14 | yes |
| `1e_0m_2j_0b` | 4 | 4 | yes |
| `1e_0m_2j_1b` | 11 | 11 | yes |
| `1e_0m_2j_2b` | 25 | 25 | yes |
| `1e_0m_2j_3b` | 29 | 29 | yes |
| `1e_0m_3j_0b` | 6 | 6 | yes |
| `1e_0m_3j_1b` | 14 | 14 | yes |
| `1e_0m_3j_2b` | 29 | 29 | yes |
| `1e_0m_3j_3b` | 33 | 33 | yes |
| `1e_0m_4j_0b` | 7 | 7 | yes |
| `1e_0m_4j_1b` | 15 | 15 | yes |
| `1e_0m_4j_2b` | 30 | 30 | yes |
| `1e_0m_4j_3b` | 34 | 34 | yes |
| `1e_1m_0j_0b` | 1 | 1 | yes |
| `1e_1m_0j_1b` | 4 | 4 | yes |
| `1e_1m_0j_2b` | 11 | 11 | yes |
| `1e_1m_1j_0b` | 4 | 4 | yes |
| `1e_1m_1j_1b` | 11 | 11 | yes |
| `1e_1m_1j_2b` | 25 | 25 | yes |
| `1e_1m_2j_0b` | 11 | 11 | yes |
| `1e_1m_2j_1b` | 25 | 25 | yes |
| `1e_1m_2j_2b` | 50 | 50 | yes |
| `1e_1m_3j_0b` | 14 | 14 | yes |
| `1e_1m_3j_1b` | 29 | 29 | yes |
| `1e_1m_3j_2b` | 55 | 55 | yes |
| `1e_1m_4j_0b` | 15 | 15 | yes |
| `1e_1m_4j_1b` | 30 | 30 | yes |
| `1e_1m_4j_2b` | 56 | 56 | yes |
| `1e_2m_0j_0b` | 4 | 4 | yes |
| `1e_2m_0j_1b` | 11 | 11 | yes |
| `1e_2m_1j_0b` | 11 | 11 | yes |
| `1e_2m_1j_1b` | 25 | 25 | yes |
| `1e_2m_2j_0b` | 25 | 25 | yes |
| `1e_2m_2j_1b` | 50 | 50 | yes |
| `1e_2m_3j_0b` | 29 | 29 | yes |
| `1e_2m_3j_1b` | 55 | 55 | yes |
| `1e_2m_4j_0b` | 30 | 30 | yes |
| `1e_2m_4j_1b` | 56 | 56 | yes |
| `1e_3m_0j_0b` | 6 | 6 | yes |
| `1e_3m_1j_0b` | 14 | 14 | yes |
| `1e_3m_2j_0b` | 29 | 29 | yes |
| `1e_3m_3j_0b` | 33 | 33 | yes |
| `1e_3m_4j_0b` | 34 | 34 | yes |
| `2e_0m_0j_0b` | 1 | 1 | yes |
| `2e_0m_0j_1b` | 4 | 4 | yes |
| `2e_0m_0j_2b` | 11 | 11 | yes |
| `2e_0m_1j_0b` | 4 | 4 | yes |
| `2e_0m_1j_1b` | 11 | 11 | yes |
| `2e_0m_1j_2b` | 25 | 25 | yes |
| `2e_0m_2j_0b` | 11 | 11 | yes |
| `2e_0m_2j_1b` | 25 | 25 | yes |
| `2e_0m_2j_2b` | 50 | 50 | yes |
| `2e_0m_3j_0b` | 14 | 14 | yes |
| `2e_0m_3j_1b` | 29 | 29 | yes |
| `2e_0m_3j_2b` | 55 | 55 | yes |
| `2e_0m_4j_0b` | 15 | 15 | yes |
| `2e_0m_4j_1b` | 30 | 30 | yes |
| `2e_0m_4j_2b` | 56 | 56 | yes |
| `2e_1m_0j_0b` | 4 | 4 | yes |
| `2e_1m_0j_1b` | 11 | 11 | yes |
| `2e_1m_1j_0b` | 11 | 11 | yes |
| `2e_1m_1j_1b` | 25 | 25 | yes |
| `2e_1m_2j_0b` | 25 | 25 | yes |
| `2e_1m_2j_1b` | 50 | 50 | yes |
| `2e_1m_3j_0b` | 29 | 29 | yes |
| `2e_1m_3j_1b` | 55 | 55 | yes |
| `2e_1m_4j_0b` | 30 | 30 | yes |
| `2e_1m_4j_1b` | 56 | 56 | yes |
| `2e_2m_0j_0b` | 11 | 11 | yes |
| `2e_2m_1j_0b` | 25 | 25 | yes |
| `2e_2m_2j_0b` | 50 | 50 | yes |
| `2e_2m_3j_0b` | 55 | 55 | yes |
| `2e_2m_4j_0b` | 56 | 56 | yes |
| `3e_0m_0j_0b` | 2 | 2 | yes |
| `3e_0m_0j_1b` | 6 | 6 | yes |
| `3e_0m_1j_0b` | 6 | 6 | yes |
| `3e_0m_1j_1b` | 14 | 14 | yes |
| `3e_0m_2j_0b` | 14 | 14 | yes |
| `3e_0m_2j_1b` | 29 | 29 | yes |
| `3e_0m_3j_0b` | 17 | 17 | yes |
| `3e_0m_3j_1b` | 33 | 33 | yes |
| `3e_0m_4j_0b` | 18 | 18 | yes |
| `3e_0m_4j_1b` | 34 | 34 | yes |
| `3e_1m_0j_0b` | 6 | 6 | yes |
| `3e_1m_1j_0b` | 14 | 14 | yes |
| `3e_1m_2j_0b` | 29 | 29 | yes |
| `3e_1m_3j_0b` | 33 | 33 | yes |
| `3e_1m_4j_0b` | 34 | 34 | yes |
| `4e_0m_0j_0b` | 3 | 3 | yes |
| `4e_0m_1j_0b` | 7 | 7 | yes |
| `4e_0m_2j_0b` | 15 | 15 | yes |
| `4e_0m_3j_0b` | 18 | 18 | yes |
| `4e_0m_4j_0b` | 19 | 19 | yes |

