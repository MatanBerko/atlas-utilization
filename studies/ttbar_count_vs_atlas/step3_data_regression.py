#!/usr/bin/env python
"""
Step 3 proof 1 (ttbar-count-vs-atlas): the --population notrigger addition
did not change DATA mode.

This is studies/cms_mc_weights/v2/compare_v2_data_regression.py extended to
ALL FOUR shard types (normal, top4, nonjet4, rare4) instead of three. It
does not re-implement the comparison: it imports that script's own
read_all_arrays / compare_identical straight out of the file (by path, so
the original is used verbatim and is not modified) and only widens the
baseline/shard tables.

Baseline: the delivered rare4 production run,
output/cms_datasets/runs_matched_rare4/, which is the only production
output that carries all four shard types for the same jobs. It was
produced at commit 635d261; `git diff 635d261 da140cc --
studies/cms_datasets/cluster/run_dataset_on_file.py` is EMPTY, so that
output is exactly what da140cc's driver produces for these files.
Everything under that directory is opened read-only
(mode=ro&immutable=1, inside read_all_arrays) and never written.

Pilot files (the same 4 as the top-4 / nonjet4 / v2 tasks):
  DoubleMuon 30522/0 -> delivered DoubleMuon/job_0
  DoubleMuon 30555/0 -> delivered DoubleMuon/job_29
  SingleMuon 30530/0 -> delivered SingleMuon/job_0
  SingleMuon 30563/0 -> delivered SingleMuon/job_70

Usage:
    python step3_data_regression.py --new-base <dir> --out <report.json>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

_V2 = REPO_ROOT / "studies" / "cms_mc_weights" / "v2" / "compare_v2_data_regression.py"
_spec = importlib.util.spec_from_file_location("compare_v2_data_regression", _V2)
_v2mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_v2mod)

read_all_arrays = _v2mod.read_all_arrays
compare_identical = _v2mod.compare_identical

BASELINE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_rare4"

# (new run dir name, delivered dataset dir, delivered job index)
RUNS = [
    ("DoubleMuon_30522_0", "DoubleMuon", 0),
    ("DoubleMuon_30555_0", "DoubleMuon", 29),
    ("SingleMuon_30530_0", "SingleMuon", 0),
    ("SingleMuon_30563_0", "SingleMuon", 70),
]

# All four shard types, inclusive and exclusive -- the extension over
# compare_v2_data_regression.py, which stopped at nonjet4.
SHARDS = [
    "dataset_shard_inclusive.sqlite",
    "dataset_shard_exclusive.sqlite",
    "dataset_shard_top4_inclusive.sqlite",
    "dataset_shard_top4_exclusive.sqlite",
    "dataset_shard_nonjet4_inclusive.sqlite",
    "dataset_shard_nonjet4_exclusive.sqlite",
    "dataset_shard_rare4_inclusive.sqlite",
    "dataset_shard_rare4_exclusive.sqlite",
]

METADATA_KEYS = list(_v2mod.METADATA_KEYS)
TOP4_DIAG_KEYS = list(_v2mod.TOP4_DIAG_KEYS)
NONJET4_DIAG_KEYS = list(_v2mod.NONJET4_DIAG_KEYS)
RARE4_DIAG_KEYS = [
    "n_accepted_events_before_rare4_rule", "n_rejected_gt4_lepton_bjet",
    "n_kept_le4_lepton_bjet", "n_hidden_cases",
    "n_fs_groups",
    "n_signature_writes_inclusive", "n_signature_writes_exclusive",
    "n_values_written_inclusive", "n_values_written_exclusive",
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--new-base", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    all_checks = []
    overall_pass = True

    for new_run, old_label, old_job in RUNS:
        new_dir = f"{args.new_base}/{new_run}"
        old_dir = f"{BASELINE}/{old_label}/job_{old_job}"

        shard_checks = []
        for shard in SHARDS:
            result = compare_identical(f"{old_dir}/{shard}", f"{new_dir}/{shard}",
                                       f"{new_run}/{shard}")
            shard_checks.append(result)
            print(f"[{new_run}] {shard}: {'PASS' if result['pass'] else 'FAIL'} "
                  f"({result.get('n_signatures', '?')} sigs, "
                  f"{result.get('n_mismatched', '?')} mismatched)", flush=True)

        old_meta = json.load(open(f"{old_dir}/job_metadata.json"))
        new_meta = json.load(open(f"{new_dir}/job_metadata.json"))

        meta_mismatches = []
        for key in METADATA_KEYS:
            if old_meta.get(key) != new_meta.get(key):
                meta_mismatches.append({"key": key, "old": old_meta.get(key), "new": new_meta.get(key)})
        for block, keys in (("top4_diagnostics", TOP4_DIAG_KEYS),
                            ("nonjet4_diagnostics", NONJET4_DIAG_KEYS),
                            ("rare4_diagnostics", RARE4_DIAG_KEYS)):
            for key in keys:
                old_v = old_meta[block][key]
                new_v = new_meta[block][key]
                if old_v != new_v:
                    meta_mismatches.append({"key": f"{block}.{key}", "old": old_v, "new": new_v})

        # The per-final-state event-count maps, in full -- a stronger check
        # than the scalar counts above: it would catch a final state whose
        # label or membership moved even if the totals happened to match.
        for block in ("final_state_label_event_counts_inclusive",
                      "final_state_label_event_counts_exclusive"):
            if old_meta.get(block) != new_meta.get(block):
                meta_mismatches.append({"key": block, "old": "<map>", "new": "<map differs>"})
        for diag in ("top4_diagnostics", "nonjet4_diagnostics", "rare4_diagnostics"):
            for block in ("final_state_label_event_counts_inclusive",
                          "final_state_label_event_counts_exclusive"):
                if old_meta[diag].get(block) != new_meta[diag].get(block):
                    meta_mismatches.append({"key": f"{diag}.{block}", "old": "<map>", "new": "<map differs>"})

        # The new mode must leave no trace in a non-notrigger run.
        if new_meta.get("notrigger_diagnostics") is not None:
            meta_mismatches.append({"key": "notrigger_diagnostics",
                                    "old": None, "new": "not None in a data-mode run"})
        stray = sorted(Path(new_dir).glob("dataset_shard_notrigger_*"))
        if stray:
            meta_mismatches.append({"key": "stray notrigger shards",
                                    "old": [], "new": [s.name for s in stray]})

        metadata_pass = len(meta_mismatches) == 0
        print(f"[{new_run}] job_metadata.json counts + per-final-state maps: "
              f"{'PASS' if metadata_pass else 'FAIL'} ({len(meta_mismatches)} mismatches)", flush=True)

        this_pass = all(c["pass"] for c in shard_checks) and metadata_pass
        overall_pass = overall_pass and this_pass
        all_checks.append({
            "new_run": new_run, "old_label": old_label, "old_job": old_job,
            "baseline_dir": old_dir, "new_dir": new_dir,
            "baseline_git_commit": old_meta.get("git_commit"),
            "new_git_commit": new_meta.get("git_commit"),
            "shard_checks": shard_checks,
            "metadata_mismatches": meta_mismatches,
            "all_pass": this_pass,
        })

    result = {
        "what": "data-mode regression: 4 pilot files, all 4 shard types, "
                "new driver vs delivered production output",
        "baseline": BASELINE,
        "baseline_driver_identical_to_da140cc": True,
        "overall_pass": overall_pass,
        "n_shard_comparisons": len(RUNS) * len(SHARDS),
        "per_file": all_checks,
    }
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'} "
          f"({len(RUNS) * len(SHARDS)} shard comparisons)")
    print(f"wrote {args.out}")
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
