# Cluster file-count cleanup — berkom

**Branch:** `ops/cluster-cleanup-20261011`, from `origin/master` (`db1bd32`)
**Date:** 2026-10-11
**Phase:** 1 (measure and propose). **Read-only: nothing was deleted, moved,
archived, or written anywhere under `/storage`.**

---

## STATUS: PHASE 1 IS BLOCKED — no route to the cluster

Phase 1 cannot be completed in this session. Every measurement it asks for
(`lfs quota`, per-folder file counts, reading each folder's
`job_metadata.json` / HANDOFF) requires a shell on the cluster, and **neither
documented route is usable right now**.

This is a connectivity problem on Matan's laptop, not a problem with the
cluster account or with anything in this repository.

### What was tried, and what happened (VERIFIED BY RUNNING)

| Route | Result |
|---|---|
| `ssh wipp-campus` (direct to `wipp-an1.weizmann.ac.il`) | `banner exchange: Connection to UNKNOWN port -1: Connection timed out` — tried twice, 25 s and 45 s timeouts |
| `ssh wipp-home` (via `sshproxy@wipp-jump.weizmann.ac.il`) | `ssh: Could not resolve hostname wipp-jump.weizmann.ac.il: No such host is known` |
| `Test-NetConnection wipp-an1.weizmann.ac.il -Port 22` | `TcpTestSucceeded: False`, `PingSucceeded: False` |
| `nslookup wipp-an1.weizmann.ac.il` | resolves: `192.114.102.133` |
| `nslookup wipp-jump.weizmann.ac.il` | `can't find ...: Non-existent domain` (answered by `ns1.weizmann.ac.il`) |
| `Get-NetAdapter` (adapters in state `Up`) | **only `Wi-Fi`** — no VPN adapter is connected |
| local source address | `10.7.139.40`, next hop `10.7.128.245` — a home/office LAN, not a Weizmann address |

### What this means

The two routes fail for **two different reasons**, and both point the same way:

1. **`wipp-campus`** needs the laptop to be on the Weizmann network (campus
   Wi-Fi or VPN). The name resolves, but there is no network path to port 22.
   `Get-NetAdapter` confirms no VPN adapter is up.
2. **`wipp-home`** needs `wipp-jump.weizmann.ac.il`, and that name does not
   exist in public DNS. It is almost certainly an internal-only name that is
   published by the VPN's own DNS server — so it will resolve again once the
   VPN is connected, and it would fail even today for the same reason.

**Action needed from Matan: connect the Weizmann VPN.** That should restore
both routes at once. If `wipp-home` still fails after connecting but
`wipp-campus` works, that is fine — `wipp-campus` is the preferred route
anyway, and the jump host may simply have been retired.

Nothing else is needed from him for Phase 1; once the VPN is up, the scan
below runs unattended in well under the one-hour interactive budget.

---

## What WAS established, from the repository alone (no cluster access)

This is the part of Phase 1, item **1c** — "identify what each folder is,
which task produced it, and whether anything depends on it" — that can be
done from the fork's own history and handoffs. It is recorded here so the
next session only has to run the scans and fill in the numbers.

**Every file count and size in the real Phase 1 table is still UNKNOWN.**
Nothing below is a measurement; the protection status is a *rule* applied to
paths named in committed documents.

### Confirmed PROTECTED (rule 3) — never to be proposed for removal

