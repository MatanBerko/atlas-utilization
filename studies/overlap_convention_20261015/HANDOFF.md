# HANDOFF — overlap-convention study (15 Oct 2026)

**Status: jobs running.** PBS array `5227772[]` (8 subjobs, one per file),
submitted from the pinned checkout at `440a7aa`.

| | |
|---|---|
| checkout | `/storage/agrp/berkom/atlas-utilization/checkouts/overlapconv_20261015/repo` (`440a7aa`) |
| work dir | `/storage/agrp/berkom/atlas-utilization/work/overlapconv_20261015/` (`out/`, `logs/`, `smoke/`) |
| route | `wipp-home` (`wipp-campus` timed out all day) |
| file count before | 109,592 (`lfs quota -u berkom /storage`) |

Submit command (from the checkout):

```bash
/opt/pbs/bin/qsub -J 0-7 -N ovlconv -o $W/logs/f_^array_index^.out -e $W/logs/f_^array_index^.err \
  -v REPO_DIR=$R,MAPPING_FILE=$R/studies/overlap_convention_20261015/cluster/mapping.txt,OUT_DIR=$W/out \
  studies/overlap_convention_20261015/cluster/pbs_overlap.sh
```

Next steps:
1. When all 8 jobs are done, run `merge_results.py --in-dir $W/out
   --reference-runs $B/work/mcport_20261014/data`. That reference is the
   production output for the same 8 files, identical to the 14 Oct rebuild
   validation.
2. Copy the results JSON to `results/`, then run `make_plots.py` and write
   `REPORT.md`.
3. Archive the checkout as tar.gz, verify it, and remove only the
   uncompressed checkout.
