#!/usr/bin/env python
"""
CMS MC full run (17 Oct 2026), FULL_RUN_PLAN.md §6 step 4: production audit.

For every line of every mapping file: the job directory exists, its
job_metadata.json is present (the driver writes it as its LAST step), the
PBS log's /usr/bin/time block says exit 0, and the per-file Sigma-w
self-check (|sum genWeight - Runs genEventSumw| / Runs genEventSumw <= 1e-6,
the builder's D4 tolerance) passes. Expected: exactly ONE Sigma-w failure,
75589 file 98 (Matan's decision, option A). Also sums CPU time, wall time,
peak memory, events read/stored and negative-weight counts per record.

Read-only. Writes one JSON.

Run (as a PBS job):
    python studies/cms_mc_weights_v3/fullrun/audit_production.py \
        --work /storage/.../work/fullrun_20261017 --out <work>/evidence/production_audit.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SIGMA_W_TOLERANCE = 1e-6
EXPECTED_SIGMA_W_FAILURES = {(75589, 98)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    w = Path(args.work)
    jobids = {}
    for line in (w / "jobids.txt").read_text().splitlines():
        rid, jid, n, wt = line.split()
        jobids[rid] = {"array": jid, "n": int(n), "walltime": wt}

    records, problems, sw_fail = {}, [], []
    for rid, info in jobids.items():
        agg = {"array": info["array"], "expected": info["n"], "ok": 0, "missing_metadata": [],
               "nonzero_exit": [], "no_log": [], "sigma_w_failures": [],
               "events_read": 0, "events_stored": 0, "n_negative_stored": 0,
               "cpu_seconds_driver": 0.0, "max_wall_s": 0.0, "max_wall_file": None,
               "max_rss_gb": 0.0, "output_bytes": 0, "n_output_files": 0,
               "sum_runs_gen_event_sumw_passing": 0.0, "sum_genweight_stored_passing": 0.0, "walltime_request": info["walltime"]}
        for line in (w / "mappings" / f"mapping_{rid}.txt").read_text().splitlines():
            idx, r, fidx = line.split()
            jd = w / "runs" / f"record{rid}" / f"job_{fidx}"
            err = w / "logs" / rid / f"f_{idx}.err"
            text = err.read_text(errors="replace") if err.exists() else None
            if text is None:
                agg["no_log"].append(int(fidx))
            else:
                m = re.search(r"Exit status: (\d+)", text)
                if not m or int(m.group(1)) != 0:
                    agg["nonzero_exit"].append({"file_index": int(fidx), "array_index": int(idx),
                                                "exit": int(m.group(1)) if m else None,
                                                "tail": text.strip().splitlines()[-5:]})
                r_ = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
                if r_:
                    agg["max_rss_gb"] = max(agg["max_rss_gb"], int(r_.group(1)) / 1024 / 1024)
            mp = jd / "job_metadata.json"
            if not mp.exists():
                agg["missing_metadata"].append(int(fidx))
                continue
            meta = json.loads(mp.read_text())
            sw = meta["mc_sigma_w_self_check"]
            rel = abs(sw["file_sum_genweight"] - sw["runs_gen_event_sumw"]) / abs(sw["runs_gen_event_sumw"])
            if rel > SIGMA_W_TOLERANCE:
                agg["sigma_w_failures"].append({"file_index": int(fidx), "rel_diff": rel,
                                                "n_read": meta["n_read"],
                                                "runs_gen_event_count": sw.get("runs_gen_event_count")})
                sw_fail.append((int(rid), int(fidx)))
            else:
                agg["sum_runs_gen_event_sumw_passing"] += sw["runs_gen_event_sumw"]
            mc = meta.get("mc_diagnostics") or {}
            if rel <= SIGMA_W_TOLERANCE:
                agg["sum_genweight_stored_passing"] += (mc.get("genweight_stored_events") or {}).get("sum", 0.0)
            agg["events_read"] += meta["n_read"]
            agg["events_stored"] += mc.get("n_stored", meta.get("n_after_gate", 0))
            agg["n_negative_stored"] += (mc.get("genweight_stored_events") or {}).get("n_negative", 0)
            agg["cpu_seconds_driver"] += meta["elapsed_sec"]
            if meta["elapsed_sec"] > agg["max_wall_s"]:
                agg["max_wall_s"], agg["max_wall_file"] = meta["elapsed_sec"], int(fidx)
            outs = [p for p in jd.iterdir() if p.is_file()]
            agg["output_bytes"] += sum(p.stat().st_size for p in outs)
            agg["n_output_files"] += len(outs)
            if text is not None and not any(e["file_index"] == int(fidx) for e in agg["nonzero_exit"]):
                agg["ok"] += 1
        agg["negative_weight_fraction_stored"] = (agg["n_negative_stored"] / agg["events_stored"]
                                                  if agg["events_stored"] else None)
        records[rid] = agg
        for k in ("missing_metadata", "nonzero_exit", "no_log"):
            if agg[k]:
                problems.append({"record": rid, k: agg[k]})

    unexpected_sw = sorted(set(sw_fail) - EXPECTED_SIGMA_W_FAILURES)
    missing_expected_sw = sorted(EXPECTED_SIGMA_W_FAILURES - set(sw_fail))
    out = {
        "records": records,
        "totals": {
            "jobs_expected": sum(r["expected"] for r in records.values()),
            "jobs_ok": sum(r["ok"] for r in records.values()),
            "events_read": sum(r["events_read"] for r in records.values()),
            "events_stored": sum(r["events_stored"] for r in records.values()),
            "cpu_hours_driver": sum(r["cpu_seconds_driver"] for r in records.values()) / 3600,
            "max_wall_s": max(r["max_wall_s"] for r in records.values()),
            "max_rss_gb": max(r["max_rss_gb"] for r in records.values()),
            "output_gb": sum(r["output_bytes"] for r in records.values()) / 1e9,
            "n_output_files": sum(r["n_output_files"] for r in records.values()),
        },
        "problems": problems,
        "sigma_w_failures": sw_fail,
        "unexpected_sigma_w_failures": unexpected_sw,
        "expected_sigma_w_failure_missing": missing_expected_sw,
        "verdict": "OK" if not problems and not unexpected_sw and not missing_expected_sw else "PROBLEMS",
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "records"}, indent=1))
    for rid, r in records.items():
        print(f"{rid}: ok {r['ok']}/{r['expected']} read {r['events_read']:,} cpu {r['cpu_seconds_driver']/3600:.2f} h "
              f"max wall {r['max_wall_s']:.0f} s rss {r['max_rss_gb']:.2f} GB sw_fail {[f['file_index'] for f in r['sigma_w_failures']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
