# HANDOFF — cluster archive, 24 Oct 2026

**Current step: Phase 1 DONE (inventory and plan). WAITING for Matan's reply, exactly:
"go ahead with archiving: <list of directories>". Nothing has been archived, moved or deleted.**

- Branch: `ops/cluster-archive-20261024` (origin only), from `origin/master` @ `8aa6960`.
- Result: `INVENTORY.md` (every folder, what it is, files, size, newest change, proposal).

## Phase 1 (VERIFIED BY RUNNING)

- Cluster reached over `wipp-home` (`wipp-campus` timed out once).
- Quota before: 123,867 files, 307,537,552 KB. After this phase's report files: 123,879.
- Report/log folder (new): `work/cluster_archive_20261024/`, holding `inventory.py`, `pbs_inventory.sh`,
  `pbs_inventory_cmsdatasets.sh`, `inventory.json`, `inventory_output_cms_datasets.json`, `logs/` and `jobids.txt`.
- Jobs: `5311883` (inventory, io=1, exit 0), `5311903` (one level deeper in `output/cms_datasets`, io=1, exit 0).
  Read-only metadata walks. `envs/` and `home_backup_20261018/` were counted only as totals.
- The walk found 123,871 inodes, which matches the quota.

## Plan (details in INVENTORY.md)

- **A (recommended), 5 folders, 24,748 files, 12.5 GB:** `logs`, `work/electron_prep`, `work/ttbar_count_vs_atlas`,
  `work/cms_mc_v2`, `work/cms_mc_phase1`. After removing the originals: about 99,139 files (UNVERIFIED projection).
- **B (optional), 20 superseded 24 Sep – 1 Oct work folders, 26,940 files:** with A, about 72,239.
- KEEP everything else, in particular:
  - `envs/` and `home_backup_20261018/`;
  - the 7 Oct production and the 17 Oct MC full run;
  - the recent proofs;
  - the two ACL folders shared with Maryna (`output/cms_datasets/deliver/`, `work/acltest_20261008`).

## Phase 2 method (only after the go-ahead, only the listed folders)

- Archive names: the path with "/" replaced by "_" (e.g. `work/cms_mc_v2` → `work_cms_mc_v2`), in
  `/storage/agrp/berkom/atlas-utilization/archive/20261024/`: `<name>.manifest.tsv`, `<name>.tar.gz`.
- PBS jobs, io=25:
  1. a manifest of every file (relative path, size, sha256);
  2. `tar -czf` with relative paths, keeping timestamps; an existing archive name means STOP;
  3. `gzip -t`;
  4. member list == manifest list;
  5. every member's sha256, recomputed from the archive stream, == the manifest.
- Originals are NOT removed in Phase 2.

## How to resume

1. `git fetch origin`; read this file's "Current step".
2. `/opt/pbs/bin/qstat -u berkom -t`. Never resubmit a job that is queued, running or finished.
