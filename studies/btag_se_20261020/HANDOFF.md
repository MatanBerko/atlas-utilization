# HANDOFF — b-tag 0.2489 + SingleElectron (Maryna, 20 Oct 2026)

**Resume rule:** read this file first. Never resubmit a job that is queued,
running or finished; every job mode skips outputs that already exist.

## Current step

- Code: DONE and pushed (both branches, gate empty).
- Local tests: DONE, all pass.
- Real-file checks A–E: being prepared for the cluster.

## Branches

| branch | head | what |
|---|---|---|
| `feature/cms-btag-singleelectron-20261020` (from master `aaf945a`) | `31f21ce` = code; later commits = this study folder only | b-tag 0.2598 → 0.2489; `--population matched5` (SingleElectron 5th, last, T = 32 GeV); data builder order guard + per-dataset counts; `test_btag_singleelectron.py` |
| `feature/cms-mc-btag-singleelectron-20261020` (from `sync/mc-upstream-35-20261020` `0e98075`) | `cd22aa2` | normal merge of the data branch; MC stores the SingleElectron acceptance as bit 6; MC builder union = 5 flags; `test_mc_singleelectron_flag.py` |

Master (`aaf945a`) and every other existing branch are unchanged. Nothing was
done on upstream, and no PR was opened.

## Cluster

- Host: wipp-campus.
- Pinned code: `checkouts/btagse_20261020/`, holding `git archive` tarballs:
  - `old_data` = `aaf945a`
  - `new_data` = `31f21ce`
  - `old_mc` = `0e98075`
  - `new_mc` = `cd22aa2`
- Work: `work/btagse_20261020/`, holding `mapping.txt`, `pbs_checks.sh`,
  `scripts/analyse.py`, `code` → the checkouts dir, `runs/{old,new,ovr}/`,
  `deliver/`, `evidence/` and `logs/`.
- Job sides:
  - **old:** the OLD code, data `matched4` / MC `--is-mc matched4`;
  - **new:** the NEW code, data `matched5` / MC `--is-mc matched4`;
  - **ovr:** the NEW code with the b-tag forced back to 0.2598 for that
    process only, so OLD vs ovr isolates the b-tag.

Jobs: (none submitted yet)

## Freeze

The cluster `$HOME` is replaced Wed 21 Oct 17:30. No job may end after
Wed 21 Oct 15:00; nothing may be queued or running by then, and no more
connections after that.
