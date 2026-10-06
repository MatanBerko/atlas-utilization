#!/usr/bin/env python
"""
E3: the closure test on one run, one file at a time.

For one (dataset, era, file index) it keeps the golden-JSON events of ONE
run and evaluates ALL FOUR acceptances on every one of them -- NOT only
the events whose own dataset's trigger fired, which is what the production
driver does. That is the whole point: the same collision has to get the
same four flags whichever dataset's copy of the file it was read from.

Both DoubleEG threshold modes are evaluated in the same pass, so the
closure result does not depend on which one is eventually chosen.

Writes, per file:
  keys_<tag>.npz      every golden (run, lumi, event) of the target run in
                      this file, as a structured array -- the input to the
                      "was it read from its own dataset's files" and
                      "within-dataset duplicates" checks.
  accepted_<tag>.csv  one row per event with at least one acceptance in at
                      least one mode: the key, the four flags in each mode,
                      and the attributed (exclusive) dataset in each mode.
  summary_<tag>.json  counts, cutflow and guard violations.

Usage:
    python closure_run.py --dataset DoubleEG --era G --file-index 3 \
        --run 281707 --out-dir /storage/.../closure/parts
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import awkward as ak  # noqa: E402
import numpy as np  # noqa: E402

from services.parsing.validated_runs import ValidatedRunsFilter, apply_validated_runs_filter  # noqa: E402
from studies.cms_datasets.cluster import run_dataset_on_file as drv  # noqa: E402
from studies.cms_datasets.electron_prep.common import record_for  # noqa: E402
from studies.m0m1j0_cms import selection  # noqa: E402

KEY_DTYPE = np.dtype([("run", "u4"), ("lumi", "u4"), ("event", "u8")])
MODES = ("leading_only", "both")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, choices=drv.DELIVERY_VETO_ORDER_4)
    p.add_argument("--era", required=True, choices=["G", "H"])
    p.add_argument("--file-index", type=int, required=True)
    p.add_argument("--run", type=int, required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--validated-runs-json", default=drv.DEFAULT_VALIDATED_RUNS_JSON)
    p.add_argument("--no-emu-overlap-removal", action="store_true")
    args = p.parse_args()

    t0 = time.time()
    tag = f"{args.dataset}_{args.era}_{args.file_index}"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    record_id = record_for(args.dataset, args.era)
    needed_hlt = sorted({p_ for paths in drv.MATCHED4_TRIGGER_PATHS.values() for p_ in paths})
    required = list(drv.BASE_OBJECT_BRANCHES) + needed_hlt + list(drv.MATCHED_MODE_EXTRA_BRANCHES)

    url = drv.resolve_file_url(record_id, args.file_index)
    print(f"[{tag}] {url}", flush=True)
    events, branch_titles = drv.read_events(url, required, return_titles=True)
    n_read = len(events)

    validated = ValidatedRunsFilter(args.validated_runs_json)
    events, golden_stats = apply_validated_runs_filter(events, validated)
    n_golden = len(events)

    in_run = ak.to_numpy(events.run == args.run)
    events = events[in_run]
    n_in_run = len(events)
    print(f"[{tag}] read {n_read} -> golden {n_golden} -> run {args.run}: {n_in_run}",
          flush=True)

    keys = np.zeros(n_in_run, dtype=KEY_DTYPE)
    if n_in_run:
        keys["run"] = ak.to_numpy(events.run).astype(np.uint32)
        keys["lumi"] = ak.to_numpy(events.luminosityBlock).astype(np.uint32)
        keys["event"] = ak.to_numpy(events.event).astype(np.uint64)
    np.savez_compressed(out_dir / f"keys_{tag}.npz", keys=keys)

    summary = {
        "dataset": args.dataset, "era": args.era, "file_index": args.file_index,
        "record_id": record_id, "file_url": url, "target_run": args.run,
        "git_commit": drv.git_commit_hash(REPO_ROOT),
        "n_read": n_read, "n_after_golden_json": n_golden, "n_in_target_run": n_in_run,
        "emu_overlap_removal_enabled": not args.no_emu_overlap_removal,
    }

    if n_in_run == 0:
        summary["note"] = "no golden events of the target run in this file"
        (out_dir / f"accepted_{tag}.csv").write_text(
            "run,lumi,event,source_dataset," + ",".join(
                f"{m}_{l}" for m in MODES for l in drv.DELIVERY_VETO_ORDER_4)
            + "," + ",".join(f"{m}_attributed" for m in MODES) + "\n", encoding="utf-8")
        (out_dir / f"summary_{tag}.json").write_text(json.dumps(summary, indent=2),
                                                     encoding="utf-8")
        print(f"[{tag}] nothing to do ({time.time() - t0:.0f}s)")
        return

    trigobj = ak.zip({
        "pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
        "id": events.TrigObj_id, "filterBits": events.TrigObj_filterBits,
    })
    summary["trigobj_title_check"] = drv.assert_trigobj_bit_meanings(branch_titles)

    muons = selection.select_muons(events)
    electrons_pre = selection.select_electrons(events)
    electrons, n_removed, _m = drv.remove_electrons_overlapping_muons(
        electrons_pre, muons, dr_max=drv.EMU_OVERLAP_DR_MAX,
        enabled=not args.no_emu_overlap_removal)
    summary["n_electrons_removed"] = int(n_removed.sum())

    acc_by_mode = {}
    attributed_by_mode = {}
    for mode in MODES:
        acc = drv.evaluate_four_acceptances(events, muons, electrons, trigobj, mode)
        acc_by_mode[mode] = {l: acc[l]["accepted"] for l in drv.DELIVERY_VETO_ORDER_4}
        attributed_by_mode[mode] = drv.attribute_to_exclusive_dataset(acc)
        summary.setdefault("cutflow_per_dataset", {})[mode] = {
            l: acc[l]["cutflow"] for l in drv.DELIVERY_VETO_ORDER_4}
        summary.setdefault("n_accepted_per_dataset", {})[mode] = {
            l: int(acc[l]["accepted"].sum()) for l in drv.DELIVERY_VETO_ORDER_4}
        summary.setdefault("n_attributed_per_dataset", {})[mode] = {
            l: int((attributed_by_mode[mode] == l).sum()) for l in drv.DELIVERY_VETO_ORDER_4}
        if mode == MODES[0]:
            summary["trigger_guard_violations"] = {
                "electrons_bit16": drv.count_trigger_guard_violations(
                    acc["DoubleEG"]["bookkeeping"], trigobj, drv.TRIGOBJ_ELECTRON_ID),
                "electrons_bit32": drv.count_trigger_guard_violations(
                    acc["MuonEG"]["bookkeeping"], trigobj, drv.TRIGOBJ_ELECTRON_ID),
                "muons_bit1": drv.count_trigger_guard_violations(
                    drv.trigobj_best_match(muons, trigobj, drv.TRIGOBJ_MUON_ID,
                                           drv.TRIGOBJ_BIT_TRKISOVVL),
                    trigobj, drv.TRIGOBJ_MUON_ID),
                "muons_bit2": drv.count_trigger_guard_violations(
                    drv.trigobj_best_match(muons, trigobj, drv.TRIGOBJ_MUON_ID,
                                           drv.TRIGOBJ_BIT_ISO),
                    trigobj, drv.TRIGOBJ_MUON_ID),
            }
            summary["trigger_guard_violations"]["total"] = int(
                sum(summary["trigger_guard_violations"].values()))

    any_accepted = np.zeros(n_in_run, dtype=bool)
    for mode in MODES:
        for l in drv.DELIVERY_VETO_ORDER_4:
            any_accepted |= acc_by_mode[mode][l]
    idx = np.flatnonzero(any_accepted)
    summary["n_events_accepted_in_at_least_one_mode"] = int(idx.size)

    header = ("run,lumi,event,source_dataset,"
              + ",".join(f"{m}_{l}" for m in MODES for l in drv.DELIVERY_VETO_ORDER_4)
              + "," + ",".join(f"{m}_attributed" for m in MODES) + "\n")
    with open(out_dir / f"accepted_{tag}.csv", "w", encoding="utf-8", newline="") as fh:
        fh.write(header)
        runs = keys["run"]
        lumis = keys["lumi"]
        evts = keys["event"]
        for i in idx:
            flags = ",".join("1" if acc_by_mode[m][l][i] else "0"
                             for m in MODES for l in drv.DELIVERY_VETO_ORDER_4)
            attr = ",".join(attributed_by_mode[m][i] or "NONE" for m in MODES)
            fh.write(f"{runs[i]},{lumis[i]},{evts[i]},{args.dataset},{flags},{attr}\n")

    summary["elapsed_sec"] = round(time.time() - t0, 1)
    (out_dir / f"summary_{tag}.json").write_text(json.dumps(summary, indent=2),
                                                 encoding="utf-8")
    print(f"[{tag}] accepted-in-some-mode {idx.size} of {n_in_run} "
          f"({summary['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
