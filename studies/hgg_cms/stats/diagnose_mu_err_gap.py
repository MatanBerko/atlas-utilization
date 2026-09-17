"""
Statistical-model task: a larger, dedicated local sample (n=120 at
mu_true=1) to characterize WHY n_with_mu_err came out so low (~9%) in
the full-scale sig_injection pull-width rerun -- the earlier 46-toy
diagnostic sample's implied ~50% strict-valid-among-loose-valid rate
was too imprecise (and, it turned out, not representative) to explain
an ~9% full-scale rate. Tabulates, among LOOSE-VALID toys (not
`failed`), exactly which strict_valid sub-condition fails.

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

OUT_PATH = Path(__file__).resolve().parent / "results" / "diagnose_mu_err_gap.json"
SEED = 20260930 + 500  # disjoint from diagnose_run1.py's own seed for this mu_true
N_TOYS = 120


def main():
    names = M.full_param_names()
    base = F.default_start(names, mu_start=0.0)
    rng = np.random.default_rng(SEED)
    t0 = time.time()
    results = J.run_sig_injection(rng, names, base, N_TOYS, 1.0)
    dt = time.time() - t0
    print(f"n={N_TOYS}: {dt:.1f}s ({dt/N_TOYS:.2f}s/toy)", flush=True)

    n_loose_failed = sum(1 for r in results if r["failed"])
    loose_valid = [r for r in results if not r["failed"]]
    sub_flag_counts = {"has_accurate_covar_false": 0, "has_posdef_covar_false": 0,
                        "has_made_posdef_covar": 0, "hesse_failed": 0,
                        "mu_err_nonfinite_or_nonpositive": 0, "no_post_hesse_data": 0}
    n_strict_valid = 0
    for r in loose_valid:
        fmin = r.get("alt_fmin_post_hesse")
        mu_err = r.get("mu_err")
        if F.strict_valid(fmin, mu_err):
            n_strict_valid += 1
            continue
        if not fmin:
            sub_flag_counts["no_post_hesse_data"] += 1
            continue
        if fmin.get("has_accurate_covar") is False:
            sub_flag_counts["has_accurate_covar_false"] += 1
        if fmin.get("has_posdef_covar") is False:
            sub_flag_counts["has_posdef_covar_false"] += 1
        if fmin.get("has_made_posdef_covar"):
            sub_flag_counts["has_made_posdef_covar"] += 1
        if fmin.get("hesse_failed"):
            sub_flag_counts["hesse_failed"] += 1
        if not (np.isfinite(mu_err) and mu_err > 0):
            sub_flag_counts["mu_err_nonfinite_or_nonpositive"] += 1

    out = {
        "seed": SEED, "n_toys": N_TOYS, "n_loose_failed": n_loose_failed,
        "n_loose_valid": len(loose_valid), "n_strict_valid": n_strict_valid,
        "n_strict_invalid_among_loose_valid": len(loose_valid) - n_strict_valid,
        "strict_valid_rate_among_loose_valid": n_strict_valid / len(loose_valid) if loose_valid else None,
        "overall_usable_rate": n_strict_valid / N_TOYS,
        "sub_flag_counts_among_strict_invalid": sub_flag_counts,
    }
    print(json.dumps(out, indent=2), flush=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
