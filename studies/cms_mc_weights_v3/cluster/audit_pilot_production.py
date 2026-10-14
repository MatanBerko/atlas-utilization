#!/usr/bin/env python
"""
Pilot Part 2: check every file of every pilot sample completed cleanly.

For each expected file it checks that
  * `job_metadata.json` exists -- the driver writes it only as its very last
    step, so its presence is the completion signal;
  * all eight shard files are present;
  * the job really ran in `--is-mc` mode;
  * the per-file Sigma-w self-check passed
    (|sum(genWeight) - Runs.genEventSumw| / genEventSumw <= 1e-6).

and aggregates, per sample: events read, events stored, the stored-only-
because-of-Ele27 count, the stored count per acceptance flag, coverage-cap
incidence and the largest cap scale factor, the sum of `genEventSumw` over the
surviving files, and total CPU hours.

Files that fail are listed with their reason and printed as a ready-to-use
`--file-indices` list for a single resubmit.

Read-only with respect to the run output. Writes one JSON into --out.

Run:
    python studies/cms_mc_weights_v3/cluster/audit_pilot_production.py \
        --runs-dir <work>/runs --out <work>/evidence/pilot_production_audit.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_datasets.cluster.run_dataset_on_file import (  # noqa: E402
    DELIVERY_VETO_ORDER_4,
)
from studies.cms_mc_weights_v3.cluster.measure_pilot_inputs import (  # noqa: E402
    PILOT_RECORDS,
)

SHARDS = (
    "dataset_shard_inclusive.sqlite", "dataset_shard_exclusive.sqlite",
    "dataset_shard_top4_inclusive.sqlite", "dataset_shard_top4_exclusive.sqlite",
    "dataset_shard_nonjet4_inclusive.sqlite", "dataset_shard_nonjet4_exclusive.sqlite",
    "dataset_shard_rare4_inclusive.sqlite", "dataset_shard_rare4_exclusive.sqlite",
)


def audit_file(job_dir: pathlib.Path) -> tuple[list, dict | None]:
    problems = []
    meta_path = job_dir / "job_metadata.json"
    if not meta_path.exists():
        return ["no job_metadata.json -- the job did not reach its last step"], None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"job_metadata.json unreadable: {type(exc).__name__}: {exc}"], None
    missing = [s for s in SHARDS if not (job_dir / s).exists()]
    if missing:
        problems.append(f"missing shard file(s): {missing}")
    if not meta.get("is_mc"):
        problems.append("job_metadata says this is not an --is-mc job")
    check = meta.get("mc_sigma_w_self_check")
    if not check:
        problems.append("no mc_sigma_w_self_check in job_metadata")
    elif not check.get("passes"):
        problems.append(
            f"Sigma-w self-check FAILED: relative difference "
            f"{check.get('relative_difference')} > {check.get('tolerance')}")
    return problems, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs = pathlib.Path(args.runs_dir)
    out = {
        "what": "CMS MC pilot Part 2: per-file completeness and Sigma-w audit",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runs_dir": str(runs),
        "records": {},
    }
    grand = {"expected": 0, "succeeded": 0, "failed": 0, "read": 0, "stored": 0,
             "ele27_only": 0, "cpu_seconds": 0.0, "capped_signatures": 0}

    for rid, info in PILOT_RECORDS.items():
        n_expected = info["expected_files"]
        ok, failed = [], []
        agg = {
            "events_read": 0, "events_after_trigger": 0, "events_stored": 0,
            "stored_only_via_ele27": 0, "stored_ele27_candidate": 0,
            "stored_by_acceptance_flag": {k: 0 for k in DELIVERY_VETO_ORDER_4},
            "cpu_seconds": 0.0, "sum_runs_gen_event_sumw_over_ok_files": 0.0,
            "n_capped_signatures": 0, "max_cap_weight_scale": 0.0,
            "slowest_file": None, "slowest_seconds": 0.0,
        }
        for file_index in range(n_expected):
            job_dir = runs / f"record{rid}" / f"job_{file_index}"
            problems, meta = audit_file(job_dir)
            if problems:
                failed.append({"file_index": file_index, "problems": problems})
                continue
            ok.append(file_index)
            mc = meta["mc_diagnostics"]
            agg["events_read"] += meta["n_read"]
            agg["events_after_trigger"] += meta["n_after_trigger"]
            agg["events_stored"] += meta["n_after_gate"]
            agg["stored_only_via_ele27"] += mc["n_stored_only_ele27_candidate"]
            agg["stored_ele27_candidate"] += mc["n_stored_ele27_candidate"]
            for flag in DELIVERY_VETO_ORDER_4:
                agg["stored_by_acceptance_flag"][flag] += \
                    mc["n_stored_by_acceptance_bit"][flag]
            agg["cpu_seconds"] += meta["elapsed_sec"]
            agg["sum_runs_gen_event_sumw_over_ok_files"] += \
                meta["mc_runs_tree"]["gen_event_sumw"]
            caps = meta.get("mc_capped_signatures_rare4") or {}
            agg["n_capped_signatures"] += len(caps)
            for cap in caps.values():
                agg["max_cap_weight_scale"] = max(
                    agg["max_cap_weight_scale"], float(cap["weight_scale"]))
            if meta["elapsed_sec"] > agg["slowest_seconds"]:
                agg["slowest_seconds"] = meta["elapsed_sec"]
                agg["slowest_file"] = file_index

        out["records"][rid] = {
            "physics_short": info["physics_short"],
            "expected": n_expected,
            "succeeded": len(ok),
            "failed": len(failed),
            "failed_file_indices": [f["file_index"] for f in failed],
            "resubmit_file_indices_argument": ",".join(
                str(f["file_index"]) for f in failed) or None,
            "failures": failed,
            "aggregate": agg,
        }
        grand["expected"] += n_expected
        grand["succeeded"] += len(ok)
        grand["failed"] += len(failed)
        grand["read"] += agg["events_read"]
        grand["stored"] += agg["events_stored"]
        grand["ele27_only"] += agg["stored_only_via_ele27"]
        grand["cpu_seconds"] += agg["cpu_seconds"]
        grand["capped_signatures"] += agg["n_capped_signatures"]

    out["grand_total"] = grand
    out["all_files_succeeded"] = grand["failed"] == 0
    path = pathlib.Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    hdr = (f"{'rec':>6} {'exp':>4} {'ok':>4} {'bad':>4} {'events read':>14} "
           f"{'stored':>12} {'ele27-only':>11} {'CPU h':>7} {'capped':>7}")
    print(hdr)
    print("-" * len(hdr))
    for rid, rec in out["records"].items():
        a = rec["aggregate"]
        print(f"{rid:>6} {rec['expected']:>4} {rec['succeeded']:>4} "
              f"{rec['failed']:>4} {a['events_read']:>14,} "
              f"{a['events_stored']:>12,} {a['stored_only_via_ele27']:>11,} "
              f"{a['cpu_seconds'] / 3600:>7.2f} {a['n_capped_signatures']:>7}")
    print("-" * len(hdr))
    print(f"{'TOTAL':>6} {grand['expected']:>4} {grand['succeeded']:>4} "
          f"{grand['failed']:>4} {grand['read']:>14,} {grand['stored']:>12,} "
          f"{grand['ele27_only']:>11,} {grand['cpu_seconds'] / 3600:>7.2f} "
          f"{grand['capped_signatures']:>7}")
    print()
    for rid, rec in out["records"].items():
        a = rec["aggregate"]
        print(f"{rid} {rec['physics_short']}:")
        print(f"    stored per acceptance flag: {a['stored_by_acceptance_flag']}")
        print(f"    sum(genEventSumw) over surviving files: "
              f"{a['sum_runs_gen_event_sumw_over_ok_files']:.6e}")
        print(f"    max cap weight scale: {a['max_cap_weight_scale']}   "
              f"slowest file: {a['slowest_file']} at {a['slowest_seconds']:.0f}s")
        if rec["failed"]:
            print(f"    FAILED: {rec['resubmit_file_indices_argument']}")
            for f in rec["failures"]:
                print(f"       file {f['file_index']}: {f['problems']}")
    print(f"\nwrote {path}")
    return 0 if grand["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
