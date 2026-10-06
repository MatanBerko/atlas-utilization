#!/usr/bin/env python
"""
E2 / E4 summary: fold the per-job `job_metadata.json` files of one pilot run
into one evidence JSON.

Reports, per dataset and in total:
  * the cutflow -- events read, golden-JSON, own trigger, acceptance,
    exclusive, and the Version B (rare4) rejection;
  * each of the four datasets' acceptance counts as evaluated inside this
    dataset's own triggered events (the de-duplication inputs);
  * D4's interpretation-check count and the shared-trigger-object count;
  * the per-object matching bookkeeping summary;
  * E4: the trigger-guard violation total across every job;
  * the overlap-removal counts, and the ordering-choice diagnostic;
  * every final-state label the pilot produced, which Step C's check C7
    then compares name-for-name against upstream's own naming code.

Usage:
    python summarize_pilot.py --root /storage/.../runs_matched4_pilot_on_<date> \
        --out evidence/E2_pilot_summary.json \
        --final-states-out evidence/pilot_final_states.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402

CUTFLOW_KEYS = ("n_read", "n_after_golden_json", "n_after_trigger", "n_after_gate",
                "n_exclusive")


# Fields that are CONSTANTS, not counts: summing them across jobs would be
# meaningless (e.g. four jobs would report a 30 GeV threshold as 120).
NON_ADDITIVE = ("offline_pt_min_gev", "threshold_mode", "emu_overlap_removal_dr_max")


def _add(dst: dict, src: dict):
    for k, v in (src or {}).items():
        if k in NON_ADDITIVE:
            dst[k] = v
            continue
        if isinstance(v, bool):
            dst[k] = bool(dst.get(k, True) and v)
        elif isinstance(v, (int, float)):
            dst[k] = dst.get(k, 0) + v
        elif isinstance(v, dict):
            _add(dst.setdefault(k, {}), v)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--final-states-out", default=None)
    args = p.parse_args()

    root = Path(args.root)
    per_dataset = {}
    final_states = set()
    guard_total = 0
    n_jobs = 0
    modes_seen = set()
    removal_seen = set()

    for dataset in DELIVERY_VETO_ORDER_4:
        d_dir = root / dataset
        if not d_dir.exists():
            continue
        block = {"n_jobs": 0, "cutflow": {}, "acceptance_counts": {}, "fired_counts": {},
                 "cutflow_per_dataset": {}, "interpretation": {}, "bookkeeping": {},
                 "overlap_removal": {}, "version_b": {}, "light_jet_multiplicity": {},
                 "guard_violations": {}, "jobs": []}
        for job in sorted(d_dir.glob("job_*")):
            f = job / "job_metadata.json"
            if not f.exists():
                continue
            m = json.loads(f.read_text(encoding="utf-8"))
            n_jobs += 1
            block["n_jobs"] += 1
            for k in CUTFLOW_KEYS:
                block["cutflow"][k] = block["cutflow"].get(k, 0) + int(m[k])
            d4 = m.get("matched4_diagnostics") or {}
            modes_seen.add(d4.get("doubleeg_threshold_mode"))
            removal_seen.add(d4.get("emu_overlap_removal_enabled"))
            _add(block["acceptance_counts"], d4.get("acceptance_counts"))
            _add(block["fired_counts"], d4.get("fired_counts"))
            _add(block["cutflow_per_dataset"], d4.get("cutflow_per_dataset"))
            _add(block["interpretation"], {
                k: v for k, v in (d4.get("doubleeg_interpretation_checks") or {}).items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)})
            for which, bk in (d4.get("bookkeeping_summary") or {}).items():
                tgt = block["bookkeeping"].setdefault(which, {})
                tgt["n_offline_objects"] = tgt.get("n_offline_objects", 0) + bk["n_offline_objects"]
                tgt["n_matched"] = tgt.get("n_matched", 0) + bk["n_matched"]
                _add(tgt.setdefault("matched_trigobj_id_counts", {}),
                     bk.get("matched_trigobj_id_counts"))
                if bk.get("matched_dr_max") is not None:
                    tgt["matched_dr_max"] = max(tgt.get("matched_dr_max", 0.0),
                                                bk["matched_dr_max"])
            for k in ("n_electrons_removed_total", "n_events_with_an_electron_removed",
                      "n_events_jet_cleaning_order_would_matter"):
                block["overlap_removal"][k] = block["overlap_removal"].get(k, 0) + int(d4.get(k, 0))
            gv = d4.get("trigger_guard_violations") or {}
            _add(block["guard_violations"], gv)
            guard_total += int(gv.get("total", 0))
            r4 = m.get("rare4_diagnostics") or {}
            for k in ("n_accepted_events_before_rare4_rule", "n_rejected_gt4_lepton_bjet",
                      "n_kept_le4_lepton_bjet", "n_hidden_cases"):
                if k in r4:
                    block["version_b"][k] = block["version_b"].get(k, 0) + int(r4[k])
            _add(block["light_jet_multiplicity"], d4.get("light_jet_multiplicity_accepted_events"))
            final_states.update((r4.get("final_state_label_event_counts_inclusive") or {}).keys())
            block["jobs"].append({
                "job": job.name, "record_id": m["record_id"], "file_index": m["file_index"],
                "n_read": m["n_read"], "n_after_trigger": m["n_after_trigger"],
                "n_after_gate": m["n_after_gate"], "n_exclusive": m["n_exclusive"],
                "n_rejected_version_b": r4.get("n_rejected_gt4_lepton_bjet"),
                "elapsed_sec": m.get("elapsed_sec"),
            })
        per_dataset[dataset] = block

    out = {
        "what": "E2/E4 pilot summary, folded from the per-job metadata",
        "root": str(root),
        "n_jobs": n_jobs,
        "doubleeg_threshold_mode": sorted(x for x in modes_seen if x),
        "emu_overlap_removal_enabled": sorted(str(x) for x in removal_seen),
        "E4_trigger_guard_violations_total": guard_total,
        "n_distinct_final_states_version_b": len(final_states),
        "per_dataset": per_dataset,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"jobs: {n_jobs}; mode={out['doubleeg_threshold_mode']}; "
          f"removal={out['emu_overlap_removal_enabled']}")
    print(f"E4 trigger-guard violations total: {guard_total}")
    for dataset, b in per_dataset.items():
        c = b["cutflow"]
        print(f"  {dataset:12s} jobs={b['n_jobs']} read={c.get('n_read',0):10d} "
              f"trig={c.get('n_after_trigger',0):9d} accepted={c.get('n_after_gate',0):8d} "
              f"exclusive={c.get('n_exclusive',0):8d} "
              f"vB_rejected={b['version_b'].get('n_rejected_gt4_lepton_bjet',0)}")
    print(f"distinct Version B final states: {len(final_states)}")
    print(f"wrote {args.out}")
    if args.final_states_out:
        Path(args.final_states_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.final_states_out).write_text(json.dumps({
            "what": "every Version B final-state label the pilot produced, for check C7",
            "root": str(root), "n_final_states": len(final_states),
            "final_states": sorted(final_states)}, indent=2), encoding="utf-8")
        print(f"wrote {args.final_states_out}")


if __name__ == "__main__":
    main()
