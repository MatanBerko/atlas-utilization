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

## v4 decisions (15 Oct 2026)

| file | source |
|---|---|
| `v4_decisions_2026-10-15.json` | Matan's reviewed cross-section decisions, transcribed as given |

Since 15 Oct 2026, `build_registry.py` takes `cross_section_pb`, the record
list and the `in_full_run` flag from this file. The two v2 files above are
still read, unchanged, for each record's older provenance. The registry keeps
that provenance as history and marks it superseded. The readable table is
`../XSEC_DECISIONS.md`, and the live portal cross-check is
`../evidence/portal_crosscheck_20261015.json`.
