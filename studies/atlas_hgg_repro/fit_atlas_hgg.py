"""
Part A2/A3: fit the extracted ATLAS Figure 4(a) diphoton spectrum with
lr_core's plain-polynomial background model, reproducing the profiled
local/global significance ATLAS itself would have seen for this single
histogram (NOT their full multi-category combination -- see REPORT.md).

Model: background = 4th-order plain polynomial in x=(m-100)/55 (guarded
against negative density, see lr_core.polynomial_shape_density); signal =
Gaussian integrated per bin, with signal-strength parameter mu used
directly as the signal YIELD in events (s_ref=1.0, so mu_hat IS the fitted
number of signal events -- there is no separate "reference yield" concept
needed for a single real dataset).
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent / "lr_toys"))
import lr_core as lc

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"

X_MIN, X_SCALE = 100.0, 55.0
N_COEFFS = 5  # 4th-order polynomial: c0..c4
MH_BOUNDS = (110.0, 150.0)
SIGMA_BOUNDS = (0.5, 6.0)
SEED_GLOBAL_SIG = 70_001
# Reduced from an initial 3000: timed directly on this machine (after fixing
# the n_bkg-start-value bug and switching the hot-loop fits to
# Minuit strategy=0) at ~0.82 s/toy for the full 41-point scan, so 3000
# toys would take ~41 minutes. 700 toys keeps this under ~10 minutes and
# is still enough for a stable Gross-Vitells estimate; see REPORT.md for
# the resulting statistical precision on the toy-based global p-value.
N_TOYS_GLOBAL = 700
MASS_SCAN = np.arange(110.0, 150.0001, 1.0)  # 1 GeV steps, 110-150 GeV


def load_data():
    edges = [100.0]
    counts = []
    with open(RESULTS_DIR / "atlas_hgg_fig4_points.csv") as f:
        for r in csv.DictReader(f):
            edges.append(float(r["bin_high_GeV"]))
            counts.append(float(r["count"]))
    return np.array(edges), np.array(counts)


def chi2_ndf(data, model, n_free_params):
    chi2 = float(np.sum((data - model) ** 2 / model))
    ndf = len(data) - n_free_params
    return chi2, ndf


def main():
    edges, data = load_data()
    nodes, weights = lc.gl_bin_nodes(edges)
    centers = lc.bin_centers(edges)
    print(f"Loaded {len(data)} bins, edges {edges[0]:.0f}-{edges[-1]:.0f} GeV, "
          f"total events {data.sum():.0f}")

    results = {}

    # --- Fit 1: background only ---
    t0 = time.time()
    fit1 = lc.fit_bkg_only_poly(data, nodes, weights, X_MIN, X_SCALE, n_coeffs=N_COEFFS)
    print(f"Fit 1 (bkg only): valid={fit1['valid']}, nll={fit1['nll']:.3f}, "
          f"n_bkg={fit1['n_bkg']:.1f}, coeffs={fit1['coeffs']}, {time.time()-t0:.2f}s")
    b1 = lc.polynomial_bin_expectation(nodes, weights, fit1["n_bkg"], fit1["coeffs"], X_MIN, X_SCALE)
    chi2_1, ndf_1 = chi2_ndf(data, b1, n_free_params=1 + N_COEFFS)
    print(f"Fit 1: chi2/ndf = {chi2_1:.2f}/{ndf_1} = {chi2_1/ndf_1:.3f}")
    results["fit1_bkg_only"] = {
        "n_bkg": fit1["n_bkg"], "coeffs": fit1["coeffs"].tolist(),
        "chi2": chi2_1, "ndf": ndf_1, "chi2_per_ndf": chi2_1 / ndf_1, "valid": fit1["valid"],
    }

    # --- Fit 2: S+B, mh and sigma floating ---
    t0 = time.time()
    fit2 = lc.fit_full_poly_floating_mass_width(
        data, edges, nodes, weights, s_ref=1.0, x_min=X_MIN, x_scale=X_SCALE,
        n_coeffs=N_COEFFS, mu_start=50.0, mh_start=126.5, mh_bounds=MH_BOUNDS,
        sigma_start=2.0, sigma_bounds=SIGMA_BOUNDS, hesse=True,
    )
    print(f"Fit 2 (S+B, mh/sigma floating): valid={fit2['valid']}, nll={fit2['nll']:.3f}, "
          f"mu_hat={fit2['mu_hat']:.2f}+-{fit2['mu_err']:.2f}, "
          f"mh_hat={fit2['mh_hat']:.2f}+-{fit2['mh_err']:.2f}, "
          f"sigma_hat={fit2['sigma_hat']:.3f}+-{fit2['sigma_err']:.3f}, "
          f"n_bkg={fit2['n_bkg']:.1f}, {time.time()-t0:.2f}s")
    b2 = lc.polynomial_bin_expectation(nodes, weights, fit2["n_bkg"], fit2["coeffs"], X_MIN, X_SCALE)
    s2 = lc.signal_bin_expectation(edges, fit2["mu_hat"], 1.0, fit2["mh_hat"], fit2["sigma_hat"])
    chi2_2, ndf_2 = chi2_ndf(data, b2 + s2, n_free_params=4 + N_COEFFS)
    print(f"Fit 2: chi2/ndf = {chi2_2:.2f}/{ndf_2} = {chi2_2/ndf_2:.3f}")
    results["fit2_splusb_floating"] = {
        "mu_hat": fit2["mu_hat"], "mu_err": fit2["mu_err"],
        "mh_hat": fit2["mh_hat"], "mh_err": fit2["mh_err"],
        "sigma_hat": fit2["sigma_hat"], "sigma_err": fit2["sigma_err"],
        "n_bkg": fit2["n_bkg"], "coeffs": fit2["coeffs"].tolist(),
        "chi2": chi2_2, "ndf": ndf_2, "chi2_per_ndf": chi2_2 / ndf_2, "valid": fit2["valid"],
    }

    # --- Plot: Fig 15-like top panels ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.5, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1.2]})
    ax1.errorbar(centers, data, yerr=np.sqrt(data), fmt="ko", ms=4, elinewidth=0.8, label="ATLAS data (extracted)")
    ax1.plot(centers, b1, "b--", lw=1.4, label=f"Bkg-only fit (4th-order poly)")
    ax1.plot(centers, b2 + s2, "r-", lw=1.6,
              label=f"S+B fit ($m_H$={fit2['mh_hat']:.1f} GeV, $\\sigma$={fit2['sigma_hat']:.2f} GeV)")
    ax1.plot(centers, b2, "r:", lw=1.2, label="Bkg component of S+B fit")
    ax1.set_ylabel("Events / 2 GeV")
    ax1.set_title("ATLAS H$\\to\\gamma\\gamma$, arXiv:1207.7214 Fig. 4(a) -- reproduction fit")
    ax1.legend(fontsize=8)

    resid = (data - b2)
    ax2.bar(centers, resid, width=1.8, color="tab:gray", label="Data - Bkg(S+B fit)")
    ax2.plot(centers, s2, "r-", lw=1.6, label="Fitted signal")
    ax2.axhline(0, color="k", lw=0.8)
    ax2.set_xlabel("$m_{\\gamma\\gamma}$ [GeV]")
    ax2.set_ylabel("Events - Bkg")
    ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "A2_fit_result.png", dpi=140)
    plt.close(fig)

    # --- Profiled local significance at mh_hat ---
    # Warm-start every poly fit below from Fit 1/Fit 2's own converged
    # background (n_bkg ~ 62,000 for this dataset), not the module default
    # of N_BKG_TRUE=250,000 (the toy study's constant) -- starting MIGRAD
    # 4x too high on n_bkg was the diagnosed cause of the earlier stuck run.
    fit2_bkg_start = [fit2["n_bkg"]] + list(fit2["coeffs"])
    null = lc.fit_bkg_only_poly(data, nodes, weights, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                 n_bkg_start=fit1["n_bkg"])
    alt_floating = lc.fit_full_poly_floating_width(
        data, edges, nodes, weights, s_ref=1.0, mh=fit2["mh_hat"], x_min=X_MIN, x_scale=X_SCALE,
        n_coeffs=N_COEFFS, mu_start=fit2["mu_hat"], sigma_start=fit2["sigma_hat"],
        sigma_bounds=SIGMA_BOUNDS, bkg_start=fit2_bkg_start,
    )
    q0_floating = lc.q0_from_nll(null["nll"], alt_floating["nll"], alt_floating["mu_hat"])
    z_floating = lc.z_from_q0(q0_floating)

    alt_fixed_width = lc.fit_full_poly(
        data, edges, nodes, weights, s_ref=1.0, mh=fit2["mh_hat"], sigma=fit2["sigma_hat"],
        x_min=X_MIN, x_scale=X_SCALE, n_coeffs=N_COEFFS, mu_start=fit2["mu_hat"],
        bkg_start=fit2_bkg_start,
    )
    q0_fixed = lc.q0_from_nll(null["nll"], alt_fixed_width["nll"], alt_fixed_width["mu_hat"])
    z_fixed = lc.z_from_q0(q0_fixed)

    print(f"\nLocal significance at mh={fit2['mh_hat']:.2f} GeV:")
    print(f"  width floating (bounded {SIGMA_BOUNDS}): Z = {z_floating:.3f}")
    print(f"  width fixed at {fit2['sigma_hat']:.3f} GeV: Z = {z_fixed:.3f}")
    results["local_significance"] = {
        "mh_hat": fit2["mh_hat"], "z_width_floating": z_floating, "z_width_fixed": z_fixed,
        "sigma_hat_used_for_fixed": fit2["sigma_hat"],
    }

    # --- Mass scan for global significance (width fixed at sigma_hat) ---
    print(f"\nScanning {len(MASS_SCAN)} mass points {MASS_SCAN[0]}-{MASS_SCAN[-1]} GeV on real data...")
    local_z_obs = np.zeros(len(MASS_SCAN))
    scan_bkg_start = fit2_bkg_start
    scan_mu_start = fit2["mu_hat"]
    for i, mh in enumerate(MASS_SCAN):
        alt = lc.fit_full_poly(data, edges, nodes, weights, s_ref=1.0, mh=mh, sigma=fit2["sigma_hat"],
                                x_min=X_MIN, x_scale=X_SCALE, n_coeffs=N_COEFFS,
                                mu_start=max(scan_mu_start, 0.0), bkg_start=scan_bkg_start)
        q0 = lc.q0_from_nll(null["nll"], alt["nll"], alt["mu_hat"])
        local_z_obs[i] = lc.z_from_q0(q0)
        scan_bkg_start = [alt["n_bkg"]] + list(alt["coeffs"])
        scan_mu_start = alt["mu_hat"]
    max_z_obs = local_z_obs.max()
    max_z_mh = MASS_SCAN[np.argmax(local_z_obs)]
    print(f"Observed max local Z = {max_z_obs:.3f} at mh = {max_z_mh:.1f} GeV")

    # Toy-based + Gross-Vitells global significance: generate background-only
    # toys around Fit 1's best estimate, repeat the same scan.
    rng = np.random.default_rng(SEED_GLOBAL_SIG)
    u0 = 1.0
    max_local_z_toys = np.full(N_TOYS_GLOBAL, np.nan)
    n_up = np.full(N_TOYS_GLOBAL, np.nan)
    t0 = time.time()
    for t in range(N_TOYS_GLOBAL):
        toy = rng.poisson(b1)
        # Warm-start at Fit 1's own n_bkg (~data.sum()), not N_BKG_TRUE=250,000.
        toy_null = lc.fit_bkg_only_poly(toy, nodes, weights, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                         n_bkg_start=fit1["n_bkg"])
        if not toy_null["valid"]:
            continue
        if (t + 1) % max(1, N_TOYS_GLOBAL // 20) == 0 or t < 5:
            print(f"  toy {t + 1}/{N_TOYS_GLOBAL} ({time.time() - t0:.1f}s elapsed, "
                  f"{(time.time() - t0) / (t + 1) * 1000:.1f} ms/toy so far)", flush=True)
        local_q0 = np.full(len(MASS_SCAN), np.nan)
        ok = True
        bkg_start = [toy_null["n_bkg"]] + list(toy_null["coeffs"])
        mu_start = 0.0
        for j, mh in enumerate(MASS_SCAN):
            alt = lc.fit_full_poly(toy, edges, nodes, weights, s_ref=1.0, mh=mh, sigma=fit2["sigma_hat"],
                                    x_min=X_MIN, x_scale=X_SCALE, n_coeffs=N_COEFFS,
                                    mu_start=max(mu_start, 0.0), bkg_start=bkg_start)
            if not alt["valid"]:
                ok = False
                break
            local_q0[j] = lc.q0_from_nll(toy_null["nll"], alt["nll"], alt["mu_hat"])
            bkg_start = [alt["n_bkg"]] + list(alt["coeffs"])
            mu_start = alt["mu_hat"]
        if not ok:
            continue
        max_local_z_toys[t] = np.sqrt(np.nanmax(local_q0))
        above = local_q0 >= u0
        n_up[t] = np.sum((~above[:-1]) & above[1:])
    dt = time.time() - t0
    valid_toys = ~np.isnan(max_local_z_toys)
    n_valid = int(valid_toys.sum())
    print(f"Global-significance toys: {n_valid}/{N_TOYS_GLOBAL} valid, {dt:.1f}s")

    n_up_mean = float(np.nanmean(n_up[valid_toys]))
    toy_global_p = float(np.mean(max_local_z_toys[valid_toys] >= max_z_obs))
    gv_global_p = float((1 - stats.norm.cdf(max_z_obs)) +
                        n_up_mean * np.exp(-(max_z_obs ** 2 - u0) / 2.0))
    local_p = float(1 - stats.norm.cdf(max_z_obs))
    print(f"At observed max local Z={max_z_obs:.3f}: local p={local_p:.4g}, "
          f"toy-based global p={toy_global_p:.4g} (N_valid={n_valid}), "
          f"Gross-Vitells global p={gv_global_p:.4g} (<N(u0)>={n_up_mean:.3f})")

    results["global_significance"] = {
        "mass_scan_range_GeV": [float(MASS_SCAN[0]), float(MASS_SCAN[-1])],
        "mass_scan_step_GeV": 1.0,
        "observed_max_local_z": float(max_z_obs), "observed_max_local_z_mh": float(max_z_mh),
        "local_p_value": local_p,
        "n_toys": N_TOYS_GLOBAL, "n_valid_toys": n_valid, "seed": SEED_GLOBAL_SIG,
        "toy_based_global_p": toy_global_p,
        "gross_vitells_global_p": gv_global_p, "gv_mean_upcrossings_u0": n_up_mean,
        "implied_trials_factor": (toy_global_p / local_p) if toy_global_p > 0 else None,
    }

    # Save local Z(mh) curve for A3's overlay reuse
    np.savez(RESULTS_DIR / "_a2_local_z_curve.npz", mass_scan=MASS_SCAN, local_z=local_z_obs)

    with open(RESULTS_DIR / "atlas_hgg_fit_results.json", "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\nWrote {RESULTS_DIR / 'atlas_hgg_fit_results.json'}")
    return fit1, fit2, edges, data, nodes, weights


if __name__ == "__main__":
    main()