| Path | Why it is protected | Source |
|---|---|---|
| `atlas-utilization/envs/` | the conda environment every job runs from | rule 3; referenced 50× across `origin/master` |
| `output/cms_datasets/runs_matched4_full_20261007/` | the delivered four-dataset data production (390 per-file jobs) | rule 3; `studies/cms_datasets/electron_vB/HANDOFF.md` |
| `output/cms_datasets/deliver/four_dataset_vB_upstreamnames_w10p0_dr012_20261007/` | the delivered four-dataset ROOT file and its build outputs | rule 3; same handoff, "WHICH FILE TO USE" |
| `work/cms_mc_v3_pilot_20261011/` **except its `scratch_*` subfolders** | the MC pilot | rule 3; `HANDOFF_PILOT.md` |
| `work/cms_mc_v3_design_20261010/` | named as an input by `HANDOFF.md` on `feature/cms-mc-weights-v3` | rule 3 |
| `work/cms_mc_v3_impl_20261011/` | named as an input by `HANDOFF_IMPLEMENTATION.md` | rule 3 |
| anything carrying an ACL entry for `marybo` | shared with Maryna | rule 3 — **must be checked with `getfacl` before anything is proposed** |

### Known candidate areas, to be measured and then classified

Named here only so the scan knows where to look. **No recommendation is made
for any of them yet** — that needs the file counts, and for several of them it
needs a `getfacl` check first.

* `work/cms_mc_v3_pilot_20261011/scratch_default/`, `scratch_unweighted/`,
  `scratch_unpruned/` — the MC builder's scratch copies. These are copies of
  shards that also exist in `work/cms_mc_v3_pilot_20261011/runs/`, which is
  exactly the exception rule 3 allows. 98 shard files each, by construction
  (one per pilot input file) — **UNVERIFIED, to be confirmed by counting.**
* `work/cms_mc_v3_impl_20261011/` — `prune_scratch/`,
  `mc_delivery_scratch/`, `mc_delivery_diag_scratch/` are scratch copies;
  `data_regression/` and `mc_smoke/` were each superseded by
  `data_regression2/` and `mc_smoke2/` in the same session
  (`HANDOFF_IMPLEMENTATION.md` says so explicitly). The *parent* directory is
  PROTECTED, so only these sub-items could be candidates, and only if that
  reading survives a second look.
* `work/cms_mc_v2/` — the MC production cancelled on 2026-09-30. Its own
  `studies/cms_mc_weights/v2/PAUSED.md` (on `feature/cms-mc-weights-v2`)
  records what it contains and that nothing was deleted. The task brief
  suggests ARCHIVE for this kind of item rather than DELETE.
* `logs/` — per-job PBS logs. Only logs of *finished* jobs whose content is
  already summarised in a pushed handoff could qualify, and each would have
  to be checked individually.
* `checkouts/` and the many `work/*/repo/` directories — each is a full git
  clone of this repository, so each costs several thousand files on its own.
  These are likely to dominate the file count. Several are named in `master`
  documents as the pinned checkout of a past production; whether a *pinned
  checkout* counts as "referenced as an input" under rule 3 is a judgement
  call that should be put to Matan rather than made here.

### The scan that will run first, next session (all read-only)

```
lfs quota -u berkom /storage                      # 1a: used / soft / hard, grace
lfs find /storage/agrp/berkom -type f | wc -l     # total files the quota counts
lfs find /storage/agrp/berkom -maxdepth 3 -type d # the folder tree to tabulate
getfacl -R <candidate> | grep -l marybo           # ACL check before proposing anything
```

with `nice`, on the analysis node. `/storage/agrp/marybo/` is never touched.

---

## Phase 1 deliverables still outstanding

| Item | State |
|---|---|
| 1a quota numbers | **blocked** — needs cluster |
| 1b file counts per folder, ≥95% of the quota accounted for | **blocked** |
| 1c identification | **partly done above** from the repo; the rest needs the folders themselves |
| 1d proposal table with IDs | **blocked** — cannot assign recommendations without counts |
| 1e projected counts vs the 135,000 target | **blocked** |

---

## Action log

Nothing has been archived or deleted. This file is the only artefact of this
session, and it is in the repository, not on the cluster.

| When | Action | Result |
|---|---|---|
| 2026-10-11 | Attempted `wipp-campus`, `wipp-home`; diagnosed DNS/TCP/VPN state | No cluster access; Phase 1 blocked |
| 2026-10-11 | Read the fork's handoffs and `master` documents to pre-build the PROTECTED list | Recorded above |
