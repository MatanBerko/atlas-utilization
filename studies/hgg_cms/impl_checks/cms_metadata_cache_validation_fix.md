# Fix: CMS metadata-cache validation rejected valid CMS URLs

## Cause

`orchestration/handlers/fetch_metadata_handler.py`'s
`_validate_cache_or_abort` (called from `handle()` at line 95, **only**
inside the `if metadata:` branch (line 86) that runs when
`self.cache.load()` (line 84) returns a cache **HIT** -- never on a cache
miss, see "Does this affect the full data/signal runs?" below) validated
every cached URL with `services/metadata/fetcher.py`'s `_classify_url`,
which matches ATLAS's RUCIO namespace convention only (`/mc\d+_`,
`/data\d+_`). It also decided "is this an MC key" purely from the key's
own name: `is_mc_key = key.endswith("_mc")` (line 163, unchanged). (Line
numbers are from this branch's current state, after this fix's own
additions earlier in the file -- the bug itself predates this fix.)

Neither assumption holds for CMS. `services/metadata/fetcher.py`'s
`fetch_by_record_ids` (used for every CMS `specific_record_ids` config)
names every key `f"record_{record_id}"` with **no `_mc` suffix at all**,
whether the record is data or simulation, and CMS Open Data URLs use an
EOS path (`/eos/opendata/cms/...`) that never matches ATLAS's RUCIO regex.
So for any CMS record key, `is_mc_key` was always `False`, and
`_classify_url` raised `ValueError` on every URL -- `_validate_cache_or_abort`
then reported it as an "unclassifiable URL" contamination and aborted the
run. This is exactly what happened to the D3 data job: it pins its one
file by pre-writing the metadata cache directly (a deliberate,
non-invasive way to guarantee the exact same file used by the earlier
physics checks is processed -- see `pbs_hgg_d3_data.sh`/
`pbs_hgg_d3_signal.sh`), so `FetchMetadataHandler` sees a cache **HIT** on
its very first read and runs the validation that no ordinary first-time
CMS run had ever exercised before.

## Does this affect the full data/signal runs? (point 1)

**Not on a clean first run of any one job, but YES on a retry/resubmission
that reuses the same run directory.**

- `handle()` (`orchestration/handlers/fetch_metadata_handler.py:75-113`):
  `metadata = self.cache.load()` (line 84); `_validate_cache_or_abort` is
  called **only** at line 95, inside `if metadata:` (line 86) -- i.e.
  only when a cache file already exists at `parsing_config.file_urls_path`.
  On a cache **miss** (line 98's `else:` branch), `self.fetcher.fetch(...)`
  is called instead, its result is used directly, and
  `_validate_cache_or_abort` is **never called** on it.
- Every data-array job (`pbs_hgg_data_array.sh`) and every signal job
  (`pbs_hgg_signal.sh`) gets its own dedicated `--run-dir`, and
  `parsing_task_config.file_urls_path` is relative in both base configs,
  so `utils/paths.py`'s `update_config_paths_with_run_dir` nests each
  job's cache file uniquely under that run dir
  (`<run-dir>/metadata_cache.json`). **The very first time a given job
  runs, that file does not exist yet -- cache miss -- so this bug is not
  triggered.**
- **If that same job is ever re-run against the same `--run-dir`**
  (the ordinary thing to do after e.g. a resource-limit kill or a
  transient failure, since re-submitting into a fresh directory would
  otherwise duplicate work already done), the metadata cache file written
  by the first attempt is now present -- cache **HIT** -- and
  `_validate_cache_or_abort` runs and would have hit this exact bug for
  every CMS record, data or signal, not just D3's pinned-cache case.
- D1/D2 (`reproduce_check_b_and_c.py`) never uses `MetadataFetcher`/
  `FetchMetadataHandler` at all (it calls `uproot.open` directly on
  pinned URLs), so it was never at risk.

**So: this was not unique to D3's file-pinning trick -- it would have
surfaced the first time any real data or signal job was resubmitted into
its own run directory.** The fix below removes the risk entirely, for a
first run or a retry alike.

## Fix

- `services/metadata/fetcher.py`: added `_classify_cms_url` (classifies a
  CMS URL by EOS path: `/eos/opendata/cms/mc/` -> simulation,
  `/eos/opendata/cms/Run\d{4}[A-Za-z]+/` -> data), used ONLY for CMS
  record keys. `_classify_url` (ATLAS) is completely untouched.
- `orchestration/handlers/fetch_metadata_handler.py`: added
  `_cms_record_id(key)` (returns the record id if `key` is
  `"record_<id>"` for an id registered as `"cms-nanoaod"` in
  `services.parsing.schemas.RECORD_ID_TO_SCHEMA`, else `None`) and
  `_cms_key_violations(key, urls)` (classifies every URL in a CMS key via
  `_classify_cms_url` and requires them all to agree on ONE type -- the
  record's type is whatever its own URLs consistently indicate, since CMS
  keys carry no naming convention to check against). `_validate_cache_or_abort`
  now branches: a CMS record key goes through the new path; every other
  key (all ATLAS release-year keys) goes through the exact, unmodified
  prior logic.

## Verification against real URLs (point 2: pattern check across all 8 H->gamma-gamma records + the 4 pre-existing CMS records used by other tasks)

All URLs below are real (fetched from CERN Open Data's own record
filepage API this session); `_classify_cms_url` result and
`_cms_key_violations` (single-URL key) shown for each.

| record | label | one real URL (truncated) | classified | violations |
|---|---|---|---|---|
| 30521 | DoubleEG Run2016G (H->gg data) | `.../Run2016G/DoubleEG/...` | DATA | none |
| 30554 | DoubleEG Run2016H (H->gg data) | `.../Run2016H/DoubleEG/...` | DATA | none |
| 37350 | ggH (H->gg signal) | `.../mc/.../GluGluHToGG.../...` | MC | none |
| 68497 | VBF (H->gg signal) | `.../mc/.../VBFHToGG.../...` | MC | none |
| 71013 | W+H (H->gg signal) | `.../mc/.../WplusH_HToGG.../...` | MC | none |
| 70173 | W-H (H->gg signal) | `.../mc/.../WminusH_HToGG.../...` | MC | none |
| 74132 | ZH (H->gg signal) | `.../mc/.../ZH_HToGG.../...` | MC | none |
| 67611 | ttH (H->gg signal) | `.../mc/.../ttHJetToGG.../...` | MC | none |
| 30529 | SingleElectron Run2016G (other task, pre-existing) | `.../Run2016G/SingleElectron/...` | DATA | none |
| 30530 | SingleMuon Run2016G (other task, pre-existing) | `.../Run2016G/SingleMuon/...` | DATA | none |
| 30522 | DoubleMuon Run2016G (other task, pre-existing) | `.../Run2016G/DoubleMuon/...` | DATA | none |
| 30555 | DoubleMuon Run2016H (other task, pre-existing) | `.../Run2016H/DoubleMuon/...` | DATA | none |

The 4 pre-existing (non-H->gamma-gamma) CMS records used by earlier tasks
classify correctly too -- this fix is not H->gamma-gamma-specific, and
does not change behavior for those other tasks' configs (they were never
exercised through a cache-hit path with this bug either, by the same "hit
only on cache reload" reasoning above, but would have hit the identical
bug on a retry).

