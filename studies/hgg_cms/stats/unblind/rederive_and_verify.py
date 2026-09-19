"""
Statistical-model task, Part 5.2 companion #2: a ONE-TIME deterministic
re-derivation of the primary unblinded fit's full parameter vector (not
saved by the gated `run_unblinded_analysis.py`, which only wrote the
scalar q0/Z/mu_hat summary), done so the headline "money plot" can show
the actual fitted curves instead of only being described by the summary
numbers.

This is NOT a new fit and NOT a re-analysis: it calls the exact same
`stats/fit.py` + `stats/model.py` building blocks, on the exact same
merged data file, with the exact same fixed seeds and starting points
as `run_unblinded_analysis.py` (primary null/alt: seed=1/2, n_starts=10,
base_start=default_start(mu_start=0.0)) and
`compute_expected_significance.py::_fit_with_restricted_nuisances` (per-
category: seed0=13/seed1=14, n_starts=10, only_category=<cat>) already
used, respectively, by the gated script itself and by
`stats/unblind/plots_unblinded.py` (already-committed, non-gated, run
after the gate). No model input, bound, start, or fit setting is
changed from those two already-existing call sites.

Before anything is written or plotted, this script:
  1. Prints a side-by-side comparison of the re-derived combined Z,
     p-value, mu_hat, and per-category Z/mu_hat against the values
     already recorded in
     `stats/results/unblinded/unblinded_result_20260917T211721Z.json`
     and `UNBLINDED_RESULT.md`. Any disagreement beyond floating-point
     noise (rtol=1e-4) is a hard stop -- nothing further runs.
  2. Re-renders `spectrum_EBEB.png`, `spectrum_notEBEB.png`, and
     `spectrum_combined_SB_weighted.png` using `plots_unblinded.py`'s
     OWN plotting code (unmodified) fed the re-derived parameters, into
     a throwaway directory, and pixel-diffs each against the
     already-committed file at
     `stats/results/plots/unblinded/<name>.png`. Any mismatch is a hard
     stop.

Only if every check above passes does it save the full re-derived
parameter vectors (null and alt fits, both categories' background
coefficients, all nuisance values, and the alt fit's Hesse covariance
matrix) to `stats/results/unblinded/rederived_fit_params_for_plotting.json`,
so this re-derivation never has to be repeated.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.output import read_output  # noqa: E402
from studies.hgg_cms.stats import model as M  # noqa: E402
from studies.hgg_cms.stats import fit as F  # noqa: E402
from studies.hgg_cms.stats import compute_expected_significance as CES  # noqa: E402
from studies.hgg_cms.stats.unblind import plots_unblinded as PU  # noqa: E402

MH_NOMINAL = 125.09
DATA_FILE = r"C:\Users\matan\hgg_full_merged\data_full_range.root"
STATS_RESULTS = Path(__file__).resolve().parents[1] / "results"
UNBLINDED_JSON = STATS_RESULTS / "unblinded" / "unblinded_result_20260917T211721Z.json"
COMMITTED_PLOTS_DIR = STATS_RESULTS / "plots" / "unblinded"
OUT_JSON = STATS_RESULTS / "unblinded" / "rederived_fit_params_for_plotting.json"

EXPECTED = {
    "combined_Z": 4.129217000006897,
    "combined_p": 1.82e-5,
    "combined_mu_hat": 1.0608589959541987,
    "EBEB_Z": 4.096797154621395,
    "EBEB_mu_hat": 1.1172013059597177,
    "notEBEB_Z": 0.8693444342552592,
    "notEBEB_mu_hat": 0.740956105124134,
}
RTOL = 1e-4


def load_real_data_counts():
    import awkward as ak
    events = read_output(DATA_FILE, unblind=True)
    edges = M.edges()
    cat_selector = {"EBEB": lambda e: e["category"] == "EBEB", "notEBEB": lambda e: e["category"] != "EBEB"}
    counts = {}
    for cat, sel in cat_selector.items():
        m = events["m_gg"][sel(events)]
        counts[cat], _ = np.histogram(ak.to_numpy(m), bins=edges)
    return counts


def check(name, got, want, rtol=RTOL):
    diff = abs(got - want)
    rel = diff / max(abs(want), 1e-300)
    ok = rel <= rtol
    print(f"  {name:16s} got={got!r:24}  want={want!r:24}  rel_diff={rel:.3e}  {'OK' if ok else 'MISMATCH'}")
    return ok


def pixel_diff(path_a: Path, path_b: Path) -> float:
    from PIL import Image
    a = np.asarray(Image.open(path_a).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(path_b).convert("RGB"), dtype=np.int16)
    if a.shape != b.shape:
        return float("inf")
    return float(np.abs(a - b).max())


def main():
    print("Loading real (unblinded) data and binning per category...")
    data_counts = load_real_data_counts()
    for cat, c in data_counts.items():
        print(f"  {cat}: {int(c.sum())} events in fit range")

    names = M.full_param_names()
    base = F.default_start(names, mu_start=0.0)

    print("\nRe-deriving primary combined fit (null seed=1, alt seed=2, n_starts=10) -- "
          "identical call to run_unblinded_analysis.py...")
    null = F.fit_model(data_counts, MH_NOMINAL, names, mu_fixed=0.0, n_starts=10, seed=1, base_start=base)
    alt = F.fit_model(data_counts, MH_NOMINAL, names, mu_fixed=None, n_starts=10, seed=2, base_start=base)
    q0info = F.q0_from_fits(null, alt)

    from scipy.stats import norm
    p_value = float(1.0 - norm.cdf(q0info["Z"]))

    print("\nRe-deriving per-category (full-model, single-category likelihood) fits -- "
          "identical call to run_unblinded_analysis.py's secondary/per_category section...")
    all_floating = set(names) - {"mu"} - {n for n in names if n.startswith("bkg_")}
    per_cat = {}
    for cat in M.CATEGORIES:
        r = CES._fit_with_restricted_nuisances(data_counts, names, base, all_floating, n_starts=10,
                                                 seed0=13, seed1=14, only_category=cat)
        per_cat[cat] = {"Z": r["q0info"]["Z"], "mu_hat": r["q0info"]["mu_hat"]}

    print("\n=== Comparison against stored unblinded result ===")
    ok = True
    ok &= check("combined_Z", q0info["Z"], EXPECTED["combined_Z"])
    ok &= check("combined_p", p_value, EXPECTED["combined_p"], rtol=2e-2)  # p quoted to 3 sig figs in the report
    ok &= check("combined_mu_hat", q0info["mu_hat"], EXPECTED["combined_mu_hat"])
    ok &= check("EBEB_Z", per_cat["EBEB"]["Z"], EXPECTED["EBEB_Z"])
    ok &= check("EBEB_mu_hat", per_cat["EBEB"]["mu_hat"], EXPECTED["EBEB_mu_hat"])
    ok &= check("notEBEB_Z", per_cat["notEBEB"]["Z"], EXPECTED["notEBEB_Z"])
    ok &= check("notEBEB_mu_hat", per_cat["notEBEB"]["mu_hat"], EXPECTED["notEBEB_mu_hat"])
    ok &= bool(q0info["invariant_ok"] and q0info["both_valid"])
    print(f"  invariant_ok={q0info['invariant_ok']} both_valid={q0info['both_valid']}")

    if not ok:
        print("\nSTOP: re-derived numbers do not match the stored gated result within tolerance. "
              "Not proceeding to plot generation.", file=sys.stderr)
        sys.exit(1)
    print("\nAll scalar checks PASSED -- re-derived fit reproduces the gated result.")

    print("\nRe-rendering spectrum plots from the re-derived parameters (plots_unblinded.py's own,"
          " unmodified plotting code) into a throwaway directory, to pixel-diff against the "
          "already-committed images...")
    edges_fine = M.edges()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        PU.PLOTS_DIR = tmp_dir
        for cat in M.CATEGORIES:
            PU.plot_category_spectrum(cat, data_counts, null.params, alt.params, edges_fine)
        weights = PU.plot_combined_sb_weighted(data_counts, null.params, alt.params, edges_fine)

        print("\n=== Pixel-diff against committed plots ===")
        all_match = True
        for fname in ("spectrum_EBEB.png", "spectrum_notEBEB.png", "spectrum_combined_SB_weighted.png"):
            d = pixel_diff(tmp_dir / fname, COMMITTED_PLOTS_DIR / fname)
            match = d == 0.0
            all_match &= match
            print(f"  {fname:36s} max_abs_pixel_diff={d}  {'IDENTICAL' if match else 'DIFFERS'}")

    if not all_match:
        print("\nSTOP: re-derived curves do not exactly reproduce the committed plots. "
              "Not proceeding.", file=sys.stderr)
        sys.exit(1)
    print("\nAll pixel checks PASSED -- re-derived curves exactly reproduce the committed plots.")

    print(f"\nCombined S/B weights (from plots_unblinded.py's own weighting): {weights}")

    # --- Save full re-derived parameter vectors + alt fit's Hesse covariance ---
    print("\nRunning HESSE on the alt (S+B) fit to get the covariance matrix for the background band...")
    alt.minuit.hesse()
    cov = alt.minuit.covariance
    cov_param_names = list(alt.minuit.parameters)
    cov_matrix = np.array(cov.tolist()) if cov is not None else None

    out = {
        "provenance": {
            "note": "Deterministic re-derivation of the already-reported primary unblinded fit, done "
                    "ONLY to obtain curve-plotting inputs not saved by the gated script. NOT a re-fit: "
                    "same code (stats/fit.py, stats/model.py, stats/compute_expected_significance.py), "
                    "same data file, same fixed seeds/n_starts/base_start as "
                    "run_unblinded_analysis.py and plots_unblinded.py. Verified against the gated "
                    "result and against the already-committed spectrum plots before being saved -- "
                    "see the printed comparison in the run log / FINAL_REPORT.md section 8.",
            "data_file": DATA_FILE,
            "mH_nominal": MH_NOMINAL,
        },
        "verification": {
            "combined_Z": q0info["Z"], "combined_p_value": p_value, "combined_mu_hat": q0info["mu_hat"],
            "per_category": per_cat,
            "matches_gated_result_within_rtol_1e-4": True,
            "matches_committed_spectrum_plots_pixel_identical": True,
        },
        "null_fit_params_mu_fixed_0": null.params,
        "alt_fit_params_mu_free": alt.params,
        "alt_fit_covariance": {
            "param_order": cov_param_names,
            "matrix": cov_matrix.tolist() if cov_matrix is not None else None,
        },
        "sb_weighted_combination_weights": weights,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
