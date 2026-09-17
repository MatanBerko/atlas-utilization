#!/usr/bin/env python
"""
Statistical-model task, Part 5.1: GATED cluster-side merge of the 133
per-job BLINDED_SIGNAL_REGION data files with the already-merged
sideband file into ONE full-range (105-180 GeV) data file, for the real
(unblinded) fit.

THIS TASK DOES NOT RUN THIS SCRIPT. Prepared only, and gated behind
`studies.hgg_cms.stats.unblind.gate.check_gate` -- see that module's
docstring for exactly what is required. Running it without every gate
condition met refuses immediately, before opening any data file.

File-identity check (in addition to the gate): refuses unless exactly
133 per-job BLINDED_SIGNAL_REGION files are found under
`--blinded-jobs-base/job_*/selected/`, the blinded event count across
all of them equals `--expected-blinded-count` (default 78992), and the
sideband file's own event count equals `--expected-sideband-count`
(default 182551) -- both defaults are this task's own recorded,
already-computed totals (see the task's own context notes), not
recomputed here from anything blinded.

Every blinded file is opened ONLY through
`studies.hgg_cms.output.read_output(path, unblind=True)` -- the shared
pipeline's own blinding-aware reader -- and the merged output is written
to a NEW file (never overwrites `--out` if it already exists), so a
previous unblinding attempt's output is never silently clobbered.

Usage (FOR LATER, AFTER EXPLICIT APPROVAL -- see the final chat message):
    HGG_UNBLIND_APPROVED=<frozen commit hash> \\
    python studies/hgg_cms/stats/unblind/merge_full_range.py \\
        --i-have-explicit-approval-to-unblind \\
        --blinded-jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_full/data \\
        --sideband-file /storage/agrp/berkom/atlas-utilization/output/hgg_full/merged/data_sidebands.root \\
        --out /storage/agrp/berkom/atlas-utilization/output/hgg_stats/unblinded/data_full_range.root
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.stats.unblind.gate import check_gate, APPROVAL_ENV_VAR, APPROVAL_FLAG  # noqa: E402

EXPECTED_N_BLINDED_JOBS = 133
EXPECTED_BLINDED_COUNT_DEFAULT = 78_992
EXPECTED_SIDEBAND_COUNT_DEFAULT = 182_551


def main():
    p = argparse.ArgumentParser()
    p.add_argument(APPROVAL_FLAG, action="store_true", default=False)
    p.add_argument("--blinded-jobs-base", required=True)
    p.add_argument("--sideband-file", required=True)
    p.add_argument("--expected-blinded-count", type=int, default=EXPECTED_BLINDED_COUNT_DEFAULT)
    p.add_argument("--expected-sideband-count", type=int, default=EXPECTED_SIDEBAND_COUNT_DEFAULT)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    import os
    gate = check_gate(repo_dir=str(REPO_ROOT), flag_present=args.i_have_explicit_approval_to_unblind,
                       env_value=os.environ.get(APPROVAL_ENV_VAR, ""))
    if not gate.ok:
        print(f"REFUSED: {gate.reason}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out)
    if out_path.exists():
        print(f"REFUSED: {out_path} already exists -- never overwriting a previous unblinding attempt's "
              f"output; move it aside yourself first if you really want to redo this.", file=sys.stderr)
        sys.exit(1)

    from studies.hgg_cms.output import read_output, BLINDED_MARKER
    import awkward as ak

    jobs_base = Path(args.blinded_jobs_base)
    blinded_files = sorted(jobs_base.glob(f"job_*/selected/*{BLINDED_MARKER}*.root"))
    job_dirs_with_file = {f.parents[1].name for f in blinded_files}
    if len(job_dirs_with_file) != EXPECTED_N_BLINDED_JOBS:
        print(f"REFUSED: found {len(job_dirs_with_file)} job directories with a {BLINDED_MARKER} file "
              f"under {jobs_base}, expected exactly {EXPECTED_N_BLINDED_JOBS}.", file=sys.stderr)
        sys.exit(1)

    blinded_arrays = [read_output(f, unblind=True) for f in blinded_files]
    n_blinded = sum(len(a) for a in blinded_arrays)
    if n_blinded != args.expected_blinded_count:
        print(f"REFUSED: total blinded event count across all {EXPECTED_N_BLINDED_JOBS} jobs is "
              f"{n_blinded}, expected {args.expected_blinded_count}.", file=sys.stderr)
        sys.exit(1)

    sideband_arr = read_output(Path(args.sideband_file), unblind=False)
    if len(sideband_arr) != args.expected_sideband_count:
        print(f"REFUSED: sideband file has {len(sideband_arr)} events, expected "
              f"{args.expected_sideband_count}.", file=sys.stderr)
        sys.exit(1)

    full = ak.concatenate(blinded_arrays + [sideband_arr])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    import uproot
    with uproot.recreate(out_path) as f:
        f["events"] = full
    print(f"wrote {out_path}: {len(full)} events "
          f"({n_blinded} from signal region + {len(sideband_arr)} from sidebands)")


if __name__ == "__main__":
    main()