## Point 4: the D3 pinned caches specifically

```
record_30521 (D3 data):   ['root://.../Run2016G/DoubleEG/.../11DA657F-....root']  -> 0 violations
record_37350 (D3 signal): ['root://.../mc/.../GluGluHToGG.../3231834B-....root']  -> 0 violations
```
Both pass the new check with zero violations (verified directly, see
`tests/test_cms_metadata_cache_validation.py`'s
`ValidateCacheOrAbortEndToEndTests.test_d3_data_pinned_cache_passes` /
`test_d3_signal_pinned_cache_passes`).

## Regression (point 3)

`_classify_url` and the `is_mc_key = key.endswith("_mc")` / ATLAS branch
of `_validate_cache_or_abort` are **byte-for-byte unchanged** (confirmed
by diff -- no lines in either were touched), so ATLAS behavior cannot have
changed. This is also covered directly by
`tests/test_cms_metadata_cache_validation.py`'s
`AtlasValidationUnchangedTests` (MC key OK, DATA key OK, a contaminated MC
key still aborts, a contaminated DATA key still aborts -- all using the
same `data23_13p6TeV`/`mc23_13p6TeV`-style URLs as the project's existing
`tests/test_parse_mc_selection.py`).

Unlike tasks 1-6's usual `dump_parsed_fields.py`/`compare_dumps.py`
regression harness, this fix lives entirely in the metadata-fetch/cache-
validation layer -- upstream of, and never called by,
`FileParser._parse_opened_file` (which is all `dump_parsed_fields.py`
exercises). Running that harness on the usual 4 CMS files + 1 ATLAS file
would trivially report "IDENTICAL" regardless of this change, since it
never executes the modified code path at all -- so it would not actually
prove anything about this fix. The genuine regression proof for this fix
is: (a) the diff itself, showing zero lines changed in the ATLAS-only
code path; (b) `tests/test_cms_metadata_cache_validation.py`'s 17 tests,
which directly exercise `_validate_cache_or_abort` (the changed function)
for both ATLAS and CMS keys, including the exact D3 pinned-cache
dictionaries and the 4 pre-existing CMS records' real URLs above; and (c)
the full test suite (180 passed, the same 7 pre-existing unrelated
failures, no new failures).
