#!/usr/bin/env python
"""
Step 3 proof 2 (ttbar-count-vs-atlas): the --population notrigger addition
did not change --population matched --is-mc either.

Compares a freshly-run `--population matched --is-mc` job on ONE TTTo2L2Nu
(record 67801) file against the SAME file's output in the paused MC v2
production run under work/cms_mc_v2/67801/DoubleMuon/.  The paused run is
read-only throughout: every shard is opened with mode=ro&immutable=1 (via
compare_v2_data_regression.read_all_arrays) and nothing under
work/cms_mc_v2/ is written, moved or deleted.

Checked: the normal / top4 / nonjet4 MASS shards (inclusive + exclusive)
AND the corresponding WEIGHT shards, plus the per-stage counts in
job_metadata.json.  The paused run predates the rare4 version, so its
directories carry no rare4 shard and none is compared -- that absence is
reported explicitly rather than silently skipped.

Usage:
    python step3_mc_identity.py --new-dir <dir> --old-dir <dir> --out <report.json>
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
compare_identical = _v2mod.compare_identical

MASS_SHARDS = [
    "dataset_shard_inclusive.sqlite",
    "dataset_shard_exclusive.sqlite",
    "dataset_shard_top4_inclusive.sqlite",
    "dataset_shard_top4_exclusive.sqlite",
    "dataset_shard_nonjet4_inclusive.sqlite",
    "dataset_shard_nonjet4_exclusive.sqlite",
]
WEIGHT_SHARDS = [
    "dataset_shard_weights_inclusive.sqlite",
    "dataset_shard_weights_exclusive.sqlite",
    "dataset_shard_top4_weights_inclusive.sqlite",
    "dataset_shard_top4_weights_exclusive.sqlite",
    "dataset_shard_nonjet4_weights_inclusive.sqlite",
    "dataset_shard_nonjet4_weights_exclusive.sqlite",
]

METADATA_KEYS = [
    "n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate", "n_exclusive",
    "n_signature_writes_inclusive", "n_signature_writes_exclusive",
    "n_values_written_inclusive", "n_values_written_exclusive",
    "n_final_state_groups", "n_capped_signatures",
    "file_url", "record_id", "file_index", "population", "is_mc",
    "mc_sum_genweight_all_events_this_file", "mc_runs_tree_sums_this_file",
    "final_state_label_event_counts_inclusive", "final_state_label_event_counts_exclusive",
]
DIAG_BLOCKS = {
    "top4_diagnostics": [
        "n_accepted_events", "n_accepted_events_gt4_objects",
        "n_signature_writes_inclusive", "n_signature_writes_exclusive",
        "n_values_written_inclusive", "n_values_written_exclusive",
        "final_state_label_event_counts_inclusive", "final_state_label_event_counts_exclusive",
    ],
    "nonjet4_diagnostics": [
        "n_accepted_events_before_nonjet4_rule", "n_rejected_gt4_lepton_bjet",
        "n_kept_le4_lepton_bjet", "n_kept_events_with_light_jets_dropped",
        "n_signature_writes_inclusive", "n_signature_writes_exclusive",
        "n_values_written_inclusive", "n_values_written_exclusive",
        "final_state_label_event_counts_inclusive", "final_state_label_event_counts_exclusive",
    ],
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--new-dir", required=True)
    p.add_argument("--old-dir", required=True, help="paused MC v2 job dir (read-only)")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    checks = []
    overall_pass = True

    for shard in MASS_SHARDS + WEIGHT_SHARDS:
        old_p = Path(args.old_dir) / shard
        new_p = Path(args.new_dir) / shard
        if not old_p.exists():
            checks.append({"label": shard, "pass": False, "reason": "missing in paused run"})
            overall_pass = False
            print(f"{shard}: FAIL (missing in paused run)", flush=True)
            continue
        r = compare_identical(str(old_p), str(new_p), shard)
        checks.append(r)
        overall_pass = overall_pass and r["pass"]
        print(f"{shard}: {'PASS' if r['pass'] else 'FAIL'} "
              f"({r.get('n_signatures', '?')} sigs, {r.get('n_mismatched', '?')} mismatched)", flush=True)

    old_meta = json.load(open(f"{args.old_dir}/job_metadata.json"))
    new_meta = json.load(open(f"{args.new_dir}/job_metadata.json"))

    meta_mismatches = []
    for key in METADATA_KEYS:
        if old_meta.get(key) != new_meta.get(key):
            meta_mismatches.append({"key": key,
                                    "old": str(old_meta.get(key))[:200],
                                    "new": str(new_meta.get(key))[:200]})
    for block, keys in DIAG_BLOCKS.items():
        for key in keys:
            if old_meta[block][key] != new_meta[block][key]:
                meta_mismatches.append({"key": f"{block}.{key}",
                                        "old": str(old_meta[block][key])[:200],
                                        "new": str(new_meta[block][key])[:200]})
    if new_meta.get("notrigger_diagnostics") is not None:
        meta_mismatches.append({"key": "notrigger_diagnostics",
                                "old": None, "new": "not None in a matched-mode run"})
    stray = sorted(Path(args.new_dir).glob("dataset_shard_notrigger_*"))
    if stray:
        meta_mismatches.append({"key": "stray notrigger shards",
                                "old": [], "new": [s.name for s in stray]})

    metadata_pass = len(meta_mismatches) == 0
    overall_pass = overall_pass and metadata_pass
    print(f"job_metadata.json: {'PASS' if metadata_pass else 'FAIL'} "
          f"({len(meta_mismatches)} mismatches)", flush=True)

    result = {
        "what": "matched --is-mc identity: one TTTo2L2Nu file, new driver vs paused MC v2 run",
        "new_dir": args.new_dir,
        "old_dir": args.old_dir,
        "old_git_commit": old_meta.get("git_commit"),
        "new_git_commit": new_meta.get("git_commit"),
        "file_url": new_meta.get("file_url"),
        "rare4_shard_in_paused_run": (Path(args.old_dir) / "dataset_shard_rare4_inclusive.sqlite").exists(),
        "note_rare4": "the paused MC v2 run was produced before the rare4 version existed, so it "
                      "carries no rare4 shard and none is compared here",
        "overall_pass": overall_pass,
        "shard_checks": checks,
        "metadata_mismatches": meta_mismatches,
    }
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"wrote {args.out}")
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
