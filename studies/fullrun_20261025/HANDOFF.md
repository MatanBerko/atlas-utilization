# HANDOFF — CMS full run with loose muon/electron IDs (25 Oct 2026 directories)

Branch `run/cms-fullrun-20261025` (origin only), made from `origin/lean/cms-layer-20261023`
@ `33d77f5` (= upstream master `29291ae` + 63 CMS files). Decision (Maryna, 24 Oct, approved
by Matan): muons CMS Loose ID (`Muon_looseId`), isolation `pfRelIso04_all < 0.15` kept;
electrons `cutBased >= 2` (Loose); jets unchanged.

Nothing is submitted for the full run. No Pull Request; nothing upstream; no message sent.

## Step 0 — preflight (24 Oct 2026) — DONE

- `upstream/master` = `29291ae` (unchanged) and `origin/lean/cms-layer-20261023` = `33d77f5`
  — VERIFIED BY RUNNING (`git rev-parse` after `git fetch`).
- File quota on /storage: **72,328** files used (soft limit 150,000; Matan's ceiling 125,000)
  — VERIFIED BY RUNNING (`quota -s` on wipp-home). Space 293.7 GB of 4 TB.
- `ssh wipp-campus`: timed out (one try). `wipp-home` is used.
- Branch `run/cms-fullrun-20261025` created from the lean branch.

## Step 1 — branch titles (in progress)

Script `cluster/branch_titles.py` + `cluster/pbs_titles.sh` (io=1). Results follow.
