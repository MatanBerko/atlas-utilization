# Cluster file-count cleanup — berkom

**Branch:** `ops/cluster-cleanup-20261011`, from `origin/master` (`db1bd32`)
**Date:** 2026-10-11
**Phase:** 1 (complete) and **2 (complete — A1 + A2 executed)**.

Access note: the first attempt at this session failed because the laptop had
no route to the cluster. Matan connected the secure Wi-Fi; `wipp-campus` then
worked directly (`wipp-home`'s jump host `wipp-jump.weizmann.ac.il` still does
not resolve and appears to have been retired — `wipp-campus` is the route to
use from now on).

---

## 1a. Quota — VERIFIED BY RUNNING

`lfs quota -u berkom /storage` on `wipp-an1`, Lustre mount
`192.114.102.151@tcp:192.114.102.152@tcp:/wipp/storage` → `/storage`.

| | used | soft quota | hard limit | grace left |
|---|---:|---:|---:|---|
| **space** | **120.8 G** | 4 T | 5 T | — (not over) |
| **files (inodes)** | **152,680** | **150,000** | **200,000** | **6 d 9 h 27 m** |

Space is not a problem and is not addressed here. The file count is over the
soft quota by 2,680 and the grace period expires in a little over six days;
when it does, Lustre refuses new files as if the hard limit had been reached.

**Target: below 135,000 → at least 17,681 inodes must be freed.**

`qstat -u berkom`: **no jobs running or queued** (VERIFIED), so nothing in
flight depends on any of this.

---

## 1b. Where the inodes are — VERIFIED BY RUNNING

One `lfs find` metadata pass over `/storage/agrp/berkom` (files, directories
and symlinks counted separately, then summed — Lustre charges an inode for
each). `/storage/agrp/marybo/` was never touched.

| area | inodes | share |
|---|---:|---:|
| `work/` | 52,600 | 34.5% |
| `checkouts/` | 44,547 | 29.2% |
| `output/` | 25,026 | 16.4% |
| `envs/` | 23,401 | 15.3% |
| `logs/` | 7,104 | 4.7% |
| the two top-level directories | 2 | — |
| **total** | **152,680** | **100.0%** |

**This is 100% of the quota's own figure — nothing is unexplained.**
(128,461 files + 23,040 directories + 1,179 symlinks = 152,680.)

### The single dominant cause: 50 copies of this repository

| | clones | inodes |
|---|---:|---:|
| `checkouts/<commit>/repo` — standalone pinned checkouts | 25 | 44,547 |
| `work/<task>/repo` — a clone embedded in each work directory | 25 | 35,024 |
| **total git clones** | **50** | **79,571 (52.1% of the quota)** |

Each clone is ~1,700–1,850 inodes and ~310 MB. They are byte-for-byte
reproducible: the commit is in the folder name and in every job's
`job_metadata.json`, and the repository itself lives on GitHub. Nothing
unique is stored in any of them.

---

## 1c / 1d. Proposal table

Recommendations are one of **KEEP**, **PROTECTED** (rule 3), **ARCHIVE**
(pack into one `.tar` beside the folder, verify the entry count and size,
then remove the original — data kept, inode cost drops to 1), **DELETE**.

Every inode number below is **VERIFIED BY RUNNING**.

### Proposed for action

