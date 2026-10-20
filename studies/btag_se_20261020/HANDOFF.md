# HANDOFF — b-tag 0.2489 + SingleElectron (Maryna, 20 Oct 2026)

**Resume rule:** read this file first. Never resubmit a job that is queued,
running or finished; every job mode skips outputs that already exist.

## Current step

- Code: DONE and pushed (both branches, gate empty).
- Local tests: DONE, all pass.
- Real-file checks A–E: SUBMITTED 20 Oct 10:21 (see Jobs). PARTLY FAILED at
  ~10:31: the CERN Open Data portal returned 502 Bad Gateway while file
  URLs were being looked up (an outage outside our code). 16 of 22 runs
  finished. Still missing: ovr DoubleMuon/DoubleEG/MuonEG/MC 67801, plus
  old and ovr SingleMuon. Build 5253153 and analyse 5253154 never ran
  (their dependency failed). NEXT: once the portal answers 200, resubmit
  array indices 0,1,2,3,6 (finished sides are skipped automatically), then
  build and analyse.

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

Jobs (wipp-campus, submitted 20 Oct 10:21 IDT):

| job | what | resources |
|---|---|---|
| `5253152[]` (0-7) | per-file, `mapping.txt`: data DM/SM/DEG/MEG file 0 (new, old, ovr), SE 30529/0 and 30562/0 (new), MC 67801/0 and 75589/0 (new, old, ovr) | 32gb, 8h |
| `5253153` | build (afterok): data NEW 5 datasets / OLD 4; MC OLD/OLD, OLD builder on NEW runs, NEW/NEW, all `--smoke-test` | 16gb, 3h |
| `5253154` | analyse (afterok): `scripts/analyse.py` -> `evidence/` | 16gb, 1h |

Pre-check (login node, VERIFIED BY RUNNING): all six data files carry every
trigger branch matched5 needs and the "2 = 1e (WPTight)" bit title.
File count before: 120,686.

Study targets for check B (read-only `work/serecheck_20261019/se/a_0p2598/`):
30529/0 accepted 32,459, not taken by the other four 30,774; 30562/0 902,673
and 855,435.

## Freeze

The cluster `$HOME` is replaced Wed 21 Oct 17:30. No job may end after
Wed 21 Oct 15:00; nothing may be queued or running by then, and no more
connections after that.
