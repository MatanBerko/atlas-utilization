#!/usr/bin/env python
"""
Statistical-model task, Parts 2 and 3.3/3.5: ONE toy job -- runs a batch
of `--n-toys` synthetic toys of one `--job-type` and writes a JSON
summary. NEVER touches real data (no file with BLINDED in the name is
imported or opened anywhere in this module); every toy is Poisson-drawn
from the model's own prediction (`fit.generate_toy`), i.e. fully
synthetic, per this task's OUT OF SCOPE rule.

Job types:
  bkg_only        -- mu_true=0, nominal nuisances. One q0 per toy at
                      m_H=125.09 (Part 2.1).
  sig_injection    -- mu_true=`--mu-true` (0.5, 1, or 2), nominal
                      nuisances. One q0 + mu_hat per toy at m_H=125.09
                      (Part 2.2 AND Part 3.3's expected band at mu=1 --
                      the mu_true=1 sig_injection toy set IS the Part
                      3.3 toy set; no separate run needed, see
                      STATS_REPORT.md).
  spurious_check   -- mu_true=0, nominal nuisances, but the TRUTH used
                      to draw each toy has S_spur,c signal-shaped events
                      added on top of the model's own nu (a leakage-like
                      bias the theta_spur nuisance is supposed to
                      absorb) -- added directly to the truth counts, not
                      via the theta_spur parameter itself, since this
                      models a real background mismodeling, not a
                      fluctuation of the constrained nuisance (Part 2.3).
  mass_scan_bkg    -- mu_true=0, nominal nuisances. ONE null fit per toy
                      (does not depend on the scanned mass -- the
                      atlas_hgg_repro lesson) reused across an 81-point
                      110-150 GeV / 0.5 GeV scan of alt(mu free) fits;
                      records the max local Z over the scan per toy
                      (Part 3.5, look-elsewhere).

Usage:
    python studies/hgg_cms/stats/cluster/run_toy_job.py \\
        --job-type bkg_only --n-toys 200 --seed 20260918001 \\
        --out /storage/agrp/berkom/atlas-utilization/output/hgg_stats/bkg_only/job_0001.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.stats import model as M  # noqa: E402
from studies.hgg_cms.stats import fit as F  # noqa: E402

MH_NOMINAL = 125.09
MASS_SCAN = np.arange(110.0, 150.0 + 0.25, 0.5)


def run_bkg_only(rng, names, base, n_toys):
    out = []
    for i in range(n_toys):
        info = F.toy_q0(rng, base, MH_NOMINAL, names, seed_base=10_000 + 7 * i)
        out.append({"q0": info["q0"], "Z": info["Z"], "mu_hat": info["mu_hat"],
                     "failed": info["failed"], "retried": info["retried"],
                     "mu_err": info["mu_err"], "n_obs_total": info["n_obs_total"],
                     "null_fmin": info["null_fmin"], "alt_fmin": info["alt_fmin"],
                     "alt_fmin_post_hesse": info["alt_fmin_post_hesse"]})
    return out


def run_sig_injection(rng, names, base, n_toys, mu_true):
    par_true = dict(base)
    par_true["mu"] = mu_true
    out = []
    for i in range(n_toys):
        info = F.toy_q0(rng, par_true, MH_NOMINAL, names, seed_base=20_000 + 7 * i)
        out.append({"q0": info["q0"], "Z": info["Z"], "mu_hat": info["mu_hat"],
                     "failed": info["failed"], "retried": info["retried"],
                     "mu_err": info["mu_err"], "n_obs_total": info["n_obs_total"],
                     "null_fmin": info["null_fmin"], "alt_fmin": info["alt_fmin"],
                     "alt_fmin_post_hesse": info["alt_fmin_post_hesse"]})
    return out


def run_spurious_check(rng, names, base, n_toys):
    mi = M.get_model_inputs()
    edges = M.edges()
    leak_probs = {}
    for cat in M.CATEGORIES:
        ci = mi.categories[cat]
        shape = M.signal_shape_for(ci, MH_NOMINAL, 0.0, 0.0)
        leak_probs[cat] = shape.bin_probabilities(edges)

    par_true = dict(base)
    par_true["mu"] = 0.0
    out = []
    for i in range(n_toys):
        nu = {cat: M.expected_counts(cat, par_true, MH_NOMINAL, edges)
              + mi.categories[cat].S_spur * leak_probs[cat] for cat in M.CATEGORIES}
        toy = {cat: rng.poisson(nu[cat]).astype(float) for cat in M.CATEGORIES}
        null_fit = F.fit_model(toy, MH_NOMINAL, names, mu_fixed=0.0, n_starts=1,
                                seed=30_000 + 7 * i, base_start=par_true)
        alt_fit = F.fit_model(toy, MH_NOMINAL, names, mu_fixed=None, n_starts=1,
                               seed=30_001 + 7 * i,
                               base_start=null_fit.params if null_fit.valid else par_true)
        info = F.q0_from_fits(null_fit, alt_fit)
        failed = not (info["invariant_ok"] and info["both_valid"] and null_fit.valid and alt_fit.valid)
        if failed:
            alt_fit2 = F.fit_model(toy, MH_NOMINAL, names, mu_fixed=None, n_starts=1,
                                    seed=30_002 + 7 * i, base_start=par_true)
            info2 = F.q0_from_fits(null_fit, alt_fit2)
            if info2["nll_alt"] < info["nll_alt"]:
                # alt_fit must be swapped too -- info alone was swapped
                # here before this fix, leaving mu_err/alt_fmin below
                # describing the DISCARDED original fit instead of the
                # one info["mu_hat"]/q0/Z actually came from (found
                # diagnosing the 18 Sep 2026 validation run).
                alt_fit, info = alt_fit2, info2
            failed = not (info["invariant_ok"] and info["both_valid"])
        n_obs_total = float(sum(toy[cat].sum() for cat in toy))
        # fmin captured BEFORE mu_hesse_error(): an explicit .hesse()
        # call recomputes the covariance and can change fmin's flags --
        # see fit.toy_q0's own comment on this same ordering issue.
        null_fmin = F.fmin_diagnostics(null_fit)
        alt_fmin = F.fmin_diagnostics(alt_fit)
        mu_err = F.mu_hesse_error(alt_fit)
        alt_fmin_post_hesse = F.fmin_diagnostics(alt_fit)
        out.append({"q0": info["q0"], "Z": info["Z"], "mu_hat": info["mu_hat"], "failed": failed,
                     "mu_err": mu_err, "n_obs_total": n_obs_total,
                     "null_fmin": null_fmin, "alt_fmin": alt_fmin,
                     "alt_fmin_post_hesse": alt_fmin_post_hesse})
    return out


def run_mass_scan_bkg(rng, names, base, n_toys):
    """A toy is `any_failed=True` if EVEN ONE of its 81 scanned mass
    points' alt fit is invalid, or its own single null fit is invalid
    -- `n_failed_points` (new) records exactly how many of the 81 that
    was, for real diagnosis rather than just the boolean."""
    out = []
    for i in range(n_toys):
        toy = F.generate_toy(rng, base, MH_NOMINAL)
        null_fit = F.fit_model(toy, MH_NOMINAL, names, mu_fixed=0.0, n_starts=1,
                                seed=40_000 + 100 * i, base_start=base)
        zs = []
        alt_base = null_fit.params if null_fit.valid else base
        n_failed_points = 0
        worst_alt_fmin = {}
        for j, mH in enumerate(MASS_SCAN):
            alt_fit = F.fit_model(toy, float(mH), names, mu_fixed=None, n_starts=1,
                                   seed=40_001 + 100 * i + j, base_start=alt_base)
            info = F.q0_from_fits(null_fit, alt_fit)
            zs.append(info["Z"])
            if alt_fit.valid:
                alt_base = alt_fit.params
            else:
                n_failed_points += 1
                if not worst_alt_fmin:
                    worst_alt_fmin = F.fmin_diagnostics(alt_fit)
        any_failed = (not null_fit.valid) or (n_failed_points > 0)
        n_obs_total = float(sum(toy[cat].sum() for cat in toy))
        out.append({"max_Z": float(np.max(zs)), "max_Z_mH": float(MASS_SCAN[int(np.argmax(zs))]),
                     "Z_scan": zs, "any_failed": any_failed, "n_failed_points": n_failed_points,
                     "null_valid": bool(null_fit.valid), "n_obs_total": n_obs_total,
                     "null_fmin": F.fmin_diagnostics(null_fit),
                     "first_failed_point_fmin": worst_alt_fmin})
    return out


JOB_TYPES = {
    "bkg_only": run_bkg_only,
    "sig_injection": run_sig_injection,
    "spurious_check": run_spurious_check,
    "mass_scan_bkg": run_mass_scan_bkg,
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job-type", required=True, choices=list(JOB_TYPES))
    p.add_argument("--n-toys", required=True, type=int)
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--mu-true", type=float, default=0.0, help="only used by sig_injection")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    t0 = time.time()
    names = M.full_param_names()
    base = F.default_start(names, mu_start=0.0)
    rng = np.random.default_rng(args.seed)

    if args.job_type == "sig_injection":
        results = run_sig_injection(rng, names, base, args.n_toys, args.mu_true)
    else:
        results = JOB_TYPES[args.job_type](rng, names, base, args.n_toys)

    out = {
        "job_type": args.job_type, "n_toys": args.n_toys, "seed": args.seed,
        "mu_true": args.mu_true if args.job_type == "sig_injection" else
                   (0.0 if args.job_type != "spurious_check" else 0.0),
        "results": results, "elapsed_sec": time.time() - t0,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {out_path} ({time.time() - t0:.1f}s, {args.n_toys} toys)")


if __name__ == "__main__":
    main()