| ID | path (under `/storage/agrp/berkom/atlas-utilization/`) | inodes | size | what it is | still needed? | rec. | freed |
|---|---|---:|---:|---|---|---|---:|
| **A1** | `checkouts/` — the **12** clones no committed document mentions: `be5a4a1 80774cf 8670f8f 58f3ca1 8c35b2e 2354a66 6e0b027 498cf15 6c0e963 c1b4a8f a64d928 21fd3b7` | 21,687 | ~3.6 G | pinned copies of this repo at 12 commits, left over from past jobs | No. Not referenced anywhere in `master` or `feature/cms-mc-weights-v3`; re-creatable by `git clone` + `git checkout <hash>` | **ARCHIVE** (12 tars) | **21,675** |
| **A2** | `checkouts/` — the **13** clones that committed documents do mention: `analysis_944afe5 06778c9 ac6f343 5d0d71d 26a7982 3930b43 7895359 6e78433 analysis_upnames 4bbe972 4640c47 06922a9 2666684` | 22,859 | ~3.9 G | the pinned checkouts past productions ran from (e.g. `06778c9` = the delivered four-dataset production) | The *commit* matters and is recorded in the handoffs; the working copy does not. Archiving keeps every byte | **ARCHIVE** (13 tars) | **22,846** |
| **A3** | `logs/` (whole tree, ~30 subfolders) | 7,104 | 54 M | PBS stdout/stderr of finished jobs; every production's outcome is already summarised in a pushed handoff | No live dependency | **ARCHIVE** (1 tar) | **7,103** |
| **A4** | `work/cms_mc_v2/` | 3,708 | — | the MC production cancelled on 2026-09-30; its own `PAUSED.md` records the contents | Superseded by the v3 design → implementation → pilot chain. Referenced in the v3 handoffs only as "read-only, untouched", never as an input | **ARCHIVE** (1 tar) | **3,707** |
| **A5** | `work/cms_mc_phase1/` | 3,012 | — | the earlier phase-1 MC study | Superseded by the same chain; its conclusions are carried in `DESIGN.md` Part B | **ARCHIVE** (1 tar) | **3,011** |
| **A6** | `work/<task>/repo/` for the **20** work dirs that are not protected and not A4/A5 | 26,108 | ~6.2 G | the repo clone embedded in each past work directory | No — same reasoning as A1/A2. The work dirs themselves are untouched; only their `repo/` subfolder is archived | **ARCHIVE** (20 tars) | **26,088** |
| **S1** | `work/cms_mc_v3_pilot_20261011/scratch_default/` | 298 | 5.0 G | the MC builder's scratch copies of shards that also live in `.../runs/` | No. Pure copies; the builder recreates them (~31 min) | **DELETE** | **298** |
| **S2** | `work/cms_mc_v3_pilot_20261011/scratch_unpruned/` | 298 | 7.2 G | the same, for the unpruned build that fed the data/MC plots | No. The plots and their JSON are committed; regenerable (~49 min) if Part 4 is ever re-run | **DELETE** | **298** |
| **S3** | `work/cms_mc_v3_impl_20261011/{prune_scratch, mc_delivery_scratch, mc_delivery_diag_scratch}` | 41 | 51 M | scratch copies from the implementation round | No | **DELETE** | **41** |
| | **total if everything above is approved** | | | | | | **85,067** |

`scratch_unweighted/` was already removed by the builder itself (0 inodes) —
nothing to do.

### PROTECTED — not proposed, under rule 3

| ID | path | inodes | why protected |
|---|---|---:|---|
| P1 | `envs/atlas-pipeline/` | 23,400 | the conda environment every job runs from |
| P2 | `output/cms_datasets/runs_matched4_full_20261007/` | 4,694 | the delivered four-dataset data production |
| P3 | `output/cms_datasets/deliver/` | 264 | contains the delivered four-dataset ROOT file — **and carries an ACL granting `marybo` access (VERIFIED)** |
| P4 | `work/cms_mc_v3_pilot_20261011/` minus S1+S2 | 3,238 | the MC pilot; rule 3 allows only its scratch copies to be proposed |
| P5 | `work/cms_mc_v3_impl_20261011/` minus S3 | 2,230 | named as an input by `HANDOFF_IMPLEMENTATION.md` |
| P6 | `work/cms_mc_v3_design_20261010/` | 1,862 | named as an input by `HANDOFF.md` |
| P7 | `work/acltest_20261008/` | 3 | **carries a `marybo` ACL (VERIFIED)** |

An ACL sweep over every directory to depth 4 found **exactly two** paths
granting `marybo` access — P3 and P7. No checkout, no log folder and no other
work directory is shared with her, so nothing in A1–A6 or S1–S3 touches
anything of Maryna's. No ACL was read-modified or changed; `getfacl` only
reads.

### KEEP — not proposed, not protected either

