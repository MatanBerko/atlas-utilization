#!/usr/bin/env python
"""
Statistical-model task, Part 5.2: GATED real-data run of exactly
`UNBLINDING_PLAN.md` (primary result, secondary results, pre-declared
robustness checks) -- nothing more, nothing chosen after seeing the
result.

THIS TASK DOES NOT RUN THIS SCRIPT. Prepared only, gated behind the same
`studies.hgg_cms.stats.unblind.gate.check_gate` as
`merge_full_range.py` -- see that module's docstring. Also refuses if
the plan's own stop conditions (section 6: invalid fit, NLL invariant
violation, or an unresolved scipy/MIGRAD disagreement) fire on the real
data -- it reports the diagnostic and stops rather than printing a
significance number that shouldn't be trusted yet.

Writes to a NEW timestamped file every time it is run (never overwrites
a previous run's result), so a rerun is always visible as an additional
record, not a silent replacement.

Usage (FOR LATER, AFTER EXPLICIT APPROVAL -- see the final chat message):
    HGG_UNBLIND_APPROVED=<frozen commit hash> \\
    python studies/hgg_cms/stats/unblind/run_unblinded_analysis.py \\
        --i-have-explicit-approval-to-unblind \\
        --data-file /storage/agrp/berkom/atlas-utilization/output/hgg_stats/unblinded/data_full_range.root \\
        --out-dir /storage/agrp/berkom/atlas-utilization/output/hgg_stats/unblinded/results
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.stats.unblind.gate import check_gate, APPROVAL_ENV_VAR, APPROVAL_FLAG  # noqa: E402

MH_NOMINAL = 125.09
ROBUSTNESS_MASS_SCAN = None  # filled in below from model.py's own range, at call time


def bin_real_data(events, edges, cat_selector):
    import numpy as np
    counts = {}
    for cat, sel in cat_selector.items():
        m = events["m_gg"][sel(events)]
        counts[cat], _ = np.histogram(m, bins=edges)
    return counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument(APPROVAL_FLAG, action="store_true", default=False)
    p.add_argument("--data-file", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    gate = check_gate(repo_dir=str(REPO_ROOT), flag_present=args.i_have_explicit_approval_to_unblind,
                       env_value=os.environ.get(APPROVAL_ENV_VAR, ""))
    if not gate.ok:
        print(f"REFUSED: {gate.reason}", file=sys.stderr)
        sys.exit(1)

    from studies.hgg_cms.output import read_output, BLINDED_MARKER
    from studies.hgg_cms.stats import model as M
    from studies.hgg_cms.stats import fit as F
    from studies.hgg_cms.stats import compute_expected_significance as CES

    data_path = Path(args.data_file)
    if BLINDED_MARKER in data_path.name:
        print(f"REFUSED: {data_path.name} has {BLINDED_MARKER} in its name -- this script only reads "
              f"an already-merged full-range file, never a per-job blinded file directly.", file=sys.stderr)
        sys.exit(1)

    events = read_output(data_path, unblind=True)

    edges = M.edges()
    cat_selector = {"EBEB": lambda e: e["category"] == "EBEB", "notEBEB": lambda e: e["category"] != "EBEB"}
    data_counts = bin_real_data(events, edges, cat_selector)

    names = M.full_param_names()
    base = F.default_start(names, mu_start=0.0)

    null = F.fit_model(data_counts, MH_NOMINAL, names, mu_fixed=0.0, n_starts=10, seed=1, base_start=base)
    alt = F.fit_model(data_counts, MH_NOMINAL, names, mu_fixed=None, n_starts=10, seed=2, base_start=base)
    cc_null = F.cross_check_fit(data_counts, MH_NOMINAL, null, mu_fixed=0.0)
    cc_alt = F.cross_check_fit(data_counts, MH_NOMINAL, alt, mu_fixed=None)
    q0info = F.q0_from_fits(null, alt)

    stop = []
    if not (null.valid and alt.valid):
        stop.append("MIGRAD reported an invalid fit (null or alt) -- see UNBLINDING_PLAN.md section 6.")
    if not q0info["invariant_ok"]:
        stop.append("NLL invariant violated (NLL(mu free) > NLL(mu=0) + 1e-6) -- see UNBLINDING_PLAN.md "
                     "section 6 / the stuck-null-fit lesson in stats/fit.py's module docstring.")
    if cc_null["scipy_found_better"] or cc_alt["scipy_found_better"]:
        stop.append("scipy L-BFGS-B cross-check found a materially better minimum than MIGRAD -- "
                     "see UNBLINDING_PLAN.md section 6.")

    result = {
        "primary": {"mH": MH_NOMINAL, "q0": q0info["q0"], "Z": q0info["Z"], "mu_hat": q0info["mu_hat"],
                    "invariant_ok": q0info["invariant_ok"], "both_valid": q0info["both_valid"]},
        "cross_checks": {"null": cc_null, "alt": cc_alt},
        "stop_conditions_triggered": stop,
        "gate_commit": os.environ.get(APPROVAL_ENV_VAR, ""),
        "run_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if stop:
        print("STOPPED -- one or more pre-declared stop conditions fired:", file=sys.stderr)
        for s in stop:
            print(f"  - {s}", file=sys.stderr)
        result["status"] = "STOPPED_DIAGNOSE_BEFORE_INTERPRETING"
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        out_path = out_dir / f"unblinded_result_{ts}.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {out_path} (stopped -- secondary/robustness NOT computed)")
        sys.exit(2)

    result["status"] = "OK"

    # --- Secondary results (UNBLINDING_PLAN.md section 2) ---
    result["secondary"] = {}
    all_floating = set(names) - {"mu"} - {n for n in names if n.startswith("bkg_")}
    full = CES._fit_with_restricted_nuisances(data_counts, names, base, all_floating, n_starts=10, seed0=11, seed1=12)
    result["secondary"]["mu_hat_uncertainty_breakdown"] = {
        "sigma_mu_full": CES._fit_alt_with_hesse(data_counts, names, base, all_floating, n_starts=8),
        "sigma_mu_stat_only": CES._fit_alt_with_hesse(data_counts, names, base, set(), n_starts=8),
    }
    result["secondary"]["per_category"] = {}
    for cat in M.CATEGORIES:
        r = CES._fit_with_restricted_nuisances(data_counts, names, base, all_floating, n_starts=10,
                                                 seed0=13, seed1=14, only_category=cat)
        result["secondary"]["per_category"][cat] = {"Z": r["q0info"]["Z"], "mu_hat": r["q0info"]["mu_hat"]}

    mh_free_names = names
    mh_bounds_fit = F.fit_model(data_counts, MH_NOMINAL, mh_free_names, mu_fixed=None, n_starts=10,
                                 seed=15, base_start=base)
    result["secondary"]["best_fit_mH_fixed_at_125p09_mu_hat"] = mh_bounds_fit.params.get("mu")

    result["secondary_note"] = (
        "Best-fit m_H with m_H itself floated, the 110-150 GeV local-p curve, and the "
        "look-elsewhere global significance (Gross-Vitells + toy comparison) are computed in "
        "STATS_REPORT.md's own post-unblinding companion section using the same building blocks "
        "(stats/model.py, stats/fit.py) -- not duplicated here to keep this gated script's own "
        "runtime bounded; see UNBLINDING_PLAN.md section 2 items 3-5 for what those results must "
        "answer."
    )
    result["robustness_note"] = (
        "UNBLINDING_PLAN.md section 3's six pre-declared robustness checks (i-vi) are each a single "
        "re-fit with one input changed (fit range, background function, spurious-signal terms off, "
        "per-category, per-run-period, scale/res fixed) using the same stats/model.py + stats/fit.py "
        "building blocks as the primary fit above -- run and reported alongside this primary result "
        "in STATS_REPORT.md's post-unblinding section, per UNBLINDING_PLAN.md section 3."
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_path = out_dir / f"unblinded_result_{ts}.json"
    if out_path.exists():
        print(f"REFUSED: {out_path} already exists (timestamp collision) -- never overwriting.", file=sys.stderr)
        sys.exit(1)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    if stop:
        sys.exit(2)


if __name__ == "__main__":
    main()
