"""
Part A3: compute four candidate definitions (V1-V4) of the bin-by-bin
SIGNED likelihood-ratio significance curve, and compare each against
BumpNet's own Z_LR curve (extracted by extract_bumpnet_fig15.py).

Range declared BEFORE computing anything below (per task instructions --
not chosen after seeing which matches best): full 100-160 GeV, all 30 bins
(mass = 101, 103, ..., 159 GeV) -- the SAME range as our own ATLAS Fig. 4(a)
extraction. This was verified, not assumed: BumpNet's Figure 15 visibly
displays only ~100-156 GeV, but the underlying Z_LR curve's own vector path
(extracted directly from the PDF) has 30 vertices on exactly our 30-bin
grid, with the last two (at 157 and 159 GeV) lying just past the plot's
drawn frame edge -- present in the data, invisible in the rendering. So the
plot's visible window was cropped for display; the calculation was not.
See REPORT.md for the full evidence trail.

V1: fixed background (= Fit 2's background component), signal width fixed
    at Fit 2's sigma_hat, only signal yield floats per mass point.
V2: same fixed background, but signal width = 2 GeV (one bin), matching
    BumpNet's own training convention (paper Sec. 2.1).
V3: background re-profiled (refit) under both mu=0 and mu free, signal
    width fixed at sigma_hat.
V4: like V3, with width = 2 GeV.

All four use the SIGNED convention: Z = sign(mu_hat) * sqrt(-2 ln lambda(0)),
never zeroed for mu_hat < 0.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent / "lr_toys"))
import lr_core as lc

HERE = Path(__file__).parent
RESULTS_DIR = HERE / "results"

X_MIN, X_SCALE = 100.0, 55.0
N_COEFFS = 5
MASS_POINTS = np.arange(101.0, 160.0, 2.0)  # 30 points: 101, 103, ..., 159

PASS_MAX_Z_TOL = 0.3
PASS_MASS_TOL_GEV = 2.0  # "same bin, +/-1 bin" = +/-2 GeV given 2 GeV bins
PASS_RMS_MAX = 0.3
PAPER_MAX_Z = 4.2
PAPER_MAX_Z_MASS = 126.5  # "at 126-128 GeV" per task description


def load_data():
    edges = [100.0]
    counts = []
    with open(RESULTS_DIR / "atlas_hgg_fig4_points.csv") as f:
        for r in csv.DictReader(f):
            edges.append(float(r["bin_high_GeV"]))
            counts.append(float(r["count"]))
    return np.array(edges), np.array(counts)


def load_bumpnet_curve():
    masses, zs = [], []
    with open(RESULTS_DIR / "bumpnet_fig15_zlr_curve.csv") as f:
        for r in csv.DictReader(f):
            masses.append(float(r["mass_GeV"]))
            zs.append(float(r["z_lr"]))
    return np.array(masses), np.array(zs)


def main():
    edges, data = load_data()
    nodes, weights = lc.gl_bin_nodes(edges)
    print(f"Loaded {len(data)} bins, total {data.sum():.0f} events")

    fit1 = lc.fit_bkg_only_poly(data, nodes, weights, X_MIN, X_SCALE, n_coeffs=N_COEFFS)
    fit2 = lc.fit_full_poly_floating_mass_width(
        data, edges, nodes, weights, s_ref=1.0, x_min=X_MIN, x_scale=X_SCALE,
        n_coeffs=N_COEFFS, mu_start=50.0, mh_start=126.5, mh_bounds=(110, 150),
        sigma_start=2.0, sigma_bounds=(0.5, 6.0),
    )
    sigma_fit2 = fit2["sigma_hat"]
    b_fixed = lc.polynomial_bin_expectation(nodes, weights, fit2["n_bkg"], fit2["coeffs"], X_MIN, X_SCALE)
    print(f"Fit 2: mh={fit2['mh_hat']:.2f}, sigma={sigma_fit2:.3f}, n_bkg={fit2['n_bkg']:.1f}")

    # Null for V3/V4 (profiled): same for every mass point (no signal at all).
    null_profiled = lc.fit_bkg_only_poly(data, nodes, weights, X_MIN, X_SCALE, n_coeffs=N_COEFFS,
                                          n_bkg_start=fit1["n_bkg"])
    # Null for V1/V2 (fixed background): background entirely fixed, no free params.
    nll_null_fixed = lc.poisson_nll(data, b_fixed)

    variants = {"V1": [], "V2": [], "V3": [], "V4": []}
    bkg_start = [fit1["n_bkg"]] + list(fit1["coeffs"])
    mu_start_v3, mu_start_v4 = 0.0, 0.0
    bkg_start_v3, bkg_start_v4 = list(bkg_start), list(bkg_start)

    for mh in MASS_POINTS:
        # V1: fixed bkg, width = sigma_fit2
        alt_v1 = lc.fit_mu_only(data, b_fixed, edges, s_ref=1.0, mh=mh, sigma=sigma_fit2)
        z_v1 = lc.signed_z_from_nll(nll_null_fixed, alt_v1["nll"], alt_v1["mu_hat"])
        variants["V1"].append(z_v1)

        # V2: fixed bkg, width = 2 GeV (one bin)
        alt_v2 = lc.fit_mu_only(data, b_fixed, edges, s_ref=1.0, mh=mh, sigma=2.0)
        z_v2 = lc.signed_z_from_nll(nll_null_fixed, alt_v2["nll"], alt_v2["mu_hat"])
        variants["V2"].append(z_v2)

        # V3: profiled, width = sigma_fit2
        alt_v3 = lc.fit_full_poly(data, edges, nodes, weights, s_ref=1.0, mh=mh, sigma=sigma_fit2,
                                   x_min=X_MIN, x_scale=X_SCALE, n_coeffs=N_COEFFS,
                                   mu_start=max(mu_start_v3, 0.0), bkg_start=bkg_start_v3)
        z_v3 = lc.signed_z_from_nll(null_profiled["nll"], alt_v3["nll"], alt_v3["mu_hat"])
        variants["V3"].append(z_v3)
        bkg_start_v3 = [alt_v3["n_bkg"]] + list(alt_v3["coeffs"])
        mu_start_v3 = alt_v3["mu_hat"]

        # V4: profiled, width = 2 GeV
        alt_v4 = lc.fit_full_poly(data, edges, nodes, weights, s_ref=1.0, mh=mh, sigma=2.0,
                                   x_min=X_MIN, x_scale=X_SCALE, n_coeffs=N_COEFFS,
                                   mu_start=max(mu_start_v4, 0.0), bkg_start=bkg_start_v4)
        z_v4 = lc.signed_z_from_nll(null_profiled["nll"], alt_v4["nll"], alt_v4["mu_hat"])
        variants["V4"].append(z_v4)
        bkg_start_v4 = [alt_v4["n_bkg"]] + list(alt_v4["coeffs"])
        mu_start_v4 = alt_v4["mu_hat"]

    for k in variants:
        variants[k] = np.array(variants[k])

    paper_mass, paper_z = load_bumpnet_curve()
    # MASS_POINTS and paper_mass should already be on the same grid; align
    # by nearest match rather than assuming exact float equality.
    paper_z_aligned = np.array([paper_z[np.argmin(np.abs(paper_mass - m))] for m in MASS_POINTS])

    results = {}
    paper_peak_mass = float(paper_mass[np.argmax(paper_z)])
    print(f"\nPaper's own curve: max Z={paper_z.max():.3f} at mass={paper_peak_mass:.2f} GeV")
    for name, z in variants.items():
        max_z = float(z.max())
        max_mass = float(MASS_POINTS[np.argmax(z)])
        rms = float(np.sqrt(np.mean((z - paper_z_aligned) ** 2)))
        max_z_pass = abs(max_z - PAPER_MAX_Z) <= PASS_MAX_Z_TOL
        mass_pass = abs(max_mass - paper_peak_mass) <= PASS_MASS_TOL_GEV
        rms_pass = rms <= PASS_RMS_MAX
        overall_pass = max_z_pass and mass_pass and rms_pass
        print(f"{name}: max Z={max_z:.3f} at {max_mass:.1f} GeV, RMS vs paper={rms:.3f} "
              f"-- max_z_pass={max_z_pass}, mass_pass={mass_pass}, rms_pass={rms_pass} "
              f"=> {'PASS' if overall_pass else 'FAIL'}")
        results[name] = {
            "max_z": max_z, "max_z_mass": max_mass, "rms_vs_paper": rms,
            "max_z_pass": max_z_pass, "mass_pass": mass_pass, "rms_pass": rms_pass,
            "overall_pass": overall_pass, "curve": z.tolist(),
        }

    results["paper"] = {"max_z": float(paper_z.max()), "max_z_mass": paper_peak_mass,
                          "mass_points": paper_mass.tolist(), "curve": paper_z.tolist()}
    results["mass_points_ours"] = MASS_POINTS.tolist()
    results["criteria"] = {"max_z_tol": PASS_MAX_Z_TOL, "mass_tol_GeV": PASS_MASS_TOL_GEV,
                            "rms_max": PASS_RMS_MAX}

    # RMS restricted to the 28 bins actually VISIBLE in the rendered figure
    # (100-156 GeV), as a secondary cross-check.
    visible_mask = MASS_POINTS <= 156.0
    for name, z in variants.items():
        rms_vis = float(np.sqrt(np.mean((z[visible_mask] - paper_z_aligned[visible_mask]) ** 2)))
        results[name]["rms_vs_paper_visible_28bins_only"] = rms_vis
        print(f"  ({name} RMS restricted to the 28 visible bins: {rms_vis:.3f})")

    with open(RESULTS_DIR / "zlr_variants_results.json", "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\nWrote {RESULTS_DIR / 'zlr_variants_results.json'}")

    # --- Plot: all 4 variants overlaid on the paper's own curve ---
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(paper_mass, paper_z, "k-", lw=2.2, label="BumpNet paper's own $Z_{LR}$ (digitized)")
    colors = {"V1": "tab:blue", "V2": "tab:orange", "V3": "tab:green", "V4": "tab:red"}
    styles = {"V1": "--", "V2": ":", "V3": "-.", "V4": (0, (3, 1, 1, 1))}
    for name, z in variants.items():
        ax.plot(MASS_POINTS, z, ls=styles[name], color=colors[name], lw=1.6,
                 label=f"{name} (max={results[name]['max_z']:.2f} @ {results[name]['max_z_mass']:.0f} GeV, "
                       f"RMS={results[name]['rms_vs_paper']:.2f})")
    ax.axvline(156, color="gray", lw=0.8, ls=":")
    ax.text(156.3, ax.get_ylim()[0] + 0.3, "edge of\nvisible plot\nin Fig. 15", fontsize=7, color="gray")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("$m_{\\gamma\\gamma}$ [GeV]")
    ax.set_ylabel("signed $Z$")
    ax.set_title("A3: four candidate $Z_{LR}$ definitions vs. BumpNet's own curve")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "A3_variants_comparison.png", dpi=140)
    plt.close(fig)
    print(f"Wrote {RESULTS_DIR / 'A3_variants_comparison.png'}")


if __name__ == "__main__":
    main()
