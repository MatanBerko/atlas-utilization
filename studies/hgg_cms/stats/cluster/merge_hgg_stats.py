#!/usr/bin/env python
"""
Statistical-model task, Parts 2 and 3.3/3.5: merges every
`run_toy_job.py` output under `--jobs-base/<job_type>/job_*.json` into
one summary JSON per job_type, with the validation criteria from Part 2
of this task's instructions evaluated directly (PASS/FAIL), plus the
Part 3.3 expected band and Part 3.5 look-elsewhere trials-factor numbers.

Usage:
    python studies/hgg_cms/stats/cluster/merge_hgg_stats.py \\
        --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_stats \\
        --out /storage/agrp/berkom/atlas-utilization/output/hgg_stats/merged/hgg_stats_merged.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats as sps


def load_job_type(jobs_base: Path, job_type: str) -> list:
    out = []
    for f in sorted((jobs_base / job_type).glob("job_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.extend(d["results"])
    return out


def asymptotic_q0_tail(z_thresh):
    """P(Z >= z) for a half-chi2_1 mixture: 1 - Phi(z)."""
    return float(1.0 - sps.norm.cdf(z_thresh))


def summarize_bkg_only(results: list) -> dict:
    ok = [r for r in results if not r["failed"]]
    n_failed = len(results) - len(ok)
    q0 = np.array([r["q0"] for r in ok])
    mu_hat = np.array([r["mu_hat"] for r in ok])
    n = len(ok)
    frac_mu_leq_0 = float(np.mean(mu_hat <= 0))
    tails = {}
    for zt in (1, 2, 3):
        n_ge = int(np.sum(np.sqrt(np.maximum(q0, 0.0)) >= zt))
        frac = n_ge / n if n else float("nan")
        binom_sigma = float(np.sqrt(frac * (1 - frac) / n)) if n else float("nan")
        asym = asymptotic_q0_tail(zt)
        tails[f"Z_ge_{zt}"] = {"observed_fraction": frac, "binomial_sigma": binom_sigma,
                                "asymptotic": asym, "within_3sigma": bool(abs(frac - asym) <= 3 * binom_sigma)}
    return {
        "n_toys": len(results), "n_failed": n_failed, "n_used": n,
        "frac_mu_hat_leq_0": frac_mu_leq_0, "frac_mu_hat_leq_0_expected": 0.5,
        "mu_leq_0_pass": bool(abs(frac_mu_leq_0 - 0.5) < 0.05),
        "tail_fractions": tails,
    }


def summarize_sig_injection(results: list, mu_true: float) -> dict:
    ok = [r for r in results if not r["failed"]]
    n_failed = len(results) - len(ok)
    mu_hat = np.array([r["mu_hat"] for r in ok])
    z = np.array([r["Z"] for r in ok])
    pull_mean = float(np.mean(mu_hat) - mu_true)
    pull_width = float(np.std(mu_hat))
    return {
        "mu_true": mu_true, "n_toys": len(results), "n_failed": n_failed, "n_used": len(ok),
        "mu_hat_mean": float(np.mean(mu_hat)), "pull_mean": pull_mean, "pull_width": pull_width,
        "pull_mean_pass": bool(abs(pull_mean) < 0.05), "pull_width_pass": bool(abs(pull_width - 1.0) < 0.05),
        "median_Z": float(np.median(z)), "Z_16pct": float(np.percentile(z, 16)),
        "Z_84pct": float(np.percentile(z, 84)),
        "P_Z_ge_3": float(np.mean(z >= 3)), "P_Z_ge_5": float(np.mean(z >= 5)),
    }


def summarize_spurious_check(results: list) -> dict:
    ok = [r for r in results if not r["failed"]]
    n_failed = len(results) - len(ok)
    mu_hat = np.array([r["mu_hat"] for r in ok])
    return {
        "n_toys": len(results), "n_failed": n_failed, "n_used": len(ok),
        "mu_hat_mean": float(np.mean(mu_hat)), "mu_hat_std": float(np.std(mu_hat)),
        "absorbed_ok": bool(abs(float(np.mean(mu_hat))) < 0.1),
    }


def summarize_mass_scan_bkg(results: list) -> dict:
    max_z = np.array([r["max_Z"] for r in results if not r.get("any_failed")])
    n_failed = sum(1 for r in results if r.get("any_failed"))
    trials_factor_at_3 = {}
    for local_z in (1.0, 2.0, 3.0):
        global_p = float(np.mean(max_z >= local_z))
        local_p = asymptotic_q0_tail(local_z)
        trials_factor = global_p / local_p if local_p > 0 else float("nan")
        trials_factor_at_3[f"local_Z_{local_z}"] = {
            "global_p_from_toys": global_p, "local_p_asymptotic": local_p, "trials_factor": trials_factor,
        }
    return {
        "n_toys": len(results), "n_failed": n_failed, "n_used": len(max_z),
        "max_Z_mean": float(np.mean(max_z)) if len(max_z) else float("nan"),
        "trials_factor": trials_factor_at_3,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    out = {}

    bkg = load_job_type(jobs_base, "bkg_only")
    if bkg:
        out["part_2_1_background_only"] = summarize_bkg_only(bkg)

    sig_by_mu = {}
    for f in sorted((jobs_base / "sig_injection").glob("job_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        sig_by_mu.setdefault(d["mu_true"], []).extend(d["results"])
    if sig_by_mu:
        out["part_2_2_signal_injection"] = {
            str(mu): summarize_sig_injection(results, mu) for mu, results in sorted(sig_by_mu.items())
        }
        if 1.0 in sig_by_mu:
            out["part_3_3_expected_band_mu1"] = summarize_sig_injection(sig_by_mu[1.0], 1.0)

    spur = load_job_type(jobs_base, "spurious_check")
    if spur:
        out["part_2_3_spurious_signal_check"] = summarize_spurious_check(spur)

    scan = load_job_type(jobs_base, "mass_scan_bkg")
    if scan:
        out["part_3_5_look_elsewhere"] = summarize_mass_scan_bkg(scan)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    for k, v in out.items():
        print(f"  {k}: {json.dumps(v)[:200]}...")


if __name__ == "__main__":
    main()
