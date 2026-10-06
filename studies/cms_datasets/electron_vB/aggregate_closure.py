#!/usr/bin/env python
"""
E3 aggregation: the four closure checks, over all per-file closure parts.

Checks, exactly as E3 specifies them:
  (1) For every (run, lumi, event) seen in MORE THAN ONE dataset's files,
      the four acceptance flags are identical whichever file it was read
      from. Mismatches expected 0. Two ways of being wrong are counted
      separately: two files reporting DIFFERENT flags for the same event,
      and one file reporting an event accepted while another dataset that
      HOLDS the same event is silent about it.
  (2) Every event accepted by >= 1 dataset is in exactly ONE exclusive
      set, namely the highest-priority accepting dataset's. Zero events in
      two sets, zero accepted events in no set.
  (3) Every event accepted by dataset D was read from D's own files.
  (4) Within-dataset duplicate (run, lumi, event) count. Expected 0.

Both DoubleEG threshold modes are checked.

Fully vectorised: at the scale this runs at (millions of accepted rows over
tens of millions of events) a per-event Python dict does not finish.

Usage:
    python aggregate_closure.py --parts-dir /storage/.../closure/parts \
        --out studies/cms_datasets/electron_vB/evidence/E3_closure.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402

MODES = ("leading_only", "both")
KEY_DTYPE = np.dtype([("run", "u4"), ("lumi", "u4"), ("event", "u8")])
N_DS = len(DELIVERY_VETO_ORDER_4)


def _as_keys(run, lumi, event) -> np.ndarray:
    out = np.zeros(len(run), dtype=KEY_DTYPE)
    out["run"] = run
    out["lumi"] = lumi
    out["event"] = event
    return out


def load_accepted(parts: Path):
    """Concatenated accepted rows: keys, per-mode flag matrices, source index.

    The source dataset is taken from the FILE NAME, not from the csv column:
    one file is one (dataset, era, file index), so every row in it has the
    same source. Only the numeric columns are parsed.
    """
    keys_parts, flag_parts, src_parts = [], {m: [] for m in MODES}, []
    n_rows = 0
    files = sorted(parts.glob("accepted_*.csv"))
    for f in files:
        dataset = f.stem[len("accepted_"):].split("_")[0]
        src = DELIVERY_VETO_ORDER_4.index(dataset)
        # columns: run,lumi,event,source_dataset,<4 flags mode0>,<4 flags mode1>,
        #          <attributed mode0>,<attributed mode1>
        cols = (0, 1, 2) + tuple(range(4, 4 + N_DS * len(MODES)))
        try:
            arr = np.loadtxt(f, delimiter=",", skiprows=1, usecols=cols, dtype=np.int64,
                             ndmin=2)
        except (StopIteration, ValueError):
            arr = np.zeros((0, len(cols)), dtype=np.int64)
        if arr.size == 0:
            continue
        keys_parts.append(_as_keys(arr[:, 0], arr[:, 1], arr[:, 2]))
        for i, mode in enumerate(MODES):
            lo = 3 + i * N_DS
            flag_parts[mode].append(arr[:, lo:lo + N_DS].astype(bool))
        src_parts.append(np.full(arr.shape[0], src, dtype=np.int8))
        n_rows += arr.shape[0]
    if not keys_parts:
        return (np.zeros(0, dtype=KEY_DTYPE),
                {m: np.zeros((0, N_DS), dtype=bool) for m in MODES},
                np.zeros(0, dtype=np.int8), 0, len(files))
    return (np.concatenate(keys_parts),
            {m: np.concatenate(flag_parts[m]) for m in MODES},
            np.concatenate(src_parts), n_rows, len(files))


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
    print(f"{len(summaries)} per-file closure parts", flush=True)

    # ---- every event of the run, per dataset: checks (3) and (4) --------
    per_dataset = {}
    unique_by_dataset = {}
    for label in DELIVERY_VETO_ORDER_4:
        arrays = []
        n_files = 0
        for f in sorted(parts.glob(f"keys_{label}_*.npz")):
            with np.load(f) as z:
                arrays.append(z["keys"])
            n_files += 1
        allk = np.concatenate(arrays) if arrays else np.zeros(0, dtype=KEY_DTYPE)
        uniq, counts = np.unique(allk, return_counts=True)
        per_dataset[label] = {
            "n_files": n_files,
            "n_events_in_run": int(allk.size),
            "n_distinct_keys": int(uniq.size),
            "n_duplicate_keys_within_dataset": int((counts > 1).sum()),
            "n_extra_rows_from_duplicates": int(allk.size - uniq.size),
        }
        unique_by_dataset[label] = uniq          # np.unique returns it sorted
        print(f"  {label:12s} {allk.size:9d} events, {uniq.size:9d} distinct, "
              f"{int((counts > 1).sum())} duplicated", flush=True)

    def contains(label: str, keys: np.ndarray) -> np.ndarray:
        uniq = unique_by_dataset[label]
        if uniq.size == 0 or keys.size == 0:
            return np.zeros(keys.size, dtype=bool)
        pos = np.clip(np.searchsorted(uniq, keys), 0, uniq.size - 1)
        return uniq[pos] == keys

    # ---- the accepted rows ---------------------------------------------
    keys, flags_by_mode, src, n_rows, n_csv = load_accepted(parts)
    print(f"  {n_rows} accepted rows from {n_csv} csv files", flush=True)

    uniq_keys, inverse = np.unique(keys, return_inverse=True)
    n_uniq = uniq_keys.size
    print(f"  {n_uniq} distinct accepted keys", flush=True)

    # which datasets REPORTED each distinct key (i.e. read it and found it
    # accepted in at least one mode)
    reported = np.zeros((n_uniq, N_DS), dtype=bool)
    reported[inverse, src] = True

    results = {}
    for mode in MODES:
        fl = flags_by_mode[mode]

        # check (1a): two rows for the same event must carry the same flags.
        # Compare every row against the first row of its own key group.
        order = np.argsort(inverse, kind="stable")
        inv_sorted = inverse[order]
        first_of_group = np.zeros(n_uniq, dtype=np.int64)
        starts = np.flatnonzero(np.r_[True, inv_sorted[1:] != inv_sorted[:-1]])
        first_of_group[inv_sorted[starts]] = order[starts]
        mismatch_row = np.any(fl != fl[first_of_group[inverse]], axis=1)
        n_mismatch = int(mismatch_row.sum())

        # per-key flags (the group's first row; identical to all of them
        # unless n_mismatch > 0, which is reported)
        key_flags = fl[first_of_group]
        accepted_any = key_flags.any(axis=1)

        # check (1b): a dataset that HOLDS the event but never reported it
        holds = np.column_stack([contains(l, uniq_keys) for l in DELIVERY_VETO_ORDER_4])
        silent = holds & ~reported & accepted_any[:, None]
        n_silent = int(silent.any(axis=1).sum())

        # check (2): attribution to the highest-priority accepting dataset
        attributed = np.where(accepted_any, np.argmax(key_flags, axis=1), -1)
        exclusive_counts = {l: int((attributed == i).sum())
                            for i, l in enumerate(DELIVERY_VETO_ORDER_4)}
        n_accepted_no_set = int((accepted_any & (attributed < 0)).sum())
        n_two_sets = int(sum(exclusive_counts.values())
                         - int(accepted_any.sum()) + n_accepted_no_set)

        # check (3): accepted by D => read from D's own files
        not_from_own = {}
        examples_not_own = []
        for i, label in enumerate(DELIVERY_VETO_ORDER_4):
            sel = key_flags[:, i]
            bad = sel & ~holds[:, i]
            not_from_own[label] = int(bad.sum())
            for k in uniq_keys[bad][:args.max_examples]:
                examples_not_own.append({"accepted_by": label,
                                         "key": [int(k["run"]), int(k["lumi"]),
                                                 int(k["event"])]})

        inclusive_counts = {l: int(key_flags[:, i].sum())
                            for i, l in enumerate(DELIVERY_VETO_ORDER_4)}
        vetoed_by_higher = {}
        for i, label in enumerate(DELIVERY_VETO_ORDER_4):
            vetoed_by_higher[label] = {
                h: int((key_flags[:, i] & key_flags[:, j]).sum())
                for j, h in enumerate(DELIVERY_VETO_ORDER_4[:i])}

        # ---- what the PRODUCTION pipeline would actually count -----------
        # Production decides per file: dataset s includes the event iff s's
        # OWN copy says s accepts it and no higher-priority dataset accepts
        # it -- using the flags from s's own copy, which is the whole point.
        # When two copies of one collision disagree (see
        # check1_*), that can make a collision counted twice or not at all.
        # This is the number that matters for the delivery, so it is measured
        # rather than argued about.
        prefix_or = np.zeros_like(fl)
        running = np.zeros(fl.shape[0], dtype=bool)
        for i in range(N_DS):
            prefix_or[:, i] = running
            running = running | fl[:, i]
        rows = np.arange(fl.shape[0])
        own_flag = fl[rows, src]
        higher_any = prefix_or[rows, src]
        included = own_flag & ~higher_any
        times_counted = np.bincount(inverse[included], minlength=n_uniq)
        accepted_somewhere = np.zeros(n_uniq, dtype=bool)
        np.logical_or.at(accepted_somewhere, inverse, fl.any(axis=1))
        n_lost = int(((times_counted == 0) & accepted_somewhere).sum())
        n_once = int((times_counted == 1).sum())
        n_multi = int((times_counted > 1).sum())
        lost_examples = [[int(k["run"]), int(k["lumi"]), int(k["event"])]
                         for k in uniq_keys[(times_counted == 0) & accepted_somewhere]
                         [:args.max_examples]]
        multi_examples = [[int(k["run"]), int(k["lumi"]), int(k["event"])]
                          for k in uniq_keys[times_counted > 1][:args.max_examples]]

        ex_mismatch = [{"key": [int(k["run"]), int(k["lumi"]), int(k["event"])]}
                       for k in keys[mismatch_row][:args.max_examples]]
        ex_silent = []
        for idx in np.flatnonzero(silent.any(axis=1))[:args.max_examples]:
            k = uniq_keys[idx]
            ex_silent.append({
                "key": [int(k["run"]), int(k["lumi"]), int(k["event"])],
                "silent_in": [DELIVERY_VETO_ORDER_4[j]
                              for j in np.flatnonzero(silent[idx])],
                "reported_by": [DELIVERY_VETO_ORDER_4[j]
                                for j in np.flatnonzero(reported[idx])]})

        results[mode] = {
            "n_distinct_accepted_keys": int(accepted_any.sum()),
            "inclusive_accepted_per_dataset": inclusive_counts,
            "exclusive_per_dataset": exclusive_counts,
            "vetoed_by_each_higher_dataset": vetoed_by_higher,
            "check1_rows_with_flags_differing_from_another_file": n_mismatch,
            "check1_mismatch_examples": ex_mismatch,
            "check1_accepted_but_silent_in_another_dataset_holding_the_event": n_silent,
            "check1_silent_examples": ex_silent,
            "check2_events_in_two_exclusive_sets": n_two_sets,
            "check2_accepted_events_in_no_exclusive_set": n_accepted_no_set,
            "check3_accepted_but_not_read_from_own_files": not_from_own,
            "check3_examples": examples_not_own,
            "delivery_counting": {
                "what": ("how many times each collision the production pipeline "
                         "would actually deliver gets counted, with each dataset "
                         "deciding from ITS OWN copy -- the consequence of the "
                         "copy-to-copy differences that check (1) exposes"),
                "n_counted_exactly_once": n_once,
                "n_counted_more_than_once": n_multi,
                "n_accepted_somewhere_but_counted_zero_times": n_lost,
                "n_counted_more_than_once_per_million_delivered": (
                    round(1e6 * n_multi / n_once, 2) if n_once else None),
                "n_lost_per_million_delivered": (
                    round(1e6 * n_lost / n_once, 2) if n_once else None),
                "examples_counted_twice": multi_examples,
                "examples_lost": lost_examples,
            },
        }
        print(f"\n  mode={mode}", flush=True)
        print(f"    accepted keys {int(accepted_any.sum())}")
        print(f"    inclusive {inclusive_counts}")
        print(f"    exclusive {exclusive_counts}")
        print(f"    check1 flag mismatches {n_mismatch}, silent-elsewhere {n_silent}")
        print(f"    check2 two-sets {n_two_sets}, no-set {n_accepted_no_set}")
        print(f"    check3 not-from-own-files {not_from_own}")
        print(f"    delivery counting: once {n_once}, twice-or-more {n_multi}, "
              f"lost {n_lost}")

    guard_total = sum(int(s.get("trigger_guard_violations", {}).get("total", 0))
                      for s in summaries)
    n_removed = sum(int(s.get("n_electrons_removed", 0)) for s in summaries)
    out = {
        "what": "E3 closure test on one run, all four datasets, both DoubleEG modes",
        "target_run": summaries[0]["target_run"],
        "priority_order": list(DELIVERY_VETO_ORDER_4),
        "n_parts": len(summaries),
        "n_accepted_rows_read": n_rows,
        "n_distinct_keys_with_any_acceptance_row": int(n_uniq),
        "emu_overlap_removal_enabled": summaries[0].get("emu_overlap_removal_enabled"),
        "n_electrons_removed_total": n_removed,
        "per_dataset_file_coverage": per_dataset,
        "check4_within_dataset_duplicate_keys": {
            d: v["n_duplicate_keys_within_dataset"] for d, v in per_dataset.items()},
        "trigger_guard_violations_total_across_parts": guard_total,
        "results_by_mode": results,
    }
    out["all_checks_pass"] = bool(
        all(r["check1_rows_with_flags_differing_from_another_file"] == 0
            and r["check1_accepted_but_silent_in_another_dataset_holding_the_event"] == 0
            and r["check2_events_in_two_exclusive_sets"] == 0
            and r["check2_accepted_events_in_no_exclusive_set"] == 0
            and all(v == 0 for v in r["check3_accepted_but_not_read_from_own_files"].values())
            for r in results.values())
        and all(v["n_duplicate_keys_within_dataset"] == 0 for v in per_dataset.values())
        and guard_total == 0)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nall_checks_pass = {out['all_checks_pass']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
