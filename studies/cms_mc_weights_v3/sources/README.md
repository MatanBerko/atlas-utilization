# Inputs of record for the v3 normalisation registry

Both files are copied VERBATIM out of `feature/cms-mc-weights-v2` (head
`c89d0f0`) so `build_registry.py` has stable, auditable inputs that do not
depend on another branch being fetched:

| file | source |
|---|---|
| `v2_cms_mc_normalisation.json` | `feature/cms-mc-weights-v2:studies/cms_mc_weights/cms_mc_normalisation.json` |
| `v2_normalisation_table_v2.csv` | `feature/cms-mc-weights-v2:studies/cms_mc_weights/normalisation_table_v2.csv` |

Neither is edited here. The v2 branch itself is untouched. Every number in
them is UNVERIFIED by this round: they are the previous round's research
output, carried forward with their provenance and caveats, not re-derived.
