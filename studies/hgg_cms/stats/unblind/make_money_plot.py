"""
Statistical-model task, Part 5.2 companion #3: the headline ("money")
plot for the unblinded H->gamma-gamma result.

Uses ONLY: (a) the real, already-unblinded, already-selected data
(read the same way as every other plot in this package -- no new
selection, no new cuts), and (b) the deterministically re-derived S+B
fit parameters and Hesse covariance saved by `rederive_and_verify.py`
(itself verified, before being saved, to reproduce the gated primary
result's Z/mu_hat exactly and the already-committed spectrum plots
pixel-for-pixel -- see that script's own docstring and printed log).
No fit is run here. No number here can differ from
`UNBLINDED_RESULT.md` / the gated JSON.

Background-only component convention (per this task's explicit
instruction): the dashed curve is the background COMPONENT of the
same signal+background (alt) fit, not a separately-fit null model --
the standard CMS/ATLAS money-plot convention. This differs slightly
from the exploratory `spectrum_combined_SB_weighted.png` (which dashes
the independently-fit null/mu=0 model) -- both are legitimate; this
one matches what real H->gamma-gamma papers show.

The +-1 sigma background band is EXACT linear error propagation
through the Bernstein background function (linear in its own
coefficients: B(edges) = design_matrix @ coeffs), using the alt fit's
own Hesse covariance restricted to the 14 background coefficients
(7 per category) -- sigma_bin = sqrt(J Cov J^T) at each 1 GeV bin,
J being the (already-linear) design matrix's own rows summed into
1 GeV groups and scaled by the same S/B weights as the data/curves.
No new fit, no resampling -- closed-form propagation of the already-
verified covariance matrix.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from studies.hgg_cms.output import read_output  # noqa: E402
from studies.hgg_cms.stats import model as M  # noqa: E402
from studies.hgg_cms.background_model.families import FAMILIES  # noqa: E402

MH_NOMINAL = 125.09
DATA_FILE = r"C:\Users\matan\hgg_full_merged\data_full_range.root"
STATS_RESULTS = Path(__file__).resolve().parents[1] / "results"
REDERIVED_JSON = STATS_RESULTS / "unblinded" / "rederived_fit_params_for_plotting.json"
OUT_DIR = STATS_RESULTS / "plots" / "final"
GROUP = 4  # 0.25 GeV fit bins -> 1 GeV display bins

LOCAL_Z, LOCAL_Z_EXP = 4.13, 3.91
MU_HAT, MU_UP, MU_DOWN = 1.06, 0.37, 0.30
Z_EBEB, Z_NOTEBEB = 4.097, 0.869
LUMI_FB = 16.4
N_CANDIDATES = 261_543  # UNBLINDED_RESULT.md Sec. 0 / Sec. 8 -- total selected diphoton pairs


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


def rebin_sum(edges, values, group=GROUP):
    n = len(values) // group
    coarse_edges = edges[::group][: n + 1]
    coarse = values[: n * group].reshape(n, group).sum(axis=1)
    return coarse_edges, coarse


def bkg_curve(cat, params, edges_fine):
    mi = M.get_model_inputs()
    ci = mi.categories[cat]
    fam = FAMILIES[ci.bkg_family]
    bkg_names = fam.param_names(ci.bkg_order)
    bkg_params = np.array([params[f"bkg_{cat}_{n}"] for n in bkg_names])
    return fam.bin_expectation(edges_fine, ci.bkg_order, bkg_params)


def sb_curve(cat, params, edges_fine):
    return M.expected_counts(cat, params, MH_NOMINAL, edges_fine)


def main():
    print("Loading real (unblinded) data...")
    data_counts = load_real_data_counts()

    print("Loading re-derived, already-verified fit parameters/covariance...")
    rd = json.loads(REDERIVED_JSON.read_text(encoding="utf-8"))
    alt_params = rd["alt_fit_params_mu_free"]
    weights = rd["sb_weighted_combination_weights"]
    cov_names = rd["alt_fit_covariance"]["param_order"]
    cov = np.array(rd["alt_fit_covariance"]["matrix"])

    edges_fine = M.edges()
    mi = M.get_model_inputs()

    # --- weighted data, background, S+B curves at 1 GeV bins ---
    total_data_fine = None
    total_bkg_fine = None
    total_sb_fine = None
    per_cat_data_coarse = {}
    for cat in M.CATEGORIES:
        w = weights[cat]
        d = data_counts[cat].astype(float)
        bk = bkg_curve(cat, alt_params, edges_fine)
        sb = sb_curve(cat, alt_params, edges_fine)
        total_data_fine = d * w if total_data_fine is None else total_data_fine + d * w
        total_bkg_fine = bk * w if total_bkg_fine is None else total_bkg_fine + bk * w
        total_sb_fine = sb * w if total_sb_fine is None else total_sb_fine + sb * w
        _, per_cat_data_coarse[cat] = rebin_sum(edges_fine, d)

    coarse_edges, data_coarse = rebin_sum(edges_fine, total_data_fine)
    _, bkg_coarse = rebin_sum(edges_fine, total_bkg_fine)
    _, sb_coarse = rebin_sum(edges_fine, total_sb_fine)
    centers = 0.5 * (coarse_edges[:-1] + coarse_edges[1:])

    # Properly propagated Poisson error on the weighted sum:
    # Var(sum_c w_c n_c) = sum_c w_c^2 * n_c  (n_c independent Poisson, raw counts as variance estimator).
    data_err = np.sqrt(sum(weights[cat] ** 2 * per_cat_data_coarse[cat] for cat in M.CATEGORIES))

    # --- +-1 sigma background band via exact linear error propagation ---
    bkg_param_idx = {}
    for cat in M.CATEGORIES:
        ci = mi.categories[cat]
        fam = FAMILIES[ci.bkg_family]
        names_c = fam.param_names(ci.bkg_order)
        bkg_param_idx[cat] = [cov_names.index(f"bkg_{cat}_{n}") for n in names_c]

    J_blocks = []
    all_idx = []
    for cat in M.CATEGORIES:
        ci = mi.categories[cat]
        fam = FAMILIES[ci.bkg_family]
        design_fine = fam.design_matrix(edges_fine, ci.bkg_order)  # (n_fine, 7)
        n_coarse = design_fine.shape[0] // GROUP
        design_coarse = design_fine[: n_coarse * GROUP].reshape(n_coarse, GROUP, -1).sum(axis=1)
        J_blocks.append(weights[cat] * design_coarse)
        all_idx.extend(bkg_param_idx[cat])
    J = np.concatenate(J_blocks, axis=1)  # (n_coarse, 14)
    cov_bb = cov[np.ix_(all_idx, all_idx)]
    band_var = np.einsum("ij,jk,ik->i", J, cov_bb, J)
    band_sigma = np.sqrt(np.maximum(band_var, 0.0))

    print(f"S/B weights: {weights}")
    print(f"Background band: median 1-sigma = {np.median(band_sigma):.2f} events "
          f"(median background level = {np.median(bkg_coarse):.1f})")

    return dict(centers=centers, data_coarse=data_coarse, data_err=data_err,
                bkg_coarse=bkg_coarse, sb_coarse=sb_coarse, band_sigma=band_sigma,
                weights=weights, coarse_edges=coarse_edges)


def style():
    plt.rcParams.update({
        "font.size": 13,
        "axes.labelsize": 15,
        "axes.titlesize": 13,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 11.5,
        "figure.dpi": 100,
    })


def draw_base_figure(d, figsize=(7.2, 8.4)):
    centers = d["centers"]
    edges_c = d["coarse_edges"]
    width = edges_c[1] - edges_c[0]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=figsize, sharex=True,
        gridspec_kw={"height_ratios": [3, 1.1], "hspace": 0.06})

    # --- upper panel ---
    ax1.fill_between(centers, d["bkg_coarse"] - d["band_sigma"], d["bkg_coarse"] + d["band_sigma"],
                      color="#3f7fa8", alpha=0.25, lw=0, zorder=1, label=r"Background $\pm1\sigma$ (fit covariance)")
    ax1.plot(centers, d["bkg_coarse"], color="#1f5fa8", ls="--", lw=1.8, zorder=2, label="Background component of S+B fit")
    ax1.plot(centers, d["sb_coarse"], color="#c1272d", ls="-", lw=1.9, zorder=3, label="Signal + background fit")
    ax1.errorbar(centers, d["data_coarse"], yerr=d["data_err"], fmt="ko", ms=4, lw=1.2,
                 capsize=0, zorder=4, label="Data (S/B-weighted)")
    ax1.axvspan(115, 135, color="gray", alpha=0.07, lw=0, zorder=0,
                label="Blinded 115–135 GeV (opened only after pre-registration)")
    ax1.set_ylabel(f"S/B-weighted events / {width:.0f} GeV")
    ax1.set_xlim(105, 180)
    ax1.set_ylim(bottom=0, top=d["data_coarse"].max() * 1.30)
    ax1.legend(loc="upper right", frameon=False)
    ax1.tick_params(direction="in", top=True, right=True, which="both")

    ax1.text(0.0, 1.02, "CMS Open Data", transform=ax1.transAxes, fontsize=15,
              fontweight="bold", va="bottom", ha="left", clip_on=False)
    ax1.text(1.0, 1.02, f"{LUMI_FB:.1f} fb" r"$^{-1}$" " (13 TeV), 2016 (Runs G+H)",
              transform=ax1.transAxes, fontsize=11.5, va="bottom", ha="right", clip_on=False)
    ax1.text(0.02, 0.045, "Independent reanalysis of public data.\nNot a CMS publication; not reviewed or endorsed by CMS.",
              transform=ax1.transAxes, fontsize=9.5, va="bottom", ha="left", style="italic", color="#444444")

    box_text = (
        r"$H\rightarrow\gamma\gamma$" "\n"
        f"{N_CANDIDATES:,} diphoton candidates" "\n"
        f"Local significance: {LOCAL_Z:.2f}" r"$\sigma$" f" (expected {LOCAL_Z_EXP:.2f}" r"$\sigma$" ")\n"
        r"$\mu$ = " f"{MU_HAT:.2f}" r"$^{+%.2f}_{-%.2f}$" % (MU_UP, MU_DOWN) + "\n"
        r"$m_H$ fixed to 125.09 GeV (primary fit)"
    )
    ax1.text(0.985, 0.60, box_text, transform=ax1.transAxes, fontsize=11, va="top", ha="right",
              bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#888888", lw=1.0, alpha=0.95))

    # --- lower panel: background-subtracted ---
    resid = d["data_coarse"] - d["bkg_coarse"]
    sig_curve = d["sb_coarse"] - d["bkg_coarse"]
    ax2.fill_between(centers, -d["band_sigma"], d["band_sigma"], color="#3f7fa8", alpha=0.25, lw=0, zorder=1)
    ax2.axhline(0, color="#1f5fa8", ls="--", lw=1.5, zorder=2)
    ax2.plot(centers, sig_curve, color="#c1272d", ls="-", lw=1.9, zorder=3, label="Fitted signal (S+B minus its own background)")
    ax2.errorbar(centers, resid, yerr=d["data_err"], fmt="ko", ms=4, lw=1.2, capsize=0, zorder=4)
    ax2.axvspan(115, 135, color="gray", alpha=0.07, lw=0, zorder=0)
    ax2.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
    ax2.set_ylabel("Data $-$ bkg")
    ax2.legend(loc="upper right", frameon=False, fontsize=10.5)
    ax2.tick_params(direction="in", top=True, right=True, which="both")

    return fig, ax1, ax2


def build_caption(weights):
    return (
        f"{N_CANDIDATES:,} selected diphoton candidates. S/B-weighted combination of the EBEB and "
        f"notEBEB categories, weight w_c = S_c/B_c at the signal peak (m_H=125.09 GeV) from the same "
        f"signal+background fit: EBEB w={weights['EBEB']:.3f}, notEBEB w={weights['notEBEB']:.3f} "
        f"(identical weighting to spectrum_combined_SB_weighted.png). 1 GeV bins (a 2 GeV version is "
        f"kept as an alternative). Data error bars: propagated Poisson uncertainty on the weighted sum, "
        f"sigma = sqrt(sum_c w_c^2 * n_c). Background band: +-1sigma linear error propagation through "
        f"the fitted Bernstein background coefficients using the S+B fit's own Hesse covariance matrix. "
        f"The shaded grey vertical band at 115-135 GeV marks the signal region that was blinded "
        f"throughout the analysis (model, fit procedure, and reporting thresholds all frozen beforehand) "
        f"and opened only after pre-registration -- see UNBLINDING_PLAN.md / FINAL_REPORT.md Section 8."
    )


def main_plot():
    style()
    d = main()
    fig, ax1, ax2 = draw_base_figure(d)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "hgg_money_plot.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_DIR / "hgg_money_plot.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote hgg_money_plot.png / .pdf")

    # --- per-category significance: a SEPARATE small figure, not an inset --
    # (an inset placed anywhere inside the upper panel's axes covers either
    # the high-mass tail or the 105-115 GeV descending shoulder -- both are
    # real data, not empty space, at this bin width; tried and rejected.)
    figc, axc = plt.subplots(figsize=(3.4, 3.0))
    x_pos = np.array([0, 1])
    zs = [Z_EBEB, Z_NOTEBEB]
    bars = axc.bar(x_pos, zs, color=["#c1272d", "#9aa5ab"], width=0.6)
    axc.set_xticks(x_pos)
    axc.set_xticklabels(["EBEB", "notEBEB"])
    axc.set_ylim(0, 5)
    axc.axhline(LOCAL_Z, color="k", ls=":", lw=1, label=f"Combined ({LOCAL_Z:.2f})")
    axc.set_ylabel("Local Z")
    axc.set_title(r"$H\rightarrow\gamma\gamma$ per-category significance")
    for x, z in zip(x_pos, zs):
        axc.text(x, z + 0.12, f"{z:.2f}", ha="center", fontsize=11)
    axc.legend(loc="upper center", frameon=False, fontsize=9.5)
    axc.spines["top"].set_visible(False)
    axc.spines["right"].set_visible(False)
    figc.tight_layout()
    figc.savefig(OUT_DIR / "hgg_per_category_significance.png", dpi=300, bbox_inches="tight")
    figc.savefig(OUT_DIR / "hgg_per_category_significance.pdf", bbox_inches="tight")
    plt.close(figc)
    print("wrote hgg_per_category_significance.png / .pdf")

    caption = build_caption(d["weights"])
    (OUT_DIR / "hgg_money_plot_caption.txt").write_text(caption, encoding="utf-8")
    print("\nCaption:\n" + caption)


if __name__ == "__main__":
    main_plot()
