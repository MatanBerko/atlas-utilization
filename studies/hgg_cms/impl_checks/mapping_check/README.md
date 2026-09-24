# Data array job: index -> file mapping (full-run prep, Part 1)

## The question

`pbs_hgg_data_array.sh` runs `main.py --batch-job-index i --total-batch-jobs 133`
once per array index (1..133), covering DoubleEG records 30521 (47 files)
+ 30554 (86 files). Each of the 133 jobs fetches BOTH records' file lists
independently from the CERN Open Data portal API (no shared cache between
jobs -- each gets its own `--run-dir`). Does every index always get
exactly one file, with no file processed twice and none skipped, and is
that mapping STABLE across all 133 independent fetches?

## How the mapping is built (file:line)

- `services/metadata/fetcher.py:324-346` (`_fetch_files_for_record`):
  fetches one record's file list from the CERN Open Data filepage API and
  returns it **in the order the API JSON lists them -- no sorting
  anywhere.**
- `services/metadata/fetcher.py:231-243` (`fetch_by_record_ids`): builds
  `{"record_30521": [...], "record_30554": [...]}` by iterating
  `specific_record_ids` (a fixed, static list from the YAML config,
  `[30521, 30554]`) in order -- so the two records' RELATIVE order is
  always the same.
- `orchestration/handlers/parsing_handler.py:203-229`: copies
  `context.metadata`, calls `select_metadata_for_parsing` (which, for
  `record_*` keys, is an identity filter that preserves dict order --
  `orchestration/handlers/parsing_handler.py:87-91`), then
  `utils/batching.py:53-94` (`get_batch_slice_by_year`): **flattens both
  records' file lists into one list (in dict-iteration order, i.e.
  insertion order) with ZERO sorting**, then slices it with plain
  arithmetic (`utils/batching.py:13-50`, `get_batch_slice`).

With `total_batches == total_items == 133`, `get_batch_slice`'s own
arithmetic (`items_per_batch = 133 // 133 = 1`) deterministically gives
each index exactly one item, GIVEN a fixed input ordering -- this part
was verified directly with `verify_data_job_file_mapping.py`.

## What this means

The mapping's correctness rests entirely on one assumption this project
does not control: **that the CERN Open Data portal returns the exact same
file order every time its filepage API is queried**, since each of the
133 jobs queries it independently, at a different wall-clock time, with
no shared cache and no sorting to normalize the result.

## Evidence gathered (this is real risk, not a false alarm -- but also not fabricated caution)

1. Two back-to-back queries (3 seconds apart) of record 30521's filepage
   returned byte-identical file order.
2. The API's own JSON structure (`index_files.files`, each entry keyed by
   a filename like `..._file_index.json`) looks like a small number of
   static, pre-generated manifest files being read back in a fixed order
   -- not a live, randomly-ordered database query -- which is
   architecturally reassuring, though not something this project can
   verify from outside CERN's own infrastructure.
3. **Strongest evidence**: a fresh fetch of record 30521 done for this
   check (see `cms_hgg_data_file_lists.json`) put file
   `11DA657F-5262-BD4A-AD1E-8E53BE62A601.root` at index 1 -- the exact
   same file the real pilot's data job 1 (array index 1) processed on 16
   Sep 2026 (confirmed independently: that file's own `Events` tree has
   exactly 2,014,154 entries, matching the pilot's own reported event
   count for job 1 exactly). That is two independent fetches, on
   different days, agreeing on file order for the same record.

## Conclusion

No documented guarantee of this ordering was found (this project has no
access to CERN Open Data's own internal implementation or API contract).
Given points 1-3 above, the risk appears low in practice for a
submission window of hours to a few days, but it is **not eliminated**,
especially if some of the 133 jobs end up queued for a long time and
fetch their metadata much later than others.

**Minimal proposed fix** (NOT implemented -- shared-code change, needs
approval): freeze each record's file list into one committed JSON file at
submission time (e.g. `cms_hgg_data_file_lists.json`, generated once by
`verify_data_job_file_mapping.py`'s own fetch step) and have every array
job load its one file from that frozen list (by index) instead of calling
`fetch_by_record_ids` independently -- this would make the mapping
provably stable regardless of what the portal does between job 1's fetch
and job 133's fetch, and is a small, additive change (a frozen file list
input, not a change to the batching arithmetic itself).

## Files here

- `cms_hgg_data_file_lists.json`: one real fetch of both records' file
  lists (metadata-only reads).
- `verify_data_job_file_mapping.py`: uses the REAL `get_batch_slice_by_year`
  against that fetch to compute and verify the full index->file mapping.
- `data_job_file_mapping_results.json`: that tool's output -- confirms,
  for this one fetch, every file appears in exactly one index, no index
  is empty or has more than one file, and both records are fully covered
  (47 + 86 = 133).
