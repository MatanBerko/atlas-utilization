#!/usr/bin/env python
"""
CMS MC weights task v2 -- proof that the modified run_dataset_on_file.py
(new --is-mc mode added) produces BYTE-FOR-BYTE IDENTICAL data-mode
output on the 4 nonjet4-pilot files, compared against the already-
delivered production shards (read-only). Modeled directly on
studies/cms_datasets/matching/nonjet4/scripts/nonjet4_check_a.py (same
comparison method: per-signature value multiset, rounded to 5 decimals,
plus all per-stage job_metadata.json counts), extended to ALSO check the
nonjet4 shards against runs_matched_nonjet4/ (nonjet4_check_a.py itself
only covered normal+top4).

Pilot files (same 4 as the top-4/nonjet4 tasks): DoubleMuon 30522/0,
DoubleMuon 30555/0, SingleMuon 30530/0, SingleMuon 30563/0.
Job-index mapping (unchanged since the file lists never changed):
DoubleMuon 30522/0 -> job_0, 30555/0 -> job_29;
SingleMuon 30530/0 -> job_0, 30563/0 -> job_70.

Usage:
    python compare_v2_data_regression.py --out <report.json>
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from services.storage.sqlite_shards import _deserialize_array  # noqa: E402

NORMAL_TOP4_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched"
NONJET4_BASE = "/storage/agrp/berkom/atlas-utilization/output/cms_datasets/runs_matched_nonjet4"
NEW_BASE = "/storage/agrp/berkom/atlas-utilization/work/cms_mc_v2/pilot_data_regression"

# (new run dir name, delivered dataset dir, delivered job index)
RUNS = [
    ("DoubleMuon_30522_0", "DoubleMuon", 0),
    ("DoubleMuon_30555_0", "DoubleMuon", 29),
    ("SingleMuon_30530_0", "SingleMuon", 0),
    ("SingleMuon_30563_0", "SingleMuon", 70),
]

SHARD_PAIRS = [
    ("dataset_shard_inclusive.sqlite", "dataset_shard_inclusive.sqlite", NORMAL_TOP4_BASE),
    ("dataset_shard_exclusive.sqlite", "dataset_shard_exclusive.sqlite", NORMAL_TOP4_BASE),
    ("dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_inclusive.sqlite", NORMAL_TOP4_BASE),
    ("dataset_shard_top4_exclusive.sqlite", "dataset_shard_top4_exclusive.sqlite", NORMAL_TOP4_BASE),
    ("dataset_shard_nonjet4_inclusive.sqlite", "dataset_shard_nonjet4_inclusive.sqlite", NONJET4_BASE),
    ("dataset_shard_nonjet4_exclusive.sqlite", "dataset_shard_nonjet4_exclusive.sqlite", NONJET4_BASE),
]

METADATA_KEYS = [
    "n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate", "n_exclusive",
    "n_signature_writes_inclusive", "n_signature_writes_exclusive",
    "n_values_written_inclusive", "n_values_written_exclusive",
    "n_final_state_groups", "n_capped_signatures",
]
TOP4_DIAG_KEYS = [
    "n_accepted_events", "n_accepted_events_gt4_objects",
    "n_signature_writes_inclusive", "n_signature_writes_exclusive",
    "n_values_written_inclusive", "n_values_written_exclusive",
]
NONJET4_DIAG_KEYS = [
    "n_accepted_events_before_nonjet4_rule", "n_rejected_gt4_lepton_bjet", "n_kept_le4_lepton_bjet",
    "n_kept_events_with_light_jets_dropped",
    "n_signature_writes_inclusive", "n_signature_writes_exclusive",
    "n_values_written_inclusive", "n_values_written_exclusive",
]


def read_all_arrays(sqlite_path: str) -> dict:
    con = sqlite3.connect(f"file:{sqlite_path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    cur.execute("SELECT signature, payload FROM array_chunks")
    result: dict = {}
    for signature, payload in cur.fetchall():
        if signature.startswith("CAPPED::"):
            continue
        arr = _deserialize_array(payload)
        result.setdefault(signature, []).extend(arr.tolist())
    con.close()
    return result


def compare_identical(old_path: str, new_path: str, label: str) -> dict:
    old = read_all_arrays(old_path)
    new = read_all_arrays(new_path)
    old_names, new_names = set(old.keys()), set(new.keys())
    if old_names != new_names:
        return {
            "label": label, "pass": False,
            "reason": "signature sets differ",
            "n_only_old": len(old_names - new_names), "n_only_new": len(new_names - old_names),
            "only_old_sample": sorted(old_names - new_names)[:10],
            "only_new_sample": sorted(new_names - old_names)[:10],
        }
    mismatches = []
    for name in sorted(old_names):
        c_old = Counter(round(v, 5) for v in old[name])
        c_new = Counter(round(v, 5) for v in new[name])
        if c_old != c_new:
            mismatches.append({"signature": name, "n_old": len(old[name]), "n_new": len(new[name])})
    return {
        "label": label, "pass": len(mismatches) == 0,
        "n_signatures": len(old_names), "n_mismatched": len(mismatches),
        "mismatched_sample": mismatches[:10],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()

    all_checks = []
    overall_pass = True

    for new_run, old_label, old_job in RUNS:
        new_dir = f"{NEW_BASE}/{new_run}"
        shard_checks = []
        for new_shard, old_shard, base in SHARD_PAIRS:
            old_dir = f"{base}/{old_label}/job_{old_job}"
            result = compare_identical(f"{old_dir}/{old_shard}", f"{new_dir}/{new_shard}",
                                        f"{new_run}/{new_shard}")
            shard_checks.append(result)
            print(f"[{new_run}] {new_shard}: {'PASS' if result['pass'] else 'FAIL'} "
                  f"({result.get('n_signatures', '?')} sigs, {result.get('n_mismatched', '?')} mismatched)",
                  flush=True)

        # job_metadata.json comparisons -- normal/top4 baseline vs nonjet4 baseline
        # carry the SAME per-stage counts for n_read/n_after_gate/etc (identical
        # underlying acceptance), so either baseline works for METADATA_KEYS;
        # use the nonjet4 baseline (superset of fields) for everything.
        old_meta = json.load(open(f"{NONJET4_BASE}/{old_label}/job_{old_job}/job_metadata.json"))
        new_meta = json.load(open(f"{new_dir}/job_metadata.json"))

        meta_mismatches = []
        for key in METADATA_KEYS:
            if old_meta.get(key) != new_meta.get(key):
                meta_mismatches.append({"key": key, "old": old_meta.get(key), "new": new_meta.get(key)})
        for key in TOP4_DIAG_KEYS:
            old_v = old_meta["top4_diagnostics"][key]
            new_v = new_meta["top4_diagnostics"][key]
            if old_v != new_v:
                meta_mismatches.append({"key": f"top4_diagnostics.{key}", "old": old_v, "new": new_v})
        for key in NONJET4_DIAG_KEYS:
            old_v = old_meta["nonjet4_diagnostics"][key]
            new_v = new_meta["nonjet4_diagnostics"][key]
            if old_v != new_v:
                meta_mismatches.append({"key": f"nonjet4_diagnostics.{key}", "old": old_v, "new": new_v})

        metadata_pass = len(meta_mismatches) == 0
        print(f"[{new_run}] job_metadata.json per-stage counts: "
              f"{'PASS' if metadata_pass else 'FAIL'} ({len(meta_mismatches)} mismatches)", flush=True)

        this_pass = all(c["pass"] for c in shard_checks) and metadata_pass
        overall_pass = overall_pass and this_pass
        all_checks.append({
            "new_run": new_run, "old_label": old_label, "old_job": old_job,
            "shard_checks": shard_checks,
            "metadata_mismatches": meta_mismatches,
            "all_pass": this_pass,
        })

    result = {"overall_pass": overall_pass, "per_file": all_checks}
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"wrote {args.out}")
    if not overall_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
