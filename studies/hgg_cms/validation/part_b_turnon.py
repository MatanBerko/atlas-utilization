"""
Implementation task 6, Part 3B: low-edge (turn-on) exploratory check.

Pre-set scope (do not change after seeing results):
  - Fit an exponential (N(m) = A*exp(-b*m)) and a power law
    (N(m) = A*m^(-b)) to INCLUSIVE sideband data, 1 GeV bins, over
    105-115 u 135-180 GeV ONLY (100-105 excluded from the fit).
  - Extrapolate each fit into 100-105 GeV and compare its predicted total
    count there against the OBSERVED 100-105 total.
  - Pre-set flag: if the observed total deviates from BOTH extrapolations
    by more than 3 sigma (Poisson on the observed count, combined in
    quadrature with the fit's own extrapolation uncertainty -- from the
    fit covariance, propagated by a parameter Monte Carlo), flag
    "possible turn-on/edge effect" and suggest a fit range starting at
    105 or 110 GeV for the later background-model task.
  - This is EXPLORATORY ONLY. The final background fit range is decided
    in the background-model task, not here, regardless of this check's
    outcome -- stated explicitly either way below.

This is the one fit this task's rules explicitly allow (a simple smooth
fit to sideband data for this edge check) -- no signal-plus-background
fit, no background-model selection, no significance here.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from studies.hgg_cms.validation import common

OUT_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = OUT_DIR / "plots"

FIT_LO_EXCLUDE_HI = 105.0  # exclude [100,105) from the fit
N_MC = 20000
RNG_SEED = 20260916


def exponential(m, A, b):
    return A * np.exp(-b * m)


def power_law(m, A, b):
    return A * np.power(m, -b)


def fit_and_extrapolate(centers, counts, errs, func, p0):
    fit_mask = ((centers >= FIT_LO_EXCLUDE_HI) & (centers < common.BLIND_LO)) | (centers > common.BLIND_HI)
    x, y, yerr = centers[fit_mask], counts[fit_mask], errs[fit_mask]
    popt, pcov = curve_fit(func, x, y, p0=p0, sigma=yerr, absolute_sigma=True, maxfev=20000)

    # chi2/ndf of the fit itself, over the fitted range
    resid = (y - func(x, *popt)) / yerr
    chi2 = float(np.sum(resid ** 2))
    ndf = len(x) - len(popt)

    # Extrapolate into 100-105 (5 x 1 GeV bins), with fit uncertainty
    # propagated by sampling the parameter covariance (robust for a
    # nonlinear function, avoids deriving an analytic Jacobian by hand).
    lo_edges = np.arange(common.SIDEBAND_LO, FIT_LO_EXCLUDE_HI, 1.0)
    lo_centers = lo_edges + 0.5
    rng = np.random.default_rng(RNG_SEED)
    try:
        samples = rng.multivariate_normal(popt, pcov, size=N_MC)
    except np.linalg.LinAlgError:
        samples = np.tile(popt, (N_MC, 1))
    pred_totals = func(lo_centers[None, :], samples[:, 0:1], samples[:, 1:2]).sum(axis=1)
    pred_mean = float(np.mean(pred_totals))
    pred_std = float(np.std(pred_totals))

    return {
        "params": {"A": float(popt[0]), "b": float(popt[1])},
        "param_errs": {"A": float(np.sqrt(pcov[0, 0])), "b": float(np.sqrt(pcov[1, 1]))},
        "chi2": chi2, "ndf": ndf, "chi2_over_ndf": chi2 / ndf if ndf > 0 else None,
        "predicted_100_105_total": pred_mean,
        "predicted_100_105_total_fit_uncertainty": pred_std,
    }, popt, func


def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data = common.load_data_sidebands()
    mgg = np.asarray(data["m_gg"])

    bins = np.arange(common.SIDEBAND_LO, common.SIDEBAND_HI + 1, 1.0)
    counts, edges = np.histogram(mgg, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    errs = np.sqrt(np.maximum(counts, 1))  # avoid zero-error bins (only occurs inside the blinded band, excluded from fit anyway)

    observed_100_105 = int(counts[(centers >= 100.0) & (centers < 105.0)].sum())
    observed_100_105_err = float(np.sqrt(observed_100_105))

    exp_result, exp_popt, _ = fit_and_extrapolate(
        centers, counts, errs, exponential, p0=(counts[centers < 110].mean(), 0.02)
    )
    pow_result, pow_popt, _ = fit_and_extrapolate(
        centers, counts, errs, power_law, p0=(counts[centers < 110].mean() * 100 ** 2, 2.0)
    )

    def significance(pred_mean, pred_std):
        total_sigma = np.sqrt(observed_100_105_err ** 2 + pred_std ** 2)
        return float((observed_100_105 - pred_mean) / total_sigma) if total_sigma > 0 else None

    exp_sig = significance(exp_result["predicted_100_105_total"], exp_result["predicted_100_105_total_fit_uncertainty"])
    pow_sig = significance(pow_result["predicted_100_105_total"], pow_result["predicted_100_105_total_fit_uncertainty"])

    flagged = abs(exp_sig) > 3.0 and abs(pow_sig) > 3.0

    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.axvspan(common.BLIND_LO, common.BLIND_HI, color="#bdbdbd", alpha=0.6, label="blinded")
    ax.axvspan(common.SIDEBAND_LO, FIT_LO_EXCLUDE_HI, color="#f2e6ce", alpha=0.7, label="extrapolation region (100-105, excluded from fit)")
    ax.errorbar(centers, counts, yerr=errs, fmt="o", color="#1a1a1a", markersize=3, elinewidth=0.8, label="data (1 GeV bins)")
    xx = np.linspace(common.SIDEBAND_LO, common.SIDEBAND_HI, 400)
    ax.plot(xx, exponential(xx, *exp_popt), color="#0072B2", linewidth=1.5,
            label=f"exponential fit (105-115 u 135-180), $\\chi^2$/ndf={exp_result['chi2_over_ndf']:.2f}")
    ax.plot(xx, power_law(xx, *pow_popt), color="#D55E00", linewidth=1.5, linestyle="--",
            label=f"power law fit (105-115 u 135-180), $\\chi^2$/ndf={pow_result['chi2_over_ndf']:.2f}")
    ax.set_xlabel("$m_{\\gamma\\gamma}$ [GeV]")
    ax.set_ylabel("events / GeV")
    ax.set_title("Low-edge (turn-on) exploratory check -- inclusive sidebands")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "part_b_turnon.png", dpi=150)
    plt.close(fig)

    result = {
        "fit_range": "105-115 GeV and 135-180 GeV (1 GeV bins), 100-105 excluded",
        "extrapolation_region": "100-105 GeV",
        "observed_100_105_total": observed_100_105,
        "observed_100_105_poisson_uncertainty": observed_100_105_err,
        "exponential_fit": exp_result,
        "power_law_fit": pow_result,
        "exponential_deviation_significance_sigma": exp_sig,
        "power_law_deviation_significance_sigma": pow_sig,
        "flag_possible_turn_on_edge_effect": flagged,
        "pre_set_flag_rule": "flag only if |significance| > 3 sigma for BOTH extrapolations",
        "note_final_fit_range_decision": (
            "This check is exploratory only. The final background-model fit "
            "range is decided in the background-model task, independent of "
            "this result."
        ),
    }
    (OUT_DIR / "part_b_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {OUT_DIR / 'part_b_results.json'} and plot to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
