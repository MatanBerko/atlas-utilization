# HANDOFF — SingleElectron re-check + b-tag 0.2598 vs 0.25 (19 Oct 2026)

**Measurement only.** No production code or default changes, no threshold is
chosen, nothing delivered. Every number is labelled VERIFIED BY RUNNING /
UNVERIFIED in `RECHECK.md`.

**Current step: proof PASSED; 1A DONE (reproduces 7 Oct); 1B DONE; 2-data DONE; 2-MC running/queued; `5249721[]`, 2-data `5249807[]`, 2-MC `5249808[]`, 1B `5249809[]` submitted (11:37 / 11:48).**

## Branch

`study/singleelectron-btag-recheck-20261019` (origin only), from `037533b`
merged with fork master `45a7e06` (= upstream `b9f6ea3` incl. #38 + CMS
files) as `aca0de9`. Pinned commit for the jobs: see "Cluster".

## How the b-tag override works (study only)

`recheck/btag_override_run.py` imports `studies.m0m1j0_cms.selection`, sets
`selection.BTAG_DEEPFLAVB_MEDIUM_WP` inside the job process, then runs the
target's `main()` in the same process. The constant is read at call time by
`select_and_split_jets` (the only b-tag cut; no other module copies it).
`selection.py` on disk is unchanged. For the driver it also observes the first
`run_combination_funnel` call (all accepted events, before the Version B rule;
passed through unchanged) to save per-event object counts.

## Plan / jobs

| part | what | mode | state |
|---|---|---|---|
| proof | normal vs wrapper@0.2598 on DoubleMuon 30522/0 and MC 35631/0, bit-identical? | `proof` | `5249720` done, exit 0: all 8 shards bit-identical (data and MC); job_metadata differs only in created_utc/elapsed_sec; `evidence/override_proof_{data,mc}.json` |
| 1A | 7 Oct `measure_singleelectron.py` unchanged, 151 SE files, 10 per subjob (0–15) | `se_a` | `5249721[]` done 11:53, exit 0, 151/151. **Reproduces 7 Oct exactly**: 151/151 per-file JSONs identical (only elapsed_sec/git_commit differ), stepD byte-identical, stepB identical except the old-reference input path. Aggregated on the login node with nice (as on 7 Oct; JSON only) into `work/.../se/agg_a/`. Evidence `evidence/part1A_*.json` |
| 1B | same via wrapper at 0.25 | `se_b` | `5249809[]` done ~12:15, 151/151, all logs show the override 0.2598 -> 0.25. Aggregated (`work/.../se/agg_b/`). FS>=100 / new FS / projected histograms unchanged at all T; b-independent columns identical. Evidence `evidence/part1B_*.json` |
| 2 data | 41 sampled files (index % 10 == 0), driver ×2 | `sample` 0–40 | `5249807[]` done ~12:17, 41/41, no errors. Copied (13 MB) and aggregated locally (`aggregate_btag.py`): every sampled file at 0.2598 reproduces production per file; 0 alignment failures |
| 2 MC | 56 sampled files, MC driver @ `294ee59` ×2 | `sample` 41–96 | `5249808[]` submitted 11:48 (8gb, 4h) |

Sample list: `recheck/evidence/sample_files.json`, mapping `recheck/mappings/sample_mapping.txt`.

## Cluster (all NEW dirs; everything else read-only)

- Checkouts: `checkouts/serecheck_20261019/study` @ `0796e98` (pinned), `checkouts/serecheck_20261019/mcdriver` @ `294ee59`
- Work: `work/serecheck_20261019/` — `logs/`, `evidence/`, `se/{a_0p2598,b_0p25}/`, `sample/`, `mappings/`
- Read-only inputs: SE mapping `output/cms_datasets/singleelectron_prep_20261007/mappings/singleelectron.txt`; 7 Oct outputs `.../singleelectron_prep_20261007/{tnp,results}`; data production `output/cms_datasets/runs_matched4_full_20261007/`; MC full run `work/fullrun_20261017/` (mappings, runs, build report)

## Freeze

Admins replace $HOME Wed 21 Oct 17:30. No job whose walltime could end after
Wed 15:00; at Wed 12:30 qdel only OUR still-queued subjobs; by Wed 15:00
`qstat -u berkom` empty and no more connections. Priority if short: 1A, 2 data, 2 MC, 1B.

## How to resume

Never resubmit a queued/running/finished job; every mode skips outputs that
already exist. Submit from the study checkout:

```
W=/storage/agrp/berkom/atlas-utilization/work/serecheck_20261019
C=/storage/agrp/berkom/atlas-utilization/checkouts/serecheck_20261019
S=$C/study/studies/cms_datasets/singleelectron_prep/recheck/cluster/pbs_recheck.sh
V=WORK_DIR=$W,STUDY_REPO=$C/study,MC_REPO=$C/mcdriver
/opt/pbs/bin/qsub -N serc_<mode> -J <range> -l select=1:ncpus=1:mem=8gb,walltime=..,io=25 -j oe \
  -o $W/logs/<mode>/ -v MODE=<mode>,$V,SE_MAPPING=...,SAMPLE_MAPPING=$W/mappings/sample_mapping.txt $S
```

## File count

Start: 119,243 (19 Oct 11:31); 119,770 after checkouts + dirs (+527). Budget ≤ 2,500 new, total ≤ 125,000.
