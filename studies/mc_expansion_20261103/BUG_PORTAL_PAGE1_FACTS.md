# Portal "filepage/1" file list stops at 5 index files: facts

Checked 2026-11-07, for the technical lead to turn into a channel post (Maryna's request, 7 Nov). Nothing was posted,
no upstream code was changed and no Pull Request was opened. Upstream = Zhavi221/atlas-utilization `upstream/master` at
29291ae. Portal numbers come from public GETs (raw responses kept outside the repo, 35 MB). The per-record numbers are
in `evidence/bug_portal_page1_facts.json`.

## Where we found it (CMS side, VERIFIED BY RUNNING 3 Nov; `HANDOFF.md` "P1", `evidence/file_index_coverage.json`)

Our CMS copy of the same reader (`studies/m0m1j0_cms/design_checks/common.py`, `fetch_file_list`) missed files in 8 of
the 54 new CMS MC records. For example, 64659 t-channel antitop got 27 of 35 files, 68591 VBF H → ττ 5 of 7, and
37446 ggF H → ττ 35 of 40. The fix on the CMS side (P1 option B, 3 Nov) reads the record API's `_file_indices` for MC
only (`fetch_file_list_complete`). The data path and upstream were left unchanged. All 10 CMS data records used on 25 Oct
fit on page 1 (`DATA_COVERAGE.md`).

## Summary

1. The upstream constant `CMS_RECID_FILEPAGE_URL` points at `https://opendata.cern.ch/record/{id}/filepage/1?group=1` (services/consts.py:1). That URL returns at most 5 index files. Its JSON also carries an `index_files.total` field with the true count. (VERIFIED BY READING + VERIFIED BY RUNNING)
2. `MetadataFetcher._fetch_files_for_record` makes one GET of that URL. It loops only over the returned `index_files.files`, never reads `total`, and never asks for a further page, so a record with more than 5 index files is cut short without any warning (services/metadata/fetcher.py:286-296). (VERIFIED BY READING)
3. This function runs only on the record-ID path: `fetch()` calls `fetch_by_record_ids` when `specific_record_ids` is set (fetcher.py:219-221, 185-189). The upstream configs that set it are the CMS ones (config.cms_records_master.yaml:32-36 and others), with records 30529, 30562, 30530 and 30563. (VERIFIED BY READING)
4. Those four CMS records have 3, 4, 2 and 5 index files, so page 1 currently returns all of them. 30563 is exactly at the limit of 5. (VERIFIED BY RUNNING)
5. The ATLAS production path does not use this function. config.yaml:110-112 sets `release_years: ["2024r-pp"]` and `specific_record_ids: null`. Because of that, `fetch()` takes the `fetch_by_release_years` branch, which gets file URLs from `atlasopenmagic`: `atom.set_release`, then `atom.available_datasets()`, then `atom.get_urls(dataset_id)` (fetcher.py:224-225, 252-262). (VERIFIED BY READING)
6. The ATLAS path would hit the bug only if someone listed ATLAS record IDs (such as 80010) in `specific_record_ids`. Every one of the 8 ATLAS MC records that hold our 337 background DSIDs has more than 5 index files. (VERIFIED BY RUNNING)
7. In those cases page 1 would return 5 of 97 index files for 80010 (5 of 11272 ROOT files), 5 of 94 for 80012 and 5 of 55 for 80013. The shortfall is similar for the others; see the table. (VERIFIED BY RUNNING)
8. For every record checked, the record API `https://opendata.cern.ch/api/records/<id>` returns the complete list in `metadata._file_indices`. The sum of `number_files` there equals `metadata.distribution.number_files` in all 8 records. (VERIFIED BY RUNNING)
9. A second upstream reader has the same pattern: `extract_schema_from_record_id` reads the same URL (services/parsing/schemas.py:386-391). It takes only the first file, so truncation does not matter there, and no upstream code calls it (git grep finds only its definition). (VERIFIED BY READING)
10. I tried 6 URL variants to get index files 6 and up from the filepage endpoint (`filepage/2`, `filepage/20`, `&page=2`, `&size=200`, `group=2`). All of them returned the same first 5 index files. (VERIFIED BY RUNNING)

## Table: ATLAS MC records holding the 337 background DSIDs (VERIFIED BY RUNNING)

I placed each DSID in a record by matching its `physics_short` to the index-file keys in `_file_indices`. All 337 DSIDs matched exactly one record. The DSID list is `atlas_bkg_metadata.csv` on origin/plan/mc-expansion-20261026. That CSV's `record` column holds only 4 values (80010, 80012, 80014, 80017) because it carries the grouping label from the source list. The DSIDs are actually stored in the 8 records below.

| record | title | index files (API `_file_indices`) | ROOT files (API) | index files on page 1 | ROOT files on page 1 | our bkg DSIDs in record | our bkg DSIDs on page 1 | > 5 index files? |
|---|---|---|---|---|---|---|---|---|
| 80010 | MC simulation electroweak boson nominal | 97 | 11272 | 5 | 5 | 97 | 5 | YES |
| 80011 | MC simulation exotic signal | 14 | 15 | 5 | 6 | 2 | 2 | YES |
| 80012 | MC simulation Higgs nominal | 94 | 179 | 5 | 5 | 94 | 5 | YES |
| 80013 | MC simulation Higgs systematic variation | 55 | 144 | 5 | 5 | 42 | 3 | YES |
| 80014 | MC simulation QCD jet nominal | 27 | 2097 | 5 | 82 | 27 | 5 | YES |
| 80015 | MC simulation QCD jet systematic variation | 29 | 205 | 5 | 25 | 29 | 5 | YES |
| 80017 | MC simulation top nominal | 23 | 437 | 5 | 5 | 23 | 5 | YES |
| 80018 | MC simulation top systematic variation | 23 | 631 | 5 | 116 | 23 | 5 | YES |

Every record's page-1 JSON reports `index_files.total` equal to the API count in column 3. The data is there; the code just never reads it.

Upstream CMS config records (VERIFIED BY RUNNING): 30529 has 3 index files and 71 ROOT files, 30562 has 4 and 80, 30530 has 2 and 70, and 30563 has 5 and 82. Page 1 returns all of them.

Unrelated, for the record (VERIFIED BY RUNNING): for 3 DSIDs, the file count from atlasopenmagic `get_urls` in the CSV differs from the portal's `number_files`. They are 700792 (26 vs 21), 700793 (166 vs 124) and 700794 (379 vs 836). I have not looked into this further.

## Citations (upstream/master, VERIFIED BY READING)

- services/consts.py:1: `CMS_RECID_FILEPAGE_URL = "https://opendata.cern.ch/record/{0}/filepage/1?group=1"`
- services/metadata/fetcher.py:286-296: `_fetch_files_for_record` makes one `requests.get` and loops over `data["index_files"]["files"]`, with no pagination and no use of `total`.
- services/metadata/fetcher.py:169-195: `fetch_by_record_ids` calls `_fetch_files_for_record` and stores the result under `record_<id>`.
- services/metadata/fetcher.py:197-231: `fetch()` priority. Record IDs come first (219-221), then release years (224-225), then all releases (228-231).
- services/metadata/fetcher.py:233-274: `_fetch_urls_for_releases` makes the atlasopenmagic calls `atom.set_release` (252), `atom.available_datasets()` (256) and `atom.get_urls` (260).
- services/parsing/schemas.py:386-391: `extract_schema_from_record_id` reads the same URL and takes only the first file. It has no callers.
- orchestration/handlers/fetch_metadata_handler.py:57-60: the handler calls `fetcher.fetch(release_years=..., record_ids=...)` with values from the parsing config. It does this only when the metadata cache misses (the cache-hit branch comes just before it).
- pipeline/executor.py:819: `MetadataFetcher` is built; executor.py:843 registers `FetchMetadataHandler`. main.py:24 imports `PipelineExecutor`.
- domain/config.py:40-41 defines `release_years` and `specific_record_ids`; domain/config.py:384-393 parses them.
- config.yaml:110-112 (ATLAS production) sets `release_years: ["2024r-pp"]` and `specific_record_ids: null`.
- config.cms_records_master.yaml:31-36 and config.cms_singleelectronsinglemuon.yaml:31-36 set `release_years: []` with records 30529, 30562, 30530 and 30563. config.short_parse_btag.yaml:31-33 and config.short_parse_local.yaml:31-33 set record 30529.
- docker/requirements.txt:2: `atlasopenmagic==1.5.0`. The locally installed 1.10.1 gets its metadata and URLs from `https://atlasopenmagic-api.app.cern.ch` (atlasopenmagic/metadata.py:67). That is version 1.10.1, not the pinned 1.5.0.
- The same URL exists locally at studies/m0m1j0_cms/design_checks/common.py:34 on the archive/backup branches.
