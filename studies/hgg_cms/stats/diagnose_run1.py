"""
Statistical-model task: local diagnosis of the 18 Sep 2026 hgg_stats
validation run's two flagged issues (pull_width mislabeling, and high
fit-failure rates), using small reproducible samples with the FIXED
`fit.toy_q0` (now capturing `mu_err` via an explicit HESSE call and
`*_fmin` MIGRAD diagnostics -- see fit.py's and run_toy_job.py's own
change notes). NOT a full rerun of the cluster campaign -- that would
need the cluster again (an explicit HESSE roughly 5x's the per-toy
cost, see this script's own timing print), which is out of scope for
"diagnose and report"; this reproduces small, honestly-labeled samples
using the EXACT seeds already committed in logs/hgg_stats/job_list.txt,
so the numbers below are real (not fabricated), just from a smaller N
than the full cluster run.

Fully synthetic -- no data file, blinded or otherwise, is read.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from studies.hgg_cms.stats import model as M
from studies.hgg_cms.stats import fit as F
from studies.hgg_cms.stats.cluster import run_toy_job as J

OUT_PATH = Path(__file__).resolve().parent / "results" / "diagnose_run1.json"
MH_NOMINAL = 125.09


def run_sample(job_type, mu_true, seed, n_toys):
    names = M.full_param_names()
    base = F.default_start(names, mu_start=0.0)
    rng = np.random.default_rng(seed)
    t0 = time.time()
    if job_type == "bkg_only":
        results = J.run_bkg_only(rng, names, base, n_toys)
    elif job_type == "sig_injection":
        results = J.run_sig_injection(rng, names, base, n_toys, mu_true)
    elif job_type == "spurious_check":
        results = J.run_spurious_check(rng, names, base, n_toys)
    elif job_type == "mass_scan_bkg":
        results = J.run_mass_scan_bkg(rng, names, base, n_toys)
    else:
        raise ValueError(job_type)
    dt = time.time() - t0
    print(f"{job_type} mu={mu_true} seed={seed} n={n_toys}: {dt:.1f}s ({dt/n_toys:.2f}s/toy)", flush=True)
    return results


def analyze_pull(results, mu_true):
    ok = [r for r in results if not r["failed"]]
    mu_hat_all = np.array([r["mu_hat"] for r in results])
    mu_err = np.array([r.get("mu_err", np.nan) for r in ok])
    accurate = np.array([bool((r.get("alt_fmin_post_hesse") or {}).get("has_accurate_covar")) for r in ok])
    good = np.isfinite(mu_err) & (mu_err > 0) & accurate
    mu_hat_ok = np.array([r["mu_hat"] for r in ok])
    pull = (mu_hat_ok[good] - mu_true) / mu_err[good]
    return {
        "n_toys": len(results), "n_failed": len(results) - len(ok), "n_used": len(ok),
        "n_with_reliable_mu_err": int(good.sum()),
        "residual_width_all_toys_incl_failed": float(np.std(mu_hat_all - mu_true)),
        "residual_width_excl_failed": float(np.std(mu_hat_ok - mu_true)),
        "true_pull_mean": float(np.mean(pull)) if good.sum() else None,
        "true_pull_width": float(np.std(pull)) if good.sum() else None,
    }


def analyze_failures(results, job_type):
    if job_type == "mass_scan_bkg":
        failed_flag = "any_failed"
    else:
        failed_flag = "failed"
    failed = [r for r in results if r.get(failed_flag)]
    passed = [r for r in results if not r.get(failed_flag)]

    def _stat(rs, key):
        vals = [r[key] for r in rs if key in r and r[key] is not None]
        return {"mean": float(np.mean(vals)), "std": float(np.std(vals)), "n": len(vals)} if vals else None

    out = {
        "n_toys": len(results), "n_failed": len(failed), "n_passed": len(passed),
        "n_obs_total_failed": _stat(failed, "n_obs_total"),
        "n_obs_total_passed": _stat(passed, "n_obs_total"),
    }
    if job_type != "mass_scan_bkg":
        out["mu_hat_abs_failed"] = _stat([{"mu_hat_abs": abs(r["mu_hat"])} for r in failed], "mu_hat_abs")
        out["mu_hat_abs_passed"] = _stat([{"mu_hat_abs": abs(r["mu_hat"])} for r in passed], "mu_hat_abs")
        flag_counts = {}
        for r in failed:
            fmin = r.get("alt_fmin") or {}
            for k, v in fmin.items():
                if k == "edm":
                    continue
                if v:
                    flag_counts[k] = flag_counts.get(k, 0) + 1
        out["fmin_flag_counts_among_failed"] = flag_counts
        out["n_at_mu_bound_failed"] = sum(1 for r in failed if abs(r["mu_hat"]) > 19.0)
        out["n_at_mu_bound_passed"] = sum(1 for r in passed if abs(r["mu_hat"]) > 19.0)
    else:
        n_failed_points = [r["n_failed_points"] for r in results]
        vals, counts = np.unique(n_failed_points, return_counts=True)
        out["n_failed_points_histogram"] = {int(v): int(c) for v, c in zip(vals, counts)}
        out["null_invalid_count"] = sum(1 for r in results if not r.get("null_valid", True))
        # bias check: does max_Z differ between toys with 0 failed points
        # vs toys with >0 failed points (excluding the ones with 0)?
        z_clean = [r["max_Z"] for r in results if r["n_failed_points"] == 0]
        z_dirty = [r["max_Z"] for r in results if r["n_failed_points"] > 0]
        out["max_Z_mean_zero_failed_points"] = float(np.mean(z_clean)) if z_clean else None
        out["max_Z_mean_some_failed_points"] = float(np.mean(z_dirty)) if z_dirty else None
    return out


def main():
    samples = [
        ("bkg_only", 0.0, 20260918, 30),
        ("sig_injection", 0.5, 20260926, 30),
        ("sig_injection", 1.0, 20260930, 50),
        ("sig_injection", 2.0, 20260934, 30),
        ("spurious_check", 0.0, 20260938, 20),
        ("mass_scan_bkg", 0.0, 20260948, 15),
    ]
    out = {}
    for job_type, mu_true, seed, n in samples:
        results = run_sample(job_type, mu_true, seed, n)
        key = f"{job_type}_{mu_true}" if job_type == "sig_injection" else job_type
        entry = {"seed": seed, "n_toys": n}
        if job_type in ("bkg_only", "sig_injection"):
            entry["pull_analysis"] = analyze_pull(results, mu_true)
        entry["failure_analysis"] = analyze_failures(results, job_type)
        out[key] = entry
        print(f"  -> {json.dumps(entry, default=str)[:300]}...", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
