#!/usr/bin/env python3
"""
Stage 4 of the H -> gamma gamma rediscovery exercise: a conventional
signal-plus-background fit to Stage 3's existing diphoton mass histogram.

Deliberately deferred in Stage 3. Does NOT use BumpNet (absent from this
machine, out of scope). Works entirely from Stage 3's existing 1 GeV
(80-bin, 100-180 GeV) BumpNet-format histogram
(reports/higgs_diphoton_stage3_resolution/histograms/diphoton_stage3_1gev_bumpnet.root)
-- NO re-download, no re-parse. Bin edges land exactly on integer GeV, so
narrower fit ranges (105-180, 110-180) are exact sub-selections of the same
80 bins, not a rebinning or recomputation.

METHODOLOGY (stated plainly so every number here is reproducible):

  - Binned Poisson maximum-likelihood fits (not chi2 least-squares) --
    standard for histograms like this. Model per bin i is evaluated as the
    background/signal DENSITY at the bin CENTER times the bin width, same
    convention Stage 3's own polynomial fit used (evaluate at bin centers).
  - Three background functional forms (F3): 4th-order polynomial (5 free
    params, matches Stage 3), exp(a+b*m+c*m^2) (3 free params), and a power
    law N*m^-k (2 free params).
  - Signal: a Gaussian with FIXED width (F4 -- a free width can inflate to
    absorb background mis-modeling and manufacture a fake signal) and a
    floating mean, bounded to [118,132] GeV so the fit cannot wander to the
    range edges and become degenerate with the background. Width fixed at
    1.5 GeV, the middle of CMS's quoted ~1-2 GeV diphoton mass resolution
    at m=125 GeV for an inclusive (non-per-category) selection -- see the
    report for why this exact value and its limits.
  - Local significance: Z = sqrt(2*(NLL_bkg_only - NLL_signal+bkg)), i.e.
    the standard 1-dof asymptotic likelihood-ratio significance for the
    signal-strength parameter (Wilks/Chernoff), profiling over the floating
    mass and all background parameters as nuisance parameters -- the same
    convention ATLAS/CMS call "local significance." Because the mass was
    allowed to float rather than fixed a priori at exactly 125.0 GeV, this
    is explicitly LOCAL, NOT corrected for the look-elsewhere effect --
    see the report for the full discussion (F5).
  - chi2/ndf for background-only fits uses the standard Pearson statistic,
    Sum((n_i-mu_i)^2/mu_i), ndf = n_bins - n_background_params, as the
    goodness-of-fit figure requested in F3 (the fit itself is done via
    Poisson NLL, not by minimizing this chi2 directly, but at this bin
    scale -- thousands of entries/bin -- the two are numerically
    equivalent, as expected).

NO significance/p-value/sigma is asserted as evidence of a discovery
anywhere. Numbers are reported plainly, including a null result if that is
what the fit gives.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import optimize, stats

HIGGS_MASS_GEV = 125.0
FIXED_SIGMA_GEV = 1.5
MEAN_BOUNDS = (118.0, 132.0)

FIT_RANGES = [(100.0, 180.0), (105.0, 180.0), (110.0, 180.0)]
BACKGROUND_FUNCS = ["poly4", "exp_poly2", "power_law"]


def load_stage3_histogram(root_path: Path):
    import uproot

    f = uproot.open(root_path)
    name = [k for k in f.keys() if k.split(";")[0].endswith("width_1.0")][0]
    h = f[name]
    edges = np.asarray(h.axis().edges())
    counts = np.asarray(h.values())
    return edges, counts


def select_range(edges, counts, lo, hi):
    centers = 0.5 * (edges[:-1] + edges[1:])
    mask = (edges[:-1] >= lo - 1e-6) & (edges[1:] <= hi + 1e-6)
    return centers[mask], counts[mask], edges[:-1][mask], edges[1:][mask]


# ---- background model density functions (evaluated at bin centers) ----

# poly4 and exp_poly2 are evaluated on RESCALED mass, x=(m-140)/40 (maps
# 100->-1, 180->1), not raw mass. Reason: the raw-mass leading poly4
# coefficient multiplies m^4 (~1e8 for m~100-180), producing a gradient
# ~8 orders of magnitude larger than the signal yield/mean gradients --
# verified directly (numerical gradient at a representative point:
# ~1.2e8 for the leading poly4 coefficient vs ~0.01 for yield). With a
# single shared initial Hessian approximation (L-BFGS-B's default), that
# mismatch makes the optimizer's step size effectively zero for the small-
# gradient parameters -- confirmed as the actual cause (the signal yield
# parameter did not move at all from its start value before this fix, on
# both a pure-background and an injected-signal synthetic test). Rescaling
# keeps all parameters O(1-100) and fixes this; reported "coefficients" for
# these two models are therefore in the rescaled-x domain, stated as such
# wherever they're printed/saved.
MASS_CENTER, MASS_SCALE = 140.0, 40.0


def _scaled_m(m):
    return (m - MASS_CENTER) / MASS_SCALE


def bkg_poly4(m, params):
    return np.polyval(params, _scaled_m(m))


def bkg_exp_poly2(m, params):
    a, b, c = params
    x = _scaled_m(m)
    return np.exp(a + b * x + c * x ** 2)


def bkg_power_law(m, params):
    norm, k = params
    return norm * np.power(m, -k)


BKG_MODELS = {
    "poly4": {"func": bkg_poly4, "n_params": 5},
    "exp_poly2": {"func": bkg_exp_poly2, "n_params": 3},
    "power_law": {"func": bkg_power_law, "n_params": 2},
}


def bkg_initial_guess(name, centers, counts):
    if name == "poly4":
        return np.polyfit(_scaled_m(centers), counts, deg=4)
    if name == "exp_poly2":
        x = _scaled_m(centers)
        y = np.log(np.clip(counts, 1, None))
        X = np.vstack([np.ones_like(x), x, x ** 2]).T
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        return coef
    if name == "power_law":
        y = np.log(np.clip(counts, 1, None))
        X = np.vstack([np.ones_like(centers), np.log(centers)]).T
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        # y = log(norm) - k*log(m) -> coef = [log(norm), -k]
        return np.array([np.exp(coef[0]), -coef[1]])
    raise ValueError(name)


def gaussian_density(m, mean, sigma):
    return np.exp(-0.5 * ((m - mean) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))


def poisson_nll(mu, n):
    """
    -ln L up to an additive, PARAMETER-INDEPENDENT constant, computed as the
    Poisson deviance/2 (subtracting the saturated-model reference n*ln(n)-n
    per bin) rather than the raw mu - n*ln(mu) sum.

    Both forms have IDENTICAL derivatives w.r.t. the fit parameters (they
    differ only by a data-only constant), so every likelihood-ratio result
    in this script (which only ever uses NLL *differences*) is unaffected.
    The raw form's absolute magnitude scales with the total event count
    (O(1e6) here), which swamped the O(1) signal-sensitive part of the
    likelihood in floating point and caused the optimizer to see a
    numerically flat surface near the true minimum (verified: the signal
    yield parameter would not move at all from its starting value under the
    raw form). The deviance form keeps the objective at an O(1-1e3) scale
    regardless of total statistics, which is standard practice for exactly
    this numerical reason.
    """
    mu = np.clip(mu, 1e-9, None)
    n_safe = np.clip(n, 1e-9, None)
    n_log_n = np.where(n > 0, n * np.log(n_safe), 0.0)
    # (mu - n*ln(mu)) minus its value evaluated at mu=n (the saturated
    # model): (mu - n*ln(mu)) - (n - n*ln(n)) = mu - n - n*ln(mu) + n*ln(n).
    return np.sum(mu - n - n * np.log(mu) + n_log_n)


def fit_background_only(name, centers, counts, bin_width):
    model = BKG_MODELS[name]
    x0 = bkg_initial_guess(name, centers, counts)

    def nll(params):
        mu = model["func"](centers, params) * bin_width
        return poisson_nll(mu, counts)

    res = optimize.minimize(nll, x0, method="Nelder-Mead",
                             options={"maxiter": 20000, "xatol": 1e-8, "fatol": 1e-6})
    if not res.success:
        res = optimize.minimize(nll, res.x, method="Powell", options={"maxiter": 20000})
    mu_hat = model["func"](centers, res.x) * bin_width
    chi2 = float(np.sum((counts - mu_hat) ** 2 / np.clip(mu_hat, 1e-9, None)))
    ndf = len(centers) - model["n_params"]
    return {
        "params": res.x.tolist(), "nll": float(res.fun), "mu": mu_hat,
        "chi2": chi2, "ndf": ndf, "chi2_over_ndf": chi2 / ndf if ndf > 0 else float("nan"),
    }


def fit_signal_plus_background(name, centers, counts, bin_width, bkg_x0, sigma_fixed):
    model = BKG_MODELS[name]
    n_bkg = model["n_params"]

    def unpack(params):
        return params[:n_bkg], params[n_bkg], params[n_bkg + 1]

    def nll(params):
        bkg_p, yield_, mean = unpack(params)
        mu = model["func"](centers, bkg_p) * bin_width + \
            yield_ * gaussian_density(centers, mean, sigma_fixed) * bin_width
        return poisson_nll(mu, counts)

    x0 = np.concatenate([bkg_x0, [1.0, HIGGS_MASS_GEV]])
    bounds = [(None, None)] * n_bkg + [(0.0, None), MEAN_BOUNDS]
    res = optimize.minimize(nll, x0, method="L-BFGS-B", bounds=bounds,
                             options={"maxiter": 20000, "ftol": 1e-12})

    bkg_p, yield_hat, mean_hat = unpack(res.x)
    mu_hat = model["func"](centers, bkg_p) * bin_width + \
        yield_hat * gaussian_density(centers, mean_hat, sigma_fixed) * bin_width

    # Uncertainty on the yield from the local curvature of the NLL (a
    # standard finite-difference Hessian estimate; not a full MINOS/profile
    # scan, but a reasonable, transparent estimate given no iminuit here).
    yield_idx = n_bkg
    h = 1.0
    plus = np.array(res.x); plus[yield_idx] += h
    minus = np.array(res.x); minus[yield_idx] -= max(h, 0.0) if res.x[yield_idx] - h >= 0 else 0
    minus[yield_idx] = max(res.x[yield_idx] - h, 0.0)
    d2 = (nll(plus) - 2 * nll(res.x) + nll(minus)) / (h ** 2) if minus[yield_idx] != res.x[yield_idx] else np.nan
    yield_err = float(1.0 / np.sqrt(d2)) if d2 and d2 > 0 else float("nan")

    return {
        "bkg_params": bkg_p.tolist(), "yield": float(yield_hat), "yield_err": yield_err,
        "mean": float(mean_hat), "sigma_fixed": sigma_fixed, "nll": float(res.fun), "mu": mu_hat,
        "bkg_under_peak": float(np.sum(model["func"](centers, bkg_p) * bin_width *
                                        (np.abs(centers - mean_hat) <= 2 * sigma_fixed))),
    }


def significance_from_nll(nll_bkg, nll_sb):
    q = 2.0 * (nll_bkg - nll_sb)
    q = max(q, 0.0)
    return float(np.sqrt(q)), float(q)


def run_all_fits(edges, counts, free_width_check=True):
    results = {}
    for lo, hi in FIT_RANGES:
        centers, cts, _, _ = select_range(edges, counts, lo, hi)
        bin_width = 1.0
        range_key = f"{lo:.0f}-{hi:.0f}"
        results[range_key] = {}
        for bname in BACKGROUND_FUNCS:
            bkg_fit = fit_background_only(bname, centers, cts, bin_width)
            sb_fit = fit_signal_plus_background(bname, centers, cts, bin_width, bkg_fit["params"], FIXED_SIGMA_GEV)
            z, q = significance_from_nll(bkg_fit["nll"], sb_fit["nll"])
            results[range_key][bname] = {
                "bkg_fit": {k: v for k, v in bkg_fit.items() if k != "mu"},
                "sb_fit": {k: v for k, v in sb_fit.items() if k != "mu"},
                "test_stat_q": q, "local_significance_sigma": z,
            }
    return results


def run_free_width_variant(edges, counts, lo=100.0, hi=180.0, bname="poly4"):
    centers, cts, _, _ = select_range(edges, counts, lo, hi)
    bin_width = 1.0
    model = BKG_MODELS[bname]
    n_bkg = model["n_params"]
    bkg_fit = fit_background_only(bname, centers, cts, bin_width)

    def nll(params):
        bkg_p, yield_, mean, sigma = params[:n_bkg], params[n_bkg], params[n_bkg + 1], params[n_bkg + 2]
        mu = model["func"](centers, bkg_p) * bin_width + \
            yield_ * gaussian_density(centers, mean, sigma) * bin_width
        return poisson_nll(mu, cts)

    x0 = np.concatenate([bkg_fit["params"], [1.0, HIGGS_MASS_GEV, FIXED_SIGMA_GEV]])
    bounds = [(None, None)] * n_bkg + [(0.0, None), MEAN_BOUNDS, (0.3, 15.0)]
    res = optimize.minimize(nll, x0, method="L-BFGS-B", bounds=bounds,
                             options={"maxiter": 20000, "ftol": 1e-12})
    yield_hat, mean_hat, sigma_hat = res.x[n_bkg], res.x[n_bkg + 1], res.x[n_bkg + 2]
    z, q = significance_from_nll(bkg_fit["nll"], res.fun)
    return {
        "range": f"{lo:.0f}-{hi:.0f}", "background": bname,
        "yield": float(yield_hat), "mean": float(mean_hat), "sigma_free": float(sigma_hat),
        "test_stat_q": q, "local_significance_sigma": z,
        "warning": "FREE-WIDTH VARIANT -- width was allowed to float, unlike the primary fits. "
                    "Reported separately per instruction; not the primary result.",
    }


def plot_primary(edges, counts, sb_fit, bkg_fit, lo, hi, bname, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    centers, cts, _, _ = select_range(edges, counts, lo, hi)
    mu_bkg = BKG_MODELS[bname]["func"](centers, bkg_fit["params"]) * 1.0
    mu_sb = BKG_MODELS[bname]["func"](centers, sb_fit["bkg_params"]) * 1.0 + \
        sb_fit["yield"] * gaussian_density(centers, sb_fit["mean"], sb_fit["sigma_fixed"]) * 1.0
    residual = cts - mu_bkg

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
    )
    ax1.errorbar(centers, cts, yerr=np.sqrt(cts), fmt="o", ms=3.5, color="#222222",
                 label=f"data ({int(cts.sum()):,} entries, {lo:.0f}-{hi:.0f} GeV)")
    ax1.plot(centers, mu_bkg, color="#4477aa", lw=1.5, ls="--", label=f"background-only fit ({bname})")
    ax1.plot(centers, mu_sb, color="#cc3311", lw=1.8,
              label=f"signal({sb_fit['yield']:.0f}+/-{sb_fit['yield_err']:.0f})+background fit")
    ax1.axvline(sb_fit["mean"], color="#888888", ls=":", lw=1,
                 label=f"fitted mass = {sb_fit['mean']:.1f} GeV (width fixed {sb_fit['sigma_fixed']:.1f} GeV)")
    ax1.set_ylabel("candidates / 1 GeV")
    ax1.set_title(
        f"H->gamma gamma Stage 4 fit: {bname} background, {lo:.0f}-{hi:.0f} GeV range\n"
        "Statistical uncertainty only -- no systematics (energy scale, category splitting) included.\n"
        "NOT a discovery claim. See report for full caveats.",
        fontsize=8.7,
    )
    ax1.legend(fontsize=7.5)

    ax2.axhline(0, color="#888888", lw=1.0)
    ax2.bar(centers, residual, width=0.9, color="#999999", label="data - background-only fit")
    gauss_curve = sb_fit["yield"] * gaussian_density(centers, sb_fit["mean"], sb_fit["sigma_fixed"]) * 1.0
    ax2.plot(centers, gauss_curve, color="#cc3311", lw=1.8, label="fitted signal Gaussian")
    ax2.set_xlabel("diphoton invariant mass [GeV]")
    ax2.set_ylabel("data - bkg\n(counts)")
    ax2.legend(fontsize=7.5, loc="upper right")
    ax2.text(
        0.5, -0.42,
        "No third (significance) panel -- BumpNet inference is out of scope. "
        "Local significance is reported numerically in the text report, not on this plot.",
        transform=ax2.transAxes, ha="center", va="top", fontsize=7.2, style="italic", wrap=True,
    )
    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    plt.close(fig)


def plot_variation_summary(all_results, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ranges = list(all_results.keys())
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    x = np.arange(len(ranges))
    w = 0.25
    colors = {"poly4": "#4477aa", "exp_poly2": "#cc3311", "power_law": "#228833"}

    for i, bname in enumerate(BACKGROUND_FUNCS):
        yields = [all_results[r][bname]["sb_fit"]["yield"] for r in ranges]
        errs = [all_results[r][bname]["sb_fit"]["yield_err"] for r in ranges]
        axes[0].bar(x + (i - 1) * w, yields, w, yerr=errs, capsize=3, color=colors[bname], label=bname)
        sig = [all_results[r][bname]["local_significance_sigma"] for r in ranges]
        axes[1].bar(x + (i - 1) * w, sig, w, color=colors[bname], label=bname)

    axes[0].axhline(0, color="black", lw=0.8)
    axes[0].set_xticks(x); axes[0].set_xticklabels(ranges)
    axes[0].set_ylabel("fitted signal yield (events)")
    axes[0].set_title("Fitted signal yield vs. fit range & background model")
    axes[0].legend(fontsize=8)

    axes[1].set_xticks(x); axes[1].set_xticklabels(ranges)
    axes[1].set_ylabel("local significance (sigma)")
    axes[1].set_title("Local significance vs. fit range & background model\n(NOT corrected for look-elsewhere)")
    axes[1].legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage3-hist", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    edges, counts = load_stage3_histogram(args.stage3_hist)
    print(f"loaded Stage 3 histogram: {len(counts)} bins, {int(counts.sum()):,} entries, "
          f"{edges[0]:.0f}-{edges[-1]:.0f} GeV")

    all_results = run_all_fits(edges, counts)
    print(json.dumps(
        {r: {b: {"chi2_over_ndf": all_results[r][b]["bkg_fit"]["chi2_over_ndf"],
                  "yield": all_results[r][b]["sb_fit"]["yield"],
                  "yield_err": all_results[r][b]["sb_fit"]["yield_err"],
                  "mean": all_results[r][b]["sb_fit"]["mean"],
                  "sigma": all_results[r][b]["local_significance_sigma"]}
             for b in BACKGROUND_FUNCS} for r in all_results},
        indent=2))

    free_width_variants = [
        run_free_width_variant(edges, counts, lo=100.0, hi=180.0, bname="poly4"),
        run_free_width_variant(edges, counts, lo=105.0, hi=180.0, bname="poly4"),
        run_free_width_variant(edges, counts, lo=110.0, hi=180.0, bname="poly4"),
    ]
    for fw in free_width_variants:
        print("\nFree-width variant:", json.dumps(fw, indent=2))

    # Two primary panel plots, both poly4: Stage 3's original range (100-180,
    # known edge artifact) and a cleaner range (105-180) excluding it, shown
    # side by side deliberately so the range-sensitivity is visible directly
    # in the plots, not just in the numbers.
    plot_primary(
        edges, counts,
        all_results["100-180"]["poly4"]["sb_fit"], all_results["100-180"]["poly4"]["bkg_fit"],
        100.0, 180.0, "poly4",
        out / "plots" / "diphoton_stage4_fit_100_180.png",
    )
    plot_primary(
        edges, counts,
        all_results["105-180"]["poly4"]["sb_fit"], all_results["105-180"]["poly4"]["bkg_fit"],
        105.0, 180.0, "poly4",
        out / "plots" / "diphoton_stage4_fit_105_180.png",
    )
    plot_variation_summary(all_results, out / "plots" / "diphoton_stage4_variation_summary.png")

    stats_out = {
        "fixed_sigma_gev": FIXED_SIGMA_GEV,
        "mean_bounds": list(MEAN_BOUNDS),
        "fit_ranges": [f"{lo:.0f}-{hi:.0f}" for lo, hi in FIT_RANGES],
        "background_functions": BACKGROUND_FUNCS,
        "results": all_results,
        "free_width_variants": free_width_variants,
    }
    (out / "diphoton_stage4_fit_stats.json").write_text(json.dumps(stats_out, indent=2, default=str))
    print(f"\nwrote {out/'diphoton_stage4_fit_stats.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
