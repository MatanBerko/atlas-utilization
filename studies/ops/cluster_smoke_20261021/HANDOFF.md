# Cluster health check after $HOME maintenance — 21 Oct 2026

Read-only health check of the Weizmann cluster after the 21 Oct 2026 $HOME
storage replacement. The only thing changed on the cluster is a new directory
holding one tiny test job. Unless a line says otherwise, every number below is
**VERIFIED BY RUNNING** on 2026-10-21, around 18:21–18:24 IDT.

## Plain-language summary

- The cluster works after the maintenance. Login, the job queue, our Python
  environment and the home folder all came through intact.
- Nothing was missing or changed in the home folder. All 10 backed-up files are
  there and byte-for-byte the same. Nothing needed restoring, and nothing was restored.
- A tiny test job ran on a compute node and finished cleanly (exit status 0).
- File count is 121,015, below our own ceiling of 125,000 and the 150,000 soft limit.
- One connection quirk: the usual connection name `wipp-campus` timed out, even
  with VPN on. The backup name `wipp-home` worked. Nothing else is waiting for a decision.

## 1. Connection

| | |
|---|---|
| `ssh wipp-campus` | FAILED: `ssh: connect to host wipp-an1.weizmann.ac.il port 22: Operation timed out`. Tried twice; the second try was after Matan connected to VPN |
| `ssh wipp-home` | WORKED. All the steps below used it |
| hostname | `wipp-an1` |
| whoami | `berkom` |
| date | `Wed Oct 21 06:21:39 PM IDT 2026` |

Key login works, so `~/.ssh/authorized_keys` survived the maintenance.

## 2. Batch system

- `command -v qstat qsub` (login shell) → `/opt/pbs/bin/qstat`, `/opt/pbs/bin/qsub` ✔
- `/opt/pbs/bin/qstat -u berkom` → no jobs, empty output, rc=0 ✔

## 3. Python environment (`envs/atlas-pipeline`)

| package | version |
|---|---|
| uproot | 5.6.2 |
| awkward | 2.13.0 |
| numpy | 2.4.6 |
| vector | 1.6.2 |

## 4. $HOME compared with `home_backup_20261018/` (report only, nothing restored)

sha256 was computed on both sides; file contents were never printed.

| file | in $HOME | sha256 |
|---|---|---|
| .bash_logout | present | identical |
| .bash_profile | present | identical |
| .bashrc | present | identical |
| .conda/environments.txt | present | identical |
| .emacs | present | identical |
| .ssh/authorized_keys | present | identical |
| .ssh/known_hosts | present | identical |
| .ssh/known_hosts.old | present | identical |
| untracked_backup/_check_branch_units.py | present | identical |
| .zshrc | present | identical |

Result: 10/10 present and identical.

These dotfiles are in $HOME but not in the backup: `.cache/` (dir), `.config/` (dir),
`.lesshst`, `.zcompdump`. The `.conda/` dir is in $HOME, but only its
`environments.txt` is in the backup. All of these are tool caches or history
files. The non-dot directory `atlas-utilization/` is also in $HOME and not in the backup.

## 5. Smoke job

Directory (new): `/storage/agrp/berkom/atlas-utilization/work/smoke_20261021/`
holding `logs/`, `jobhome/`, `smoke.pbs` and `smoke_v2.pbs`.

- First try (`smoke.pbs`): `qsub` refused it with `qsub: Job violates queue and/or
  server resource limits` (exit 188). Queue N has `resources_min.io = 0.1`, and the
  job had not requested `io`.
- Second try (`smoke_v2.pbs`): same job plus `#PBS -l io=1`. The repo's own
  scripts always request `io` (e.g. `submit.sh` uses `io=5`). Queue N, `-m n`,
  `walltime=00:05:00,mem=200mb`. HOME, MPLCONFIGDIR and XDG_CACHE_HOME were set to `jobhome/`.
- Job ID: **5266142.pbs**. Routed to `shortE` and ran on `wn020`. It ran
  within 1 minute of submission.
- Exit status: **0**
- `logs/smoke.out`:
  ```
  wn020
  Wed Oct 21 06:23:17 PM IDT 2026
  ok
  ```
- `logs/smoke.err`: empty. `jobhome/` was left empty, and the real $HOME listing
  was unchanged after the job.

The smoke directory was left in place, as instructed.

## 6. File count (`lfs quota -u berkom /storage`)

- Files used: **121,015**. On 20 Oct it was about 121,008 (UNVERIFIED, from the task brief).
- Soft limit 150,000, hard limit 200,000. Our own ceiling is 125,000 → ✔ under.
- Disk: 299,754,556 kB used; quota 4,294,967,296 kB, limit 5,368,709,120 kB.

## Not done (out of scope)

No upstream sync. Upstream master moved to 9af30d2 (#39, muon isolation),
which needs a literature check with Matan first. #40 (multiplicity) is still open.
No production or analysis jobs ran, nothing was merged, nothing in $HOME was
touched, and no cluster files were deleted.