| ID | path | inodes | why keep |
|---|---|---:|---|
| K1 | the rest of `output/` (all other study outputs: `hgg_*`, `m0m1j0_*`, `cms_coverage_*`, the other `runs_matched*`, …) | 20,068 | real physics results of past tasks. Not needed for the target, and I cannot confirm with confidence that none is still wanted — rule 3's "anything you cannot identify with confidence" |
| K2 | the rest of `work/` (each work dir minus its `repo/`) | 11,802 | the actual per-task outputs; only their repo clones are proposed |

---

## 1e. Projected file count

| scenario | freed | inodes after | under 135,000? |
|---|---:|---:|---|
| **A1 only** (the 12 clones nothing references) | 21,675 | **131,005** | **yes** |
| A1 + A2 (all 25 standalone checkouts) | 44,521 | **108,159** | yes, comfortably |
| A1 + A2 + A3 (+ logs) | 51,624 | 101,056 | yes |
| **everything proposed (A1–A6 + S1–S3)** | **85,067** | **67,613** | yes, with very large margin |
| ARCHIVE rows + scratch-DELETE rows only | 85,067 | 67,613 | same — every row above is either an ARCHIVE or a scratch DELETE; there are no other DELETE rows |

**The target is reachable several times over without touching anything
PROTECTED.** The smallest approvable set that clears it is **A1 alone**
(131,005, a 3,000-inode margin). **A1 + A2** is the recommendation: 108,159
leaves a 42,000-inode margin, costs nothing but archive time, and preserves
every byte.

Space freed is a side effect, not the goal: A1+A2 ≈ 7.5 G, the scratch rows
≈ 12.2 G.

---

## Method and safety notes

* Measurement used one `lfs find` pass (not `du`) over
  `/storage/agrp/berkom`; `du -sh` was used only on a handful of top-level
  folders for the size column. Everything ran under `nice`. Total interactive
  time well under the one-hour budget.
* `/storage/agrp/marybo/` was never listed or accessed.
* No ACL or permission was changed. `getfacl` is read-only.
* No job was started; `qstat -u berkom` was empty throughout.
* Phase 2 will, for each approved item: re-check it is not PROTECTED,
  re-check `qstat -u berkom`, `tar -cf` with `nice`, verify with `tar -tf`
  that the entry count and size match, and only then remove the original.

---

---

# PHASE 2 — executed, A1 + A2 only

**Approved: `APPROVE: A1, A2`.** Only those two items were acted on. A3, A4,
A5, A6, S1, S2 and S3 were **not** touched and remain available.

## Pre-checks before acting (all VERIFIED BY RUNNING)

| check | result |
|---|---|
| `qstat -u berkom` | **no jobs running or queued** |
| quota unchanged since Phase 1 | 152,680 inodes — identical |
| `getfacl` on all 25 checkouts | **0 carry a `marybo` ACL** |
| all 25 checkout folders still present | yes, 44,546 inodes (+1 parent = 44,547, matching Phase 1) |
| stray non-directories already in `checkouts/` | none |

## Method

One checkout (`2666684`, the smallest) was archived first as a trial and its
numbers checked by hand before anything was removed: 1,676 inodes → 1,676 tar
entries, size ratio 1.002. Only then was its original removed and the
remaining 24 processed by `work/cluster_cleanup_20261011/archive_checkouts.sh`.

For every folder the script re-checked the `marybo` ACL, counted inodes, ran
`nice -n 10 tar -cf checkouts/<name>.tar -C checkouts <name>`, verified that
`tar -tf` listed **exactly** the same number of entries and that the
archive/folder size ratio lay in 0.95–1.10, and **only then** removed the
original. Any failure would have left the original untouched and deleted the
partial tar. No compression was used, so verification is fast and the bytes
are stored as-is.

## Result — all 25 archived, 0 failures, 0 skips

