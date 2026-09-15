# Did the union-vs-intersection concat bug (d488f21) affect the 2216-candidate H->ZZ->4l result?

## Short answer: no evidence that it did, checked against every parsed chunk file that still exists.

## What the bug is (confirmed from the actual diff, not just its description)

Upstream commit `d488f21` changes `domain/events.py`'s `EventChunk.from_batches()`.
The old code:
```python
combined_events = ak.concatenate([batch.events for batch in batches])
```
concatenates event records from several batches directly. If those batches carry
different top-level fields (particle collections), `ak.concatenate` on mismatched
record arrays keeps only the fields common to *every* batch -- so if one batch's
events lack, say, Photons entirely, Photons gets silently dropped from the whole
merged chunk, not just from that one batch's own events. Confirmed by reading the
commit's own diff and docstring; matches the task's description exactly.

## What "the existing full-scale run" actually is, and what's left of it

The 2216-candidate result is recorded in two committed report files on
`analysis/higgs-4lepton-clean`: `reports/higgs_4lepton_zz/fullscale_stats.json`
and `partA_stats.json`, both pointing at `run_dir:
"output/cms_higgs_4lepton_fullscale_20260908_150157"` with 13,579,052 total
parsed events -- this exactly matches the sum of that file's own per-record
`after_parse_time_selection` counts, confirming it's the real source of the 2216
number.

**That run's original parsed chunk files no longer exist in full, locally or on
the cluster.** Both are true:
- **Locally** (this machine): the directory
  `output/cms_higgs_4lepton_fullscale_20260908_150157/parsed_data/` exists but
  now holds only **10** `.root` chunk files, not the full set the 238-file,
  six-record run would have originally produced.
- **On the cluster** (`wipp-an1`, `/storage/agrp/berkom/atlas-utilization/output/`):
  no directory with that exact name exists at all. A related, later run --
  `cms_higgs_4lepton_cluster_fullscale_20260909_113726` (same six records, same
  selection, a full-scale cluster run for the follow-up "Part B" work) -- exists
  there, but its `parsed_data/` also holds only **12** `.root` chunk files, not
  the full set.

This is consistent with routine cleanup: large parsed ROOT chunks get consumed
by the analysis script and then pruned to save space on both the laptop and the
cluster's shared storage, while the derived report/stats stay behind. It means
a 100%-complete re-check of the exact original run is no longer possible --
**this is a real constraint, not something worked around**, and is reported
here plainly rather than glossed over.

## What was actually checked

`scripts/check_collection_drop.py` (read-only: opens each `.root` file with
`uproot`, reads branch names, writes nothing, moves nothing, deletes nothing)
was run against every parsed chunk file that still exists in both locations:

- **10 files locally** (`cms_higgs_4lepton_fullscale_20260908_150157`)
- **12 files on the cluster** (`cms_higgs_4lepton_cluster_fullscale_20260909_113726`)
- **22 files total**, spanning all six records used by this analysis
  (30521, 30522, 30528, 30554, 30555, 30561)

For every single one of those 22 files: all five expected particle collections
(Electrons, Muons, Jets, Photons, Taus) are present as branches. For every
record with more than one surviving chunk, every chunk of that record agrees
with every other chunk of that record on which collections are present --
there is no inconsistency, which is exactly the signature the bug would leave
if it had actually fired.

## Verdict

**No evidence that the bug affected this analysis, in any of the 22 chunk
files still available to check.** Per the task's own instructions, since step
5 (this check) did not show the drop condition occurring, the smoke-test
rerun comparison (step 6) is skipped -- this is a complete and valid stopping
point, not a shortcut.

**Caveat, stated plainly:** 22 surviving chunk files is not the same as the
original ~238 that made up the actual 2216-candidate run. This result says
"no evidence in what's left to check," not "proven impossible for the whole
run." If Matan wants a higher-confidence answer than this, the only way to
get one is an actual full-scale rerun on the fixed branch and a direct number
comparison -- which is explicitly out of scope for this task and is flagged
in the final summary as a decision for him, not undertaken here.
