#!/usr/bin/env python
"""
Step C3: confirm every file of the full production has exactly one
COMPLETE output, and fold the per-job metadata into the production table.

"Complete" means the job directory holds `job_metadata.json` AND all eight
shard files (normal / top4 / nonjet4 / rare4, each inclusive and
exclusive). A directory with a metadata file but a missing shard is
reported as INCOMPLETE, not as done -- that is the case a plain file count
would miss.

Reports per dataset: files expected, files complete, files missing, files
incomplete, events read, events after the validated-runs (golden JSON)
filter, events after the dataset's own trigger, accepted, exclusive,
rejected by the Version B rule, electrons removed by the overlap removal,
and trigger-guard violations.

Exits non-zero if anything is missing or incomplete, so it can gate the
delivery build.

Usage:
    python check_production_complete.py \
        --runs-root /storage/.../runs_matched4_full_20261007 \
        --out evidence/C3_production.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402
from studies.cms_datasets.cluster.datasets_records import DATASETS  # noqa: E402

EXPECTED_TOTALS = {d.label: d.expected_files_g_plus_h for d in DATASETS}
SHARDS = [f"dataset_shard_{v}{w}.sqlite"
          for v in ("", "top4_", "nonjet4_", "rare4_")
          for w in ("inclusive", "exclusive")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs-root", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    root = Path(args.runs_root)
    report = {"what": "Step C3: full-production completeness and counts",
              "runs_root": str(root), "per_dataset": {}}
    all_ok = True
    grand = {k: 0 for k in ("n_read", "n_after_golden_json", "n_after_trigger",
                            "n_accepted", "n_exclusive", "n_rejected_version_b",
                            "n_electrons_removed", "n_guard_violations")}

    for dataset in DELIVERY_VETO_ORDER_4:
        index_path = root / f"{dataset}_index.json"
        if not index_path.exists():
            raise SystemExit(f"STOP: missing {index_path}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        expected = EXPECTED_TOTALS[dataset]
        if len(index) != expected:
            raise SystemExit(f"STOP: {dataset} index has {len(index)} entries, "
                             f"expected {expected}")

        missing, incomplete = [], []
        agg = {k: 0 for k in grand}
        n_complete = 0
        elapsed = []
        for job_key in sorted(index, key=int):
            d = root / dataset / f"job_{job_key}"
            meta_f = d / "job_metadata.json"
            if not meta_f.exists():
                missing.append(int(job_key))
                continue
            absent = [s for s in SHARDS if not (d / s).exists()]
            if absent:
                incomplete.append({"job": int(job_key), "missing_shards": absent})
                continue
            m = json.loads(meta_f.read_text(encoding="utf-8"))
            n_complete += 1
            agg["n_read"] += int(m["n_read"])
            agg["n_after_golden_json"] += int(m["n_after_golden_json"])
            agg["n_after_trigger"] += int(m["n_after_trigger"])
            agg["n_accepted"] += int(m["n_after_gate"])
            agg["n_exclusive"] += int(m["n_exclusive"])
            r4 = m.get("rare4_diagnostics") or {}
            agg["n_rejected_version_b"] += int(r4.get("n_rejected_gt4_lepton_bjet", 0))
            d4 = m.get("matched4_diagnostics") or {}
            agg["n_electrons_removed"] += int(d4.get("n_electrons_removed_total", 0))
            agg["n_guard_violations"] += int(
                (d4.get("trigger_guard_violations") or {}).get("total", 0))
            if m.get("elapsed_sec"):
                elapsed.append(float(m["elapsed_sec"]))
            # sanity: the settings this production is supposed to have run with
            report.setdefault("settings_seen", {}).setdefault(
                "doubleeg_threshold_mode", set()).add(d4.get("doubleeg_threshold_mode"))
            report["settings_seen"].setdefault("emu_overlap_removal_dr_max", set()).add(
                d4.get("emu_overlap_removal_dr_max"))
            report["settings_seen"].setdefault("emu_overlap_removal_enabled", set()).add(
                d4.get("emu_overlap_removal_enabled"))

        ok = (not missing) and (not incomplete) and n_complete == expected
        all_ok = all_ok and ok
        report["per_dataset"][dataset] = {
            "files_expected": expected, "files_complete": n_complete,
            "files_missing": missing, "n_files_missing": len(missing),
            "files_incomplete": incomplete, "n_files_incomplete": len(incomplete),
            "complete": ok,
            "elapsed_sec_min": round(min(elapsed), 1) if elapsed else None,
            "elapsed_sec_max": round(max(elapsed), 1) if elapsed else None,
            "elapsed_sec_total": round(sum(elapsed), 1) if elapsed else None,
            **agg,
        }
        for k in grand:
            grand[k] += agg[k]
        print(f"{dataset:12s} {n_complete:4d}/{expected:<4d} complete  "
              f"missing {len(missing):3d}  incomplete {len(incomplete):3d}  "
              f"read {agg['n_read']:12,}  accepted {agg['n_accepted']:10,}  "
              f"exclusive {agg['n_exclusive']:10,}  guard {agg['n_guard_violations']}")
        if missing:
            print(f"             missing job indices: {missing[:20]}"
                  f"{' ...' if len(missing) > 20 else ''}")
        if incomplete:
            print(f"             incomplete: {incomplete[:5]}")

    report["totals"] = grand
    report["settings_seen"] = {k: sorted(str(x) for x in v)
                               for k, v in report.get("settings_seen", {}).items()}
    report["all_complete"] = all_ok
    report["n_files_expected_total"] = sum(EXPECTED_TOTALS[d] for d in DELIVERY_VETO_ORDER_4)
    report["n_files_complete_total"] = sum(
        report["per_dataset"][d]["files_complete"] for d in DELIVERY_VETO_ORDER_4)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nTOTAL {report['n_files_complete_total']}/{report['n_files_expected_total']} "
          f"files complete; settings seen: {report['settings_seen']}")
    print(f"guard violations across the whole production: {grand['n_guard_violations']}")
    print(f"all_complete = {all_ok}")
    print(f"wrote {args.out}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
