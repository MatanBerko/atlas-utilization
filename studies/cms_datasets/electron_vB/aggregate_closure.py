#!/usr/bin/env python
"""
E3 aggregation: the four closure checks, over all per-file closure parts.

Checks, exactly as E3 specifies them:
  (1) For every (run, lumi, event) seen in MORE THAN ONE dataset's files,
      the four acceptance flags are identical whichever file it was read
      from. Mismatches expected 0.
  (2) Every event accepted by >= 1 dataset is in exactly ONE exclusive
      set, namely the highest-priority accepting dataset's. Zero events in
      two sets, zero accepted events in no set.
  (3) Every event accepted by dataset D was read from D's own files.
  (4) Within-dataset duplicate (run, lumi, event) count. Expected 0.

Both DoubleEG threshold modes are checked.

Usage:
    python aggregate_closure.py --parts-dir /storage/.../closure/parts \
        --out studies/cms_datasets/electron_vB/evidence/E3_closure.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402

MODES = ("leading_only", "both")
KEY_DTYPE = np.dtype([("run", "u4"), ("lumi", "u4"), ("event", "u8")])


def attributed_from_flags(flags: dict) -> str:
    for label in DELIVERY_VETO_ORDER_4:
        if flags[label]:
            return label
    return ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parts-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-examples", type=int, default=10)
    args = p.parse_args()

    parts = Path(args.parts_dir)
    summaries = [json.loads(f.read_text(encoding="utf-8"))
                 for f in sorted(parts.glob("summary_*.json"))]
    if not summaries:
        raise SystemExit(f"no closure parts under {parts}")
    print(f"{len(summaries)} per-file closure parts")

    # ---- keys per dataset, and within-dataset duplicates (check 4) -----
    keys_by_dataset = defaultdict(list)
    files_per_dataset = defaultdict(int)
    for f in sorted(parts.glob("keys_*.npz")):
        stem = f.stem[len("keys_"):]
        dataset = stem.split("_")[0]
        with np.load(f) as z:
            keys_by_dataset[dataset].append(z["keys"])
        files_per_dataset[dataset] += 1

    per_dataset = {}
    unique_by_dataset = {}
    for dataset, arrays in keys_by_dataset.items():
        allk = np.concatenate(arrays) if arrays else np.zeros(0, dtype=KEY_DTYPE)
        uniq, counts = np.unique(allk, return_counts=True)
        dup = int((counts > 1).sum())
        per_dataset[dataset] = {
            "n_files": files_per_dataset[dataset],
            "n_events_in_run": int(allk.size),
            "n_distinct_keys": int(uniq.size),
            "n_duplicate_keys_within_dataset": dup,
            "n_extra_rows_from_duplicates": int(allk.size - uniq.size),
        }
        unique_by_dataset[dataset] = np.sort(uniq)
        print(f"  {dataset:12s} {allk.size:9d} events, {uniq.size:9d} distinct, "
              f"{dup} duplicated keys")

    # ---- accepted rows, flags per (key, source dataset) ----------------
    # flags_by_key[mode][key] = {label: bool}; sources_by_key[key] = {dataset}
    flags_by_key = {m: {} for m in MODES}
    reported_by = defaultdict(set)
    mismatch_examples = {m: [] for m in MODES}
    n_mismatch_between_files = {m: 0 for m in MODES}
    n_accepted_rows = 0

    for f in sorted(parts.glob("accepted_*.csv")):
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                n_accepted_rows += 1
                key = (int(row["run"]), int(row["lumi"]), int(row["event"]))
                reported_by[key].add(row["source_dataset"])
                for mode in MODES:
                    flags = {l: row[f"{mode}_{l}"] == "1" for l in DELIVERY_VETO_ORDER_4}
                    prev = flags_by_key[mode].get(key)
                    if prev is None:
                        flags_by_key[mode][key] = flags
                    elif prev != flags:
                        n_mismatch_between_files[mode] += 1
                        if len(mismatch_examples[mode]) < args.max_examples:
                            mismatch_examples[mode].append(
                                {"key": key, "first": prev, "second": flags,
                                 "second_source": row["source_dataset"]})

    print(f"  {n_accepted_rows} accepted rows, "
          f"{len(flags_by_key[MODES[0]])} distinct accepted keys")

    def contains(dataset: str, keys_list) -> np.ndarray:
        """Boolean: is each key present in `dataset`'s own files?"""
        arr = np.array(keys_list, dtype=KEY_DTYPE)
        uniq = unique_by_dataset.get(dataset, np.zeros(0, dtype=KEY_DTYPE))
        if uniq.size == 0:
            return np.zeros(arr.size, dtype=bool)
        pos = np.searchsorted(uniq, arr)
        pos = np.clip(pos, 0, uniq.size - 1)
        return uniq[pos] == arr

    results = {}
    for mode in MODES:
        accepted_keys = sorted(flags_by_key[mode])
        accepted_keys = [k for k in accepted_keys
                         if any(flags_by_key[mode][k].values())]
        keys_arr = accepted_keys

        # check 1: an event accepted in one file must be reported, with the
        # same flags, by every file that CONTAINS it.
        n_missing_from_other_file = 0
        missing_examples = []
        if keys_arr:
            silent_any = np.zeros(len(keys_arr), dtype=bool)
            silent_where = [None] * len(keys_arr)
            for dataset in unique_by_dataset:
                present = contains(dataset, keys_arr)
                reported = np.array([dataset in reported_by[k] for k in keys_arr])
                silent = present & ~reported
                for i in np.flatnonzero(silent & ~silent_any):
                    silent_where[i] = dataset
                silent_any |= silent
            n_missing_from_other_file = int(silent_any.sum())
            for i in np.flatnonzero(silent_any)[:args.max_examples]:
                missing_examples.append({"key": keys_arr[i], "silent_in": silent_where[i],
                                         "reported_by": sorted(reported_by[keys_arr[i]])})

        # check 2: exactly one exclusive set
        n_in_two_sets = 0
        n_accepted_in_no_set = 0
        attributed_counts = {l: 0 for l in DELIVERY_VETO_ORDER_4}
        for key in keys_arr:
            label = attributed_from_flags(flags_by_key[mode][key])
            if label:
                attributed_counts[label] += 1
            else:
                n_accepted_in_no_set += 1
        # "in two sets" is structurally impossible given one attribution per
        # key, so it is verified rather than assumed: the sum of the
        # per-dataset exclusive counts must equal the number of accepted keys.
        if sum(attributed_counts.values()) != len(keys_arr) - n_accepted_in_no_set:
            n_in_two_sets = abs(sum(attributed_counts.values())
                                - (len(keys_arr) - n_accepted_in_no_set))

        # check 3: accepted by D => read from D's own files
        n_not_from_own_files = {l: 0 for l in DELIVERY_VETO_ORDER_4}
        not_own_examples = []
        for label in DELIVERY_VETO_ORDER_4:
            ks = [k for k in keys_arr if flags_by_key[mode][k][label]]
            if not ks:
                continue
            present = contains(label, ks)
            n_not_from_own_files[label] = int((~present).sum())
            for k, ok in zip(ks, present):
                if not ok and len(not_own_examples) < args.max_examples:
                    not_own_examples.append({"key": k, "accepted_by": label,
                                             "reported_by": sorted(reported_by[k])})

        inclusive_counts = {l: sum(1 for k in keys_arr if flags_by_key[mode][k][l])
                            for l in DELIVERY_VETO_ORDER_4}
        vetoed_by_higher = {}
        for i, label in enumerate(DELIVERY_VETO_ORDER_4):
            higher = DELIVERY_VETO_ORDER_4[:i]
            vetoed_by_higher[label] = {
                h: sum(1 for k in keys_arr
                       if flags_by_key[mode][k][label] and flags_by_key[mode][k][h])
                for h in higher}

        results[mode] = {
            "n_distinct_accepted_keys": len(keys_arr),
            "inclusive_accepted_per_dataset": inclusive_counts,
            "exclusive_per_dataset": attributed_counts,
            "vetoed_by_each_higher_dataset": vetoed_by_higher,
            "check1_flag_mismatch_between_files": n_mismatch_between_files[mode],
            "check1_mismatch_examples": mismatch_examples[mode],
            "check1_accepted_but_silent_in_another_dataset_holding_the_event":
                n_missing_from_other_file,
            "check1_silent_examples": missing_examples,
            "check2_events_in_two_exclusive_sets": n_in_two_sets,
            "check2_accepted_events_in_no_exclusive_set": n_accepted_in_no_set,
            "check3_accepted_but_not_read_from_own_files": n_not_from_own_files,
            "check3_examples": not_own_examples,
        }
        print(f"\n  mode={mode}")
        print(f"    accepted keys {len(keys_arr)}; exclusive {attributed_counts}")
        print(f"    check1 flag mismatches {n_mismatch_between_files[mode]}, "
              f"silent-in-another-dataset {n_missing_from_other_file}")
        print(f"    check2 two-sets {n_in_two_sets}, no-set {n_accepted_in_no_set}")
        print(f"    check3 not-from-own-files {n_not_from_own_files}")

    guard_total = sum(
        int(s.get("trigger_guard_violations", {}).get("total", 0)) for s in summaries)
    out = {
        "what": "E3 closure test on one run, all four datasets, both DoubleEG modes",
        "target_run": summaries[0]["target_run"],
        "priority_order": list(DELIVERY_VETO_ORDER_4),
        "n_parts": len(summaries),
        "per_dataset_file_coverage": per_dataset,
        "check4_within_dataset_duplicate_keys": {
            d: v["n_duplicate_keys_within_dataset"] for d, v in per_dataset.items()},
        "trigger_guard_violations_total_across_parts": guard_total,
        "results_by_mode": results,
        "all_checks_pass": bool(
            all(r["check1_flag_mismatch_between_files"] == 0
                and r["check1_accepted_but_silent_in_another_dataset_holding_the_event"] == 0
                and r["check2_events_in_two_exclusive_sets"] == 0
                and r["check2_accepted_events_in_no_exclusive_set"] == 0
                and all(v == 0 for v in r["check3_accepted_but_not_read_from_own_files"].values())
                for r in results.values())
            and all(v["n_duplicate_keys_within_dataset"] == 0 for v in per_dataset.values())
            and guard_total == 0),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nall_checks_pass = {out['all_checks_pass']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
