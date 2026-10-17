#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part D: projections for the full MC run.
Arithmetic only -- submits nothing.

Inputs (all measured; committed under evidence/):
  --inputs  fullrun_inputs_20261017.json   per-file event counts, 13 records
  --smoke   smoke_production_20261017.json Part C: file 0 of 10 never-run records
  --pilot   pilot_per_file_20261017.json   the 98 pilot files of 10 Oct

Two run-time projections (Matan's decision, 17 Oct 2026):

REALISTIC (used for the requests). Per-file wall time grows with the number
of final states the file fills (n_fs) and with its events (N):
    t = a + b * n_fs + c * N/1e6,   a, b, c >= 0
fitted by non-negative least squares over all 108 measured files (CENTRAL,
used for CPU hours), and an ENVELOPE = CENTRAL x the largest measured/central
ratio, so the envelope lies above every measured file (used for walltime).
n_fs of an unmeasured file is extrapolated from the record's measured file(s)
at the steepest growth seen in the pilot (FS_PER_DECADE final states per
tenfold increase in events), never below what was measured.

LITERAL (reference only). The pilot's rule applied mechanically: the
record's SLOWEST measured rate (events/s) for every file. Meaningless for
records measured only on a tiny file (fixed start-up cost dominates).

Requests: walltime = max(2 x ENVELOPE worst file, 2 x largest wall time ever
measured), rounded up to the hour; memory = 1.5 x the largest peak ever
measured on any MC file (incl. the pilot timing job, 3.06 GB), rounded up to
the next EVEN GB as the pilot did (4.59 -> 6 GB); a single value, because
per-record peaks from tiny files are not representative.

Disk = events x the record's measured output bytes/event over all its
measured files (= the actual total for the pilot records; an upper bound
for records measured on one small file, which carries a fixed overhead). Files = per job 9 outputs + job
dir + 2 PBS logs, + record dir + log dir per record.

Writes fullrun_projection.json.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

ORDER = [67801, 67993, 35669, 35631, 64895, 64839, 72676, 72752, 75589, 68187,
         68073, 37728, 68847]
PILOT = {67801, 35669, 37728}
FILES_PER_JOB = 9 + 1 + 2
FILES_PER_RECORD = 2
PILOT_TIMING_PEAK_GB = 3.06   # HANDOFF_PILOT.md, timing job 5208393


def nnls_small(A: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Non-negative least squares by enumerating active sets (3 params)."""
    best, best_res = None, math.inf
    n = A.shape[1]
    for k in range(1, n + 1):
        for cols in itertools.combinations(range(n), k):
            c, *_ = np.linalg.lstsq(A[:, cols], t, rcond=None)
            if np.any(c < 0):
                continue
            full = np.zeros(n)
            full[list(cols)] = c
            res = float(np.sum((A @ full - t) ** 2))
            if res < best_res:
                best, best_res = full, res
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--smoke", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--files-now", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    inputs = json.loads(Path(args.inputs).read_text())["records"]
    smoke = json.loads(Path(args.smoke).read_text())["records"]
    pilot = json.loads(Path(args.pilot).read_text())["files"]

    meas = [{"record": f["record"], "n": f["n_read"], "fs": f["n_final_state_groups"],
             "t": f["elapsed_sec"], "rss": f["peak_rss_gb"], "bytes": f["output_bytes"],
             "src": "pilot 10 Oct"} for f in pilot]
    meas += [{"record": r["record"], "n": r["events_read"], "fs": r["n_final_states"],
              "t": r["wall_seconds_driver"], "rss": r["peak_rss_gb"], "bytes": r["output_bytes"],
              "src": "smoke 17 Oct"} for r in smoke if r["production_success"]]

    # final states per decade of events, per pilot record (log-linear fit)
    growth = {}
    for rid in PILOT:
        x = np.array([[math.log10(m["n"]), m["fs"]] for m in meas if m["record"] == rid])
        growth[rid] = float(np.polyfit(x[:, 0], x[:, 1], 1)[0])
    fs_per_decade = max(growth.values())

    A = np.array([[1.0, m["fs"], m["n"] / 1e6] for m in meas])
    t = np.array([m["t"] for m in meas])
    coef = nnls_small(A, t)
    central = A @ coef
    env_scale = float(np.max(t / central))
    max_wall = max(m["t"] for m in meas)
    max_rss = max(m["rss"] for m in meas if m["rss"] is not None)

    def model(fs: float, n: float) -> float:
        return float(coef[0] + coef[1] * fs + coef[2] * n / 1e6)

    rows = []
    tot = {k: 0.0 for k in ("files", "events", "cpu_h_realistic", "cpu_h_literal",
                            "disk_gb", "files_created")}
    tot_reuse = {k: 0.0 for k in ("files", "cpu_h_realistic", "disk_gb", "files_created")}
    for rid in ORDER:
        inp = inputs[str(rid)]
        m = [x for x in meas if x["record"] == rid]
        ref = max(m, key=lambda x: x["n"])          # the record's largest measured file
        def fs_est(n: int) -> float:
            if n <= ref["n"]:
                return max(x["fs"] for x in m if x["n"] <= max(n, min(y["n"] for y in m))) \
                    if rid in PILOT else ref["fs"]
            return ref["fs"] + fs_per_decade * math.log10(n / ref["n"])
        per_file = [(f["n_events"], fs_est(f["n_events"])) for f in inp["files"]]
        cpu_real = sum(model(fs, n) for n, fs in per_file) / 3600
        nmax = inp["max_events"]
        fs_max = fs_est(nmax)
        worst_central = model(fs_max, nmax)
        worst_env = worst_central * env_scale
        slow = min(x["n"] / x["t"] for x in m)
        worst_lit = nmax / slow
        cpu_lit = inp["sum_of_file_events"] / slow / 3600
        wall_req_h = math.ceil(max(2 * worst_env, 2 * max_wall) / 3600)
        bpe = sum(x["bytes"] for x in m) / sum(x["n"] for x in m)
        disk = inp["sum_of_file_events"] * bpe / 1e9
        files_created = inp["n_files"] * FILES_PER_JOB + FILES_PER_RECORD
        row = {
            "record": rid, "physics_short": inp["physics_short"],
            "n_files": inp["n_files"], "events": inp["sum_of_file_events"],
            "largest_file_events": nmax, "largest_file_index": inp["largest_file_index"],
            "measured_files": len(m), "measured_from": sorted({x["src"] for x in m}),
            "largest_measured_file_events": ref["n"], "largest_measured_file_fs": ref["fs"],
            "fs_estimated_for_largest_file": fs_max,
            "realistic_cpu_hours": cpu_real,
            "realistic_worst_file_hours_central": worst_central / 3600,
            "realistic_worst_file_hours_envelope": worst_env / 3600,
            "literal_slowest_rate_ev_per_s": slow,
            "literal_cpu_hours": cpu_lit,
            "literal_worst_file_hours": worst_lit / 3600,
            "request_walltime_h": wall_req_h,
            "request_mem_gb": 2 * math.ceil(1.5 * max(max_rss, PILOT_TIMING_PEAK_GB) / 2),
            "queue_by_walltime": "shortE (<=2 h)" if wall_req_h <= 2 else
            ("normE (2-12 h)" if wall_req_h <= 12 else "longE (12-72 h)"),
            "max_output_bytes_per_event": bpe,
            "projected_disk_gb": disk,
            "projected_files_created": files_created,
        }
        rows.append(row)
        tot["files"] += inp["n_files"]
        tot["events"] += inp["sum_of_file_events"]
        tot["cpu_h_realistic"] += cpu_real
        tot["cpu_h_literal"] += cpu_lit
        tot["disk_gb"] += disk
        tot["files_created"] += files_created
        if rid not in PILOT:
            tot_reuse["files"] += inp["n_files"]
            tot_reuse["cpu_h_realistic"] += cpu_real
            tot_reuse["disk_gb"] += disk
            tot_reuse["files_created"] += files_created
    out = {
        "model": {"coef_a_s": coef[0], "coef_b_s_per_fs": coef[1], "coef_c_s_per_Mevent": coef[2],
                  "envelope_scale": env_scale, "n_measured_files": len(meas),
                  "fs_per_decade_by_pilot_record": growth, "fs_per_decade_used": fs_per_decade,
                  "largest_measured_wall_s": max_wall, "largest_measured_peak_rss_gb": max_rss},
        "measured_cpu_hours_pilot_records": {str(r): sum(x["t"] for x in meas if x["record"] == r) / 3600
                                             for r in sorted(PILOT)},
        "rows": rows, "totals_rerun_all": tot, "totals_if_pilot_reused": tot_reuse,
        "files_now": args.files_now,
        "file_count_after_rerun_all": args.files_now + tot["files_created"],
        "file_count_after_if_pilot_reused": args.files_now + tot_reuse["files_created"],
        "soft_quota": 150000, "hard_limit": 200000,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out["model"], indent=1))
    for r in rows:
        print(f"{r['record']:>6} files {r['n_files']:>3} ev {r['events']:>11,} "
              f"fs_max~{r['fs_estimated_for_largest_file']:.0f} "
              f"realCPU {r['realistic_cpu_hours']:6.1f} h worst(env) {r['realistic_worst_file_hours_envelope']:.2f} h | "
              f"literal CPU {r['literal_cpu_hours']:7.1f} h worst {r['literal_worst_file_hours']:6.1f} h | "
              f"req {r['request_walltime_h']} h {r['request_mem_gb']} GB | disk {r['projected_disk_gb']:.1f} GB "
              f"files {r['projected_files_created']}")
    print(json.dumps({k: v for k, v in out.items() if k.startswith(("totals", "file_count"))}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
