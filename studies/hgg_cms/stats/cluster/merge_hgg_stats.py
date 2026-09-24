#!/usr/bin/env python
"""
Statistical-model task, Parts 2 and 3.3/3.5: merges every
`run_toy_job.py` output under `--jobs-base/<job_type>/*job_*.json`
(matches both the original run's `job_NNNN.json` and any retry's
`retryK_job_NNNN.json` -- see `pbs_hgg_stats_array.sh`'s OUT_PREFIX)
into one summary JSON per job_type, with the validation criteria from
Part 2 of this task's instructions evaluated directly (PASS/FAIL), plus
the Part 3.3 expected band and Part 3.5 look-elsewhere trials-factor
numbers.

Before any validation criterion is evaluated, this script reports the
final toy count actually collected per job_type (and per mu_true for
sig_injection) against this task's own pre-set minimums (bkg_only
>=2000, sig_injection >=1000 per mu_true in {0.5, 1, 2}, spurious_check
>=1000, mass_scan_bkg >=1000). If any falls short, it prints exactly
which and STOPS (exit code 2) -- it does not compute or report
validation criteria on a short toy count.

A file that fails to parse as JSON (e.g. a killed job that somehow left
a truncated file -- `run_toy_job.py` only ever writes its output in one
`Path.write_text(...)` call at the very end, so this should not happen
in practice, but is handled defensively rather than assumed) is skipped
with a printed warning and counted in `n_corrupt_files_skipped`, never
silently dropped.

Usage:
    python studies/hgg_cms/stats/cluster/merge_hgg_stats.py \\
        --jobs-base /storage/agrp/berkom/atlas-utilization/output/hgg_stats \\
        --out /storage/agrp/berkom/atlas-utilization/output/hgg_stats/merged/hgg_stats_merged.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.stats.fit import strict_valid  # noqa: E402

REQUIRED_MINIMA = {
    "bkg_only": 2000,
    "sig_injection": {0.5: 1000, 1.0: 1000, 2.0: 1000},
    "spurious_check": 1000,
    "mass_scan_bkg": 1000,
}


def _load_json_files(jobs_base: Path, job_type: str) -> list:
    """Every file matching *job_*.json under jobs_base/job_type/ (both
    the original run's job_NNNN.json and any retryK_job_NNNN.json),
    parsed defensively -- a file that fails to parse is skipped with a
    warning, not silently dropped, and not treated as fatal on its own
    (the minimum-count check below is what actually gates on this)."""
    docs = []
    n_corrupt = 0
    for f in sorted((jobs_base / job_type).glob("*job_*.json")):
        try:
            docs.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: could not parse {f}: {type(e).__name__}: {e} -- skipping this file", file=sys.stderr)
            n_corrupt += 1
    return docs, n_corrupt


def load_job_type(jobs_base: Path, job_type: str):
    docs, n_corrupt = _load_json_files(jobs_base, job_type)
    results = []
    for d in docs:
        results.extend(d["results"])
    return results, n_corrupt


def asymptotic_q0_tail(z_thresh):
    """P(Z >= z) for a half-chi2_1 mixture: 1 - Phi(z)."""
    return float(1.0 - sps.norm.cdf(z_thresh))


def histogram(values: np.ndarray, bin_edges: np.ndarray) -> dict:
    """A histogram (not the raw array) is what's saved to the merged
    JSON -- enough to plot a real distribution (q0/Z, pulls, max_Z)
    without the merged file growing to the size of the raw per-toy
    data across thousands of toys."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    counts, edges = np.histogram(values, bins=bin_edges)
    return {"bin_edges": edges.tolist(), "counts": counts.tolist(), "n": int(len(values))}


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
    z = np.sqrt(np.maximum(q0, 0.0))
    return {
        "n_toys": len(results), "n_failed": n_failed, "n_used": n,
        "frac_mu_hat_leq_0": frac_mu_leq_0, "frac_mu_hat_leq_0_expected": 0.5,
        "mu_leq_0_pass": bool(abs(frac_mu_leq_0 - 0.5) < 0.05),
        "tail_fractions": tails,
        "Z_histogram": histogram(z, np.arange(0.0, 6.01, 0.25)),
    }


def summarize_sig_injection(results: list, mu_true: float) -> dict:
    """NOTE (18 Sep 2026 review): the field previously named
    "pull_width" here was `std(mu_hat)` -- the residual width in
    ABSOLUTE mu units, not a true pull (which needs dividing by each
    toy's own fitted mu uncertainty, sigma_mu_hat). That quantity is
    kept below as `mu_hat_residual_width`, clearly labeled, and is NOT
    compared against the 1.00+-0.05 pre-set criterion (which is about
    the true pull). `pull_width` here is the REAL pull -- (mu_hat -
    mu_true) / mu_err -- computed only over toys that have a finite,
    positive `mu_err` AND an accurate post-HESSE covariance (both added
    to `toy_q0`/`run_toy_job.py` in this same review; toys from before
    that fix have neither field at all, in which case `pull_width` and
    `pull_width_pass` are None, not a guess -- see `n_with_mu_err` for
    how many toys could contribute)."""
    ok = [r for r in results if not r["failed"]]
    n_failed = len(results) - len(ok)
    mu_hat = np.array([r["mu_hat"] for r in ok])
    z = np.array([r["Z"] for r in ok])
    pull_mean = float(np.mean(mu_hat) - mu_true)
    residual_width = float(np.std(mu_hat))

    mu_err = np.array([r.get("mu_err", float("nan")) for r in ok], dtype=float)
    # A toy's alt fit can pass MIGRAD's own (cheap, automatic) validity
    # check yet still have an unreliable covariance under an EXPLICIT
    # HESSE call -- `strict_valid` (fit.py) requires an accurate AND
    # genuinely positive-definite (not forced) post-HESSE covariance,
    # not just MIGRAD's own `valid`. Toys without an
    # `alt_fmin_post_hesse` field (pre-fix data) are excluded from the
    # pull the same way a missing mu_err already excludes them.
    good_err = np.array([strict_valid(r.get("alt_fmin_post_hesse"), r.get("mu_err")) for r in ok])
    n_with_mu_err = int(np.sum(good_err))
    if n_with_mu_err > 0:
        pull = (mu_hat[good_err] - mu_true) / mu_err[good_err]
        true_pull_mean = float(np.mean(pull))
        true_pull_width = float(np.std(pull))
        pull_width_pass = bool(abs(true_pull_width - 1.0) < 0.05)
    else:
        true_pull_mean = None
        true_pull_width = None
        pull_width_pass = None  # cannot evaluate -- not a guessed True/False

    return {
        "mu_true": mu_true, "n_toys": len(results), "n_failed": n_failed, "n_used": len(ok),
        "n_with_mu_err": n_with_mu_err,
        "mu_hat_mean": float(np.mean(mu_hat)), "pull_mean": pull_mean,
        "mu_hat_residual_width": residual_width,
        "pull_width": true_pull_width, "pull_width_pass": pull_width_pass,
        "true_pull_mean_from_mu_err": true_pull_mean,
        "pull_mean_pass": bool(abs(pull_mean) < 0.05),
        "median_Z": float(np.median(z)), "Z_16pct": float(np.percentile(z, 16)),
        "Z_84pct": float(np.percentile(z, 84)),
        "P_Z_ge_3": float(np.mean(z >= 3)), "P_Z_ge_5": float(np.mean(z >= 5)),
        "Z_histogram": histogram(z, np.arange(0.0, max(float(z.max()) + 0.5, 6.0) + 0.25, 0.25)),
        "mu_hat_residual_histogram": histogram(mu_hat - mu_true, np.arange(-1.5, 1.51, 0.05)),
        "true_pull_histogram": (histogram((mu_hat[good_err] - mu_true) / mu_err[good_err],
                                           np.arange(-4.0, 4.01, 0.25))
                                 if n_with_mu_err > 0 else None),
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


def count_upcrossings(z_curve: list, level: float) -> int:
    """How many times a Z(mH) curve crosses UP through `level` (i.e.
    z[i] < level <= z[i+1]) -- the empirical input to the Gross-Vitells
    average-upcrossing-count E[N(level)]."""
    z = np.asarray(z_curve, dtype=float)
    return int(np.sum((z[:-1] < level) & (z[1:] >= level)))


def gross_vitells_global_p(local_z: float, mean_upcrossings_at_z0: float, z0: float) -> float:
    """Gross & Vitells, Eur.Phys.J.C70:525-530 (2010), arXiv:1005.1891:
    P_global(c) ~ P_local(c) + E[N(c0)] * exp(-(c - c0)/2), with c=Z^2
    (the chi2_1 test statistic) and c0=z0^2 the reference level. Valid
    for local_z >= z0; below that this formula isn't meaningful (the
    exponential extrapolation only holds well above the reference
    level) and this function returns just the local p-value."""
    if local_z < z0:
        return asymptotic_q0_tail(local_z)
    c, c0 = local_z ** 2, z0 ** 2
    return asymptotic_q0_tail(local_z) + mean_upcrossings_at_z0 * float(np.exp(-(c - c0) / 2.0))


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

    # Gross-Vitells: reference level Z0=1, E[N(Z0)] estimated as the
    # mean upcrossing count of Z0=1 across every toy's own 81-point
    # Z(mH) curve (only toys with a stored Z_scan and no failed point
    # contribute -- a failed point's Z is not trustworthy as part of a
    # smooth curve for crossing-counting).
    z0 = 1.0
    curves = [r["Z_scan"] for r in results if not r.get("any_failed") and "Z_scan" in r]
    gross_vitells = None
    if curves:
        n_up = [count_upcrossings(c, z0) for c in curves]
        mean_n_up = float(np.mean(n_up))
        gv_p_at_3 = gross_vitells_global_p(3.0, mean_n_up, z0)
        gross_vitells = {
            "reference_level_Z0": z0, "n_curves_used": len(curves),
            "mean_upcrossings_at_Z0": mean_n_up,
            "global_p_at_local_Z_3": gv_p_at_3,
            "trials_factor_at_local_Z_3": gv_p_at_3 / asymptotic_q0_tail(3.0),
            "toy_based_global_p_at_local_Z_3": trials_factor_at_3["local_Z_3.0"]["global_p_from_toys"],
        }

    n_failed_points = [r.get("n_failed_points") for r in results if r.get("n_failed_points") is not None]
    failed_points_hist = None
    if n_failed_points:
        vals, counts = np.unique(n_failed_points, return_counts=True)
        failed_points_hist = {int(v): int(c) for v, c in zip(vals, counts)}

    return {
        "n_toys": len(results), "n_failed": n_failed, "n_used": len(max_z),
        "max_Z_mean": float(np.mean(max_z)) if len(max_z) else float("nan"),
        "trials_factor": trials_factor_at_3,
        "gross_vitells": gross_vitells,
        "n_failed_points_histogram": failed_points_hist,
        "max_Z_histogram": histogram(max_z, np.arange(0.0, max(float(max_z.max()) + 0.5, 5.0) + 0.25, 0.25))
                            if len(max_z) else None,
    }


def summarize_fmin_diagnostics(results: list, has_mu_err: bool = False) -> dict:
    """Tabulates which MIGRAD fmin flag(s) are set among the FAILED
    toys of one job type (only meaningful for toys produced with the 18
    Sep 2026 fmin-capturing fix -- see fit.py's fmin_diagnostics; toys
    from before that fix simply have no fmin fields, which shows up
    here as n_with_fmin_data=0, not a fabricated breakdown).

    If `has_mu_err` (job types that call `mu_hesse_error`: bkg_only,
    sig_injection, spurious_check -- not mass_scan_bkg), also computes
    a CORRECTED failure count: `fit.strict_valid` re-checked on EVERY
    toy (not just the ones the original loose `failed` flag caught),
    since `failed` there is based on `Minuit.valid`, which does not by
    itself require an accurate or positive-definite covariance (see
    `fmin_diagnostics`'s own docstring)."""
    failed = [r for r in results if r.get("failed") or r.get("any_failed")]
    flag_counts = {"has_parameters_at_limit": 0, "has_accurate_covar_false": 0,
                   "has_posdef_covar_false": 0, "has_made_posdef_covar": 0,
                   "hesse_failed": 0, "is_above_max_edm": 0, "has_reached_call_limit": 0}
    n_with_data = 0
    edms = []
    for r in failed:
        fmin = r.get("alt_fmin") or r.get("first_failed_point_fmin") or {}
        if not fmin:
            continue
        n_with_data += 1
        if fmin.get("has_parameters_at_limit"):
            flag_counts["has_parameters_at_limit"] += 1
        if fmin.get("has_accurate_covar") is False:
            flag_counts["has_accurate_covar_false"] += 1
        if fmin.get("has_posdef_covar") is False:
            flag_counts["has_posdef_covar_false"] += 1
        if fmin.get("has_made_posdef_covar"):
            flag_counts["has_made_posdef_covar"] += 1
        if fmin.get("hesse_failed"):
            flag_counts["hesse_failed"] += 1
        if fmin.get("is_above_max_edm"):
            flag_counts["is_above_max_edm"] += 1
        if fmin.get("has_reached_call_limit"):
            flag_counts["has_reached_call_limit"] += 1
        if "edm" in fmin:
            edms.append(fmin["edm"])
    out = {
        "n_failed_toys": len(failed), "n_with_fmin_data": n_with_data,
        "flag_counts_among_failed": flag_counts,
        "median_edm_among_failed": float(np.median(edms)) if edms else None,
    }
    if has_mu_err:
        n_with_post_hesse = sum(1 for r in results if r.get("alt_fmin_post_hesse"))
        if n_with_post_hesse:
            n_strict_valid = sum(1 for r in results
                                  if strict_valid(r.get("alt_fmin_post_hesse"), r.get("mu_err")))
            out["corrected_failure_rate"] = {
                "n_toys": len(results), "n_with_post_hesse_data": n_with_post_hesse,
                "n_loose_failed": len(failed), "loose_failure_rate": len(failed) / len(results),
                "n_strict_valid": n_strict_valid,
                "n_strict_failed": len(results) - n_strict_valid,
                "strict_failure_rate": 1.0 - n_strict_valid / len(results),
            }
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-base", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    jobs_base = Path(args.jobs_base)
    n_corrupt_total = 0

    bkg, nc = load_job_type(jobs_base, "bkg_only")
    n_corrupt_total += nc

    sig_by_mu = {}
    sig_docs, nc = _load_json_files(jobs_base, "sig_injection")
    n_corrupt_total += nc
    for d in sig_docs:
        sig_by_mu.setdefault(d["mu_true"], []).extend(d["results"])

    spur, nc = load_job_type(jobs_base, "spurious_check")
    n_corrupt_total += nc

    scan, nc = load_job_type(jobs_base, "mass_scan_bkg")
    n_corrupt_total += nc

    # --- Minimum toy-count gate, evaluated BEFORE any validation
    # criterion, per this task's own pre-set rule. ---
    print("=== Toy counts vs required minimums ===")
    shortfalls = []
    counts_report = {
        "bkg_only": len(bkg),
        "sig_injection": {str(mu): len(r) for mu, r in sorted(sig_by_mu.items())},
        "spurious_check": len(spur),
        "mass_scan_bkg": len(scan),
    }
    if len(bkg) < REQUIRED_MINIMA["bkg_only"]:
        shortfalls.append(f"bkg_only: {len(bkg)} < {REQUIRED_MINIMA['bkg_only']} required")
    print(f"  bkg_only: {len(bkg)} (>= {REQUIRED_MINIMA['bkg_only']} required)"
          + ("  SHORT" if len(bkg) < REQUIRED_MINIMA["bkg_only"] else "  OK"))

    for mu_req, n_req in REQUIRED_MINIMA["sig_injection"].items():
        n_have = len(sig_by_mu.get(mu_req, []))
        status = "OK" if n_have >= n_req else "SHORT"
        print(f"  sig_injection mu={mu_req}: {n_have} (>= {n_req} required)  {status}")
        if n_have < n_req:
            shortfalls.append(f"sig_injection mu={mu_req}: {n_have} < {n_req} required")

    print(f"  spurious_check: {len(spur)} (>= {REQUIRED_MINIMA['spurious_check']} required)"
          + ("  SHORT" if len(spur) < REQUIRED_MINIMA["spurious_check"] else "  OK"))
    if len(spur) < REQUIRED_MINIMA["spurious_check"]:
        shortfalls.append(f"spurious_check: {len(spur)} < {REQUIRED_MINIMA['spurious_check']} required")

    print(f"  mass_scan_bkg: {len(scan)} (>= {REQUIRED_MINIMA['mass_scan_bkg']} required)"
          + ("  SHORT" if len(scan) < REQUIRED_MINIMA["mass_scan_bkg"] else "  OK"))
    if len(scan) < REQUIRED_MINIMA["mass_scan_bkg"]:
        shortfalls.append(f"mass_scan_bkg: {len(scan)} < {REQUIRED_MINIMA['mass_scan_bkg']} required")

    if n_corrupt_total:
        print(f"  ({n_corrupt_total} corrupt/unparseable file(s) skipped -- see WARNING lines above)")

    if shortfalls:
        print("\nSTOPPED: toy counts below the required minimum -- not evaluating any validation "
              "criterion on a short count. Submit more toys for the job type(s) below, merge again:",
              file=sys.stderr)
        for s in shortfalls:
            print(f"  - {s}", file=sys.stderr)
        sys.exit(2)

    print("All toy counts meet their required minimum -- evaluating validation criteria.\n")

    out = {"toy_counts": counts_report, "n_corrupt_files_skipped": n_corrupt_total}

    if bkg:
        out["part_2_1_background_only"] = summarize_bkg_only(bkg)
        out["part_2_1_background_only"]["fmin_diagnostics"] = summarize_fmin_diagnostics(bkg, has_mu_err=True)

    if sig_by_mu:
        out["part_2_2_signal_injection"] = {
            str(mu): summarize_sig_injection(results, mu) for mu, results in sorted(sig_by_mu.items())
        }
        for mu, results in sig_by_mu.items():
            out["part_2_2_signal_injection"][str(mu)]["fmin_diagnostics"] = \
                summarize_fmin_diagnostics(results, has_mu_err=True)
        if 1.0 in sig_by_mu:
            out["part_3_3_expected_band_mu1"] = summarize_sig_injection(sig_by_mu[1.0], 1.0)

    if spur:
        out["part_2_3_spurious_signal_check"] = summarize_spurious_check(spur)
        out["part_2_3_spurious_signal_check"]["fmin_diagnostics"] = summarize_fmin_diagnostics(spur, has_mu_err=True)

    if scan:
        out["part_3_5_look_elsewhere"] = summarize_mass_scan_bkg(scan)
        out["part_3_5_look_elsewhere"]["fmin_diagnostics"] = summarize_fmin_diagnostics(scan)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    for k, v in out.items():
        print(f"  {k}: {json.dumps(v)[:200]}...")


if __name__ == "__main__":
    main()
