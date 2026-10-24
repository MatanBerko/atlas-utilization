# HANDOFF — cluster archive, 24 Oct 2026

**Current step: COMPLETE (24 Oct 2026, 10:06 IDT). Phase 3 done: the 25 originals Matan named were deleted after
re-verification; the archives remain in `archive/20261024/`. File count 124,013 → 72,328. Nothing running.**

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

## Phase 2 (VERIFIED BY RUNNING)

- Matan's go-ahead (24 Oct): all 25 folders of A and B (`scripts/archive_dirs.txt`).
- Tools: `scripts/archive_tool.py`, `scripts/pbs_archive.sh`, pushed at `ab7ab53` before the job. The cluster copies in
  `work/cluster_archive_20261024/` were checked by sha256 against the pushed files.
- Before: 123,882 files; 293 GiB of space used of 4 TiB.
- Job `5311954[]` (0–24, 4gb, 12h, io=25): 25/25 exit 0.
- `archive/20261024/`: 25 `.tar.gz` + 25 `.manifest.tsv`. For every folder:
  - gzip test ok;
  - member list == manifest (same count, same paths and types; the count equals the Phase 1 inventory);
  - every file's sha256 recomputed from the archive == manifest.
  - In total, 51,688 entries were archived (14.27 GB → 11.57 GB). Table: INVENTORY.md, "Phase 2".
- After: 124,011 files, 330,985,564 KB.
- If all 25 originals are deleted: about 72,323 files (UNVERIFIED).

## Phase 3 method (only after "delete originals: ...", only those folders)

- Per folder, just before deleting:
  1. re-run `gzip -t`;
  2. re-count the archive members (`tar -tzf`) and check that the count equals the manifest's;
  3. check that the Phase 2 verify file says verified.
- Delete with `rm -rf -- "$ROOT/<rel>"` on that exact path only (no wildcard), never anything else.
- Then `lfs quota`; update this file; gate, commit, push; back to master.

## Phase 3 (VERIFIED BY RUNNING)

- Matan's message (24 Oct): "delete originals:" followed by the same 25 folders. `scripts/delete_dirs.txt` is identical
  to `archive_dirs.txt`.
- Tool: `scripts/pbs_delete.sh`, pushed at `4e94a64` before the job; the cluster copy was checked by sha256.
  A scratch test on the Mac deleted only the named test folder and refused a `..` path.
- Job `5321379` (io=25): exit 0, 15 minutes. For each folder, in list order, just before deleting:
  1. the Phase 2 result said verified;
  2. `gzip -t` ok;
  3. archive members == manifest entries == entries on disk.

  Then `rm -rf` on that exact path. `evidence/delete_log.tsv`: 25/25 rows `yes`, all three counts equal,
  51,688 entries removed.
- Afterwards: none of the 25 paths exists. Still present: `envs/`, `home_backup_20261018/`, the ACL folders
  (`output/cms_datasets/deliver`, `work/acltest_20261008`), the 7 Oct production, the 17 Oct MC full run, the
  four recent proofs and `checkouts/`. `archive/20261024/` holds 50 files (25 archives + 25 manifests).

| | files (quota) | space (KB) |
|---|---:|---:|
| before Phase 1 | 123,867 | 307,537,552 |
| before Phase 3 | 124,013 | 330,985,564 |
| **after Phase 3** | **72,328** | 307,971,412 |

- Restoring a folder: `tar -C /storage/agrp/berkom/atlas-utilization -xzf archive/20261024/<name>.tar.gz`. It recreates
  `<rel>/` with the original paths and times; `<name>.manifest.tsv` lists every file's sha256.

## How to resume

1. `git fetch origin`; read this file's "Current step".
2. `/opt/pbs/bin/qstat -u berkom -t`. Never resubmit a job that is queued, running or finished.