| | |
|---|---:|
| checkouts archived | **25 of 25** |
| entry-count mismatches | **0** |
| implausible size ratios | **0** (range 1.0023 – 1.0030, i.e. tar's 512-byte header per entry) |
| failures | **0** |
| skipped | **0** |
| **inodes freed** | **44,521** |

`checkouts/` now holds **25 `.tar` files and no directories** — 26 inodes in
total, down from 44,547, and 5.4 G (was 7.5 G; plain tar drops the
filesystem's per-file block padding). Spot-check: `06778c9.tar` lists cleanly
and contains `06778c9/repo/...` with its full 1,799 entries.

Per-item detail is in `ops/phase2_archive_log.txt`, one line per checkout.

## Quota — before and after (VERIFIED BY RUNNING)

| | before | after | change |
|---|---:|---:|---|
| **files (inodes)** | **152,680** | **108,163** | **−44,517** |
| soft quota | 150,000 | 150,000 | — |
| hard limit | 200,000 | 200,000 | — |
| **grace countdown** | **6 d 9 h remaining** | **cleared — none in force** | resolved |
| space | 139.8 G | 137.6 G | −2.2 G |

**The account is back under its soft quota with a 41,837-inode margin — 28%
below the limit, and comfortably past the 135,000 target.** The grace
countdown has stopped because the account is no longer in breach.

The 4-inode difference from the projected 108,159 is the small working
directory `work/cluster_cleanup_20261011/` holding the archive script, its
log and its stdout — kept deliberately as the audit trail.

## Nothing protected was touched (VERIFIED BY RUNNING, after the fact)

| protected item | state |
|---|---|
| `envs/atlas-pipeline/` | PRESENT |
| `output/cms_datasets/runs_matched4_full_20261007/` | PRESENT |
| `output/cms_datasets/deliver/` | PRESENT |
| `work/cms_mc_v3_pilot_20261011/` | PRESENT |
| `work/cms_mc_v3_impl_20261011/` | PRESENT |
| `work/cms_mc_v3_design_20261010/` | PRESENT |
| `work/acltest_20261008/` | PRESENT |
| the `marybo` ACL on the delivered four-dataset folder | intact (`user:marybo:--x`) |

No ACL or permission was changed anywhere. `/storage/agrp/marybo/` was never
accessed. No job was started.

## How to get a checkout back, if one is ever wanted

```
cd /storage/agrp/berkom/atlas-utilization/checkouts
tar -xf <commit>.tar          # restores <commit>/repo exactly as it was
```

or simply re-clone, since the folder name *is* the commit:

```
git clone https://github.com/MatanBerko/atlas-utilization.git repo
cd repo && git checkout <commit>
```

## One observation worth a glance (not acted on)

Between the Phase 1 census and the Phase 2 pre-check, about 40 minutes apart
with **no jobs running**, reported space use rose from 120.8 G to 139.8 G
(+19 G) while the inode count stayed at exactly 152,680. No new files
appeared, so this is most likely Lustre's quota accounting catching up on the
MC pilot's writes from 10 October rather than anything new being created.
**I could not confirm the cause and am not labelling it explained.** Space is
not a constraint (137.6 G of a 4 T quota), so it needs no action — but if the
figure keeps climbing with no jobs running, it is worth a look.

---

## Action log

| When | Action | Result |
|---|---|---|
| 2026-10-11 | Attempted `wipp-campus` / `wipp-home` before VPN | No route; Phase 1 blocked (first commit on this branch) |
| 2026-10-11 | Secure Wi-Fi connected; `wipp-campus` reconnected | Access restored |
| 2026-10-11 | `lfs quota`, `lfs find` inode census, `getfacl` ACL sweep, size sampling | Phase 1 measurements. Nothing written, moved or deleted |
| 2026-10-11 | A1 + A2 approved | — |
| 2026-10-11 | Phase 2 pre-checks (jobs, quota, ACLs, folder presence) | All clear |
| 2026-10-11 | Trial-archived `2666684`, verified by hand, removed original | 1,675 inodes freed |
| 2026-10-11 | Archived the remaining 24 with per-item verification | 42,846 inodes freed, 0 failures |
| 2026-10-11 | Re-ran `lfs quota`; verified protected items and the `marybo` ACL | **108,163 inodes, grace cleared** |

**A3, A4, A5, A6, S1, S2 and S3 were not acted on and remain available if
ever wanted. Nothing beyond the approved A1 + A2 was archived or deleted.**

