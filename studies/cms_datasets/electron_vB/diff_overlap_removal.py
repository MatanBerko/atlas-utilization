#!/usr/bin/env python
"""
E1(b): list every event that differs between an overlap-removal ON run and
an overlap-removal OFF run of the same files.

Reads the two runs' per-event debug dumps (debug_events.csv, written by
run_dataset_on_file.py --population matched4 --debug-event-dump) and
reports, per (run, lumi, event):
  * accepted in ON but not OFF, and vice versa;
  * accepted in both but with a different final-state label (old FS -> new
    FS), with the number of electrons the removal took out;
  * accepted in both but with a different acceptance-flag set or a
    different exclusive flag.

Every difference must trace to a removed electron: a difference in an
event with n_electrons_removed == 0 is reported separately and is a STOP
condition.

Usage:
    python diff_overlap_removal.py --on-root /storage/.../pilot_on \
        --off-root /storage/.../pilot_off --jobs DoubleMuon:0,SingleMuon:3 \
        --out evidence/E1b_overlap_diff.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402

FLAG_COLS = [f"acc_{l}" for l in DELIVERY_VETO_ORDER_4] + ["exclusive"]


def load_dump(path: Path) -> dict:
    rows = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (int(row["run"]), int(row["luminosityBlock"]), int(row["event"]))
            rows[key] = row
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--on-root", required=True)
    p.add_argument("--off-root", required=True)
    p.add_argument("--jobs", required=True, help="comma-separated Dataset:jobindex")
    p.add_argument("--out", required=True)
    p.add_argument("--max-listed", type=int, default=5000)
    args = p.parse_args()

    per_job = {}
    totals = {"n_accepted_on": 0, "n_accepted_off": 0,
              "n_only_on": 0, "n_only_off": 0,
              "n_final_state_changed": 0, "n_flags_changed": 0,
              "n_differences_without_a_removed_electron": 0,
              "n_events_with_an_electron_removed": 0,
              "n_electrons_removed": 0}
    listed = []
    for spec in args.jobs.split(","):
        dataset, idx = spec.split(":")
        on_path = Path(args.on_root) / dataset / f"job_{idx}" / "debug_events.csv"
        off_path = Path(args.off_root) / dataset / f"job_{idx}" / "debug_events.csv"
        if not on_path.exists() or not off_path.exists():
            per_job[spec] = {"status": "MISSING DUMP",
                             "on_exists": on_path.exists(), "off_exists": off_path.exists()}
            continue
        on_rows = load_dump(on_path)
        off_rows = load_dump(off_path)
        only_on = sorted(set(on_rows) - set(off_rows))
        only_off = sorted(set(off_rows) - set(on_rows))
        fs_changed = []
        flags_changed = []
        no_removal = []
        n_removed_events = 0
        n_removed = 0
        for key in sorted(set(on_rows) & set(off_rows)):
            a, b = on_rows[key], off_rows[key]
            nrem = int(a["n_electrons_removed"])
            if nrem:
                n_removed_events += 1
                n_removed += nrem
            fs_diff = a["final_state"] != b["final_state"]
            flag_diff = any(a[c] != b[c] for c in FLAG_COLS)
            if fs_diff:
                fs_changed.append({"key": key, "old_fs": b["final_state"],
                                   "new_fs": a["final_state"], "electrons_removed": nrem})
            if flag_diff:
                flags_changed.append({
                    "key": key, "electrons_removed": nrem,
                    "off": {c: b[c] for c in FLAG_COLS},
                    "on": {c: a[c] for c in FLAG_COLS}})
            if (fs_diff or flag_diff) and nrem == 0:
                no_removal.append({"key": key, "old_fs": b["final_state"],
                                   "new_fs": a["final_state"],
                                   "off": {c: b[c] for c in FLAG_COLS},
                                   "on": {c: a[c] for c in FLAG_COLS}})
        per_job[spec] = {
            "status": "ok",
            "n_accepted_on": len(on_rows), "n_accepted_off": len(off_rows),
            "n_only_on": len(only_on), "n_only_off": len(only_off),
            "only_on_examples": [list(k) for k in only_on[:20]],
            "only_off_examples": [list(k) for k in only_off[:20]],
            "n_final_state_changed": len(fs_changed),
            "n_flags_changed": len(flags_changed),
            "n_events_with_an_electron_removed": n_removed_events,
            "n_electrons_removed": n_removed,
            "n_differences_without_a_removed_electron": len(no_removal),
            "differences_without_a_removed_electron": no_removal[:20],
        }
        totals["n_accepted_on"] += len(on_rows)
        totals["n_accepted_off"] += len(off_rows)
        totals["n_only_on"] += len(only_on)
        totals["n_only_off"] += len(only_off)
        totals["n_final_state_changed"] += len(fs_changed)
        totals["n_flags_changed"] += len(flags_changed)
        totals["n_differences_without_a_removed_electron"] += len(no_removal)
        totals["n_events_with_an_electron_removed"] += n_removed_events
        totals["n_electrons_removed"] += n_removed
        for d in fs_changed:
            if len(listed) < args.max_listed:
                listed.append({"job": spec, **{k: (list(v) if k == "key" else v)
                                               for k, v in d.items()}})
        print(f"{spec}: on={len(on_rows)} off={len(off_rows)} "
              f"only_on={len(only_on)} only_off={len(only_off)} "
              f"fs_changed={len(fs_changed)} flags_changed={len(flags_changed)} "
              f"unexplained={len(no_removal)}")

    out = {
        "what": "E1(b): overlap removal ON vs OFF, event by event",
        "on_root": args.on_root, "off_root": args.off_root,
        "jobs": args.jobs.split(","),
        "totals": totals,
        "every_difference_traces_to_a_removed_electron":
            totals["n_differences_without_a_removed_electron"] == 0,
        "per_job": per_job,
        "changed_events": listed,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\ntotals: {json.dumps(totals)}")
    print(f"every difference traces to a removed electron: "
          f"{out['every_difference_traces_to_a_removed_electron']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
