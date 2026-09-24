"""
Statistical-model task, Part 5.2 companion #3: the headline ("money")
plot for the unblinded H->gamma-gamma result, in the calmer ATLAS
H->gamma-gamma style (cf. `studies/atlas_hgg_repro`'s own reproduction
of arXiv:1207.7214 Fig. 4(a), and the arXiv:2501.05603 Fig. 15 target
style this task asked to match).

Uses ONLY: (a) the real, already-unblinded, already-selected data
(read the same way as every other plot in this package -- no new
selection, no new cuts), (b) the deterministically re-derived S+B fit
parameters and Hesse covariance saved by `rederive_and_verify.py`
(itself verified, before being saved, to reproduce the gated primary
result's Z/mu_hat exactly and the already-committed spectrum plots
pixel-for-pixel), and (c) the already-computed local-p mass scan
(`stats/results/unblinded_postprocess.json`'s own `mh_scan.scan`, 81
points, mH=110-150 GeV in 0.5 GeV steps -- this is a REAL, ALREADY
STORED table of {mH, Z, mu_hat, ...}, not something derived here).
No fit is run here, no scan is redone. No number here can differ from
`UNBLINDED_RESULT.md` / the gated JSON.

Background-only component convention: the dashed curve is the
background COMPONENT of the same signal+background (alt) fit, not a
separately-fit null model -- the standard CMS/ATLAS money-plot
convention.

The +-1 sigma background band is EXACT linear error propagation
through the Bernstein background function (linear in its own
coefficients: B(edges) = design_matrix @ coeffs), using the alt fit's
own Hesse covariance restricted to the 14 background coefficients --
sigma_bin = sqrt(J Cov J^T) at each display bin, J being the
(already-linear) design matrix's own rows summed into display-width
groups and scaled by the same S/B weights as the data/curves. No new
fit, no resampling.

Three display variants are produced from the SAME underlying fine
(0.25 GeV) curves/data (the FIT range is always 105-180 GeV, never
changed by anything below -- only how it's grouped into bins and how
much of it is shown differs):
  - headline:    2 GeV bins, 105-160 GeV display window, 3 panels
  - 1gev alt:    1 GeV bins, 105-160 GeV display window, 3 panels
  - full-range:  2 GeV bins, 105-180 GeV display window, 3 panels
`verify_rebinning_consistency()` checks, and prints/reports, that the
2 GeV bins are EXACTLY the pairwise sum of the 1 GeV bins over the
same fine data (rebinned, not refitted) before any plot is drawn.

Per this task's explicit instruction, the grey blinded-region band is
NOT drawn on any of these (the calmer ATLAS style has no such band);
the fact that 115-135 GeV was blinded throughout the analysis and
opened only after pre-registration is stated in the caption text
instead.
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
POSTPROCESS_JSON = STATS_RESULTS / "unblinded_postprocess.json"
OUT_DIR = STATS_RESULTS / "plots" / "final"

FIT_LO, FIT_HI = 105.0, 180.0  # the actual fit range -- NEVER changed by any display variant below
GROUP_1GEV = 4   # 0.25 GeV fit bins -> 1 GeV display bins
GROUP_2GEV = 8   # 0.25 GeV fit bins -> 2 GeV display bins

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


def rebin_sum(edges, values, group):
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


def load_significance_scan():
    """The already-computed, already-stored local-p mass scan (real fit
    results, not recomputed here) -- `mh_scan.scan` in
    `unblinded_postprocess.json`, 81 points, mH=110-150 GeV, 0.5 GeV
    steps. Returns None if the file/field isn't there (caller must then
    fall back to the two-panel version -- this task's own instruction)."""
    if not POSTPROCESS_JSON.exists():
        return None
    pp = json.loads(POSTPROCESS_JSON.read_text(encoding="utf-8"))
    scan = pp.get("mh_scan", {}).get("scan")
    if not scan:
        return None
    mH = np.array([r["mH"] for r in scan])
    Z = np.array([r["Z"] for r in scan])
    return mH, Z


def compute_fine_curves():
    """The weighted fine (0.25 GeV) data/background/S+B arrays, computed
    ONCE from the real data and the already-verified re-derived fit
    parameters -- every display variant rebins these same arrays, never
    recomputes them."""
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

    total_data_fine = None
    total_bkg_fine = None
    total_sb_fine = None
    per_cat_data_fine = {}
    for cat in M.CATEGORIES:
        w = weights[cat]
        dd = data_counts[cat].astype(float)
        bk = bkg_curve(cat, alt_params, edges_fine)
        sb = sb_curve(cat, alt_params, edges_fine)
        total_data_fine = dd * w if total_data_fine is None else total_data_fine + dd * w
        total_bkg_fine = bk * w if total_bkg_fine is None else total_bkg_fine + bk * w
        total_sb_fine = sb * w if total_sb_fine is None else total_sb_fine + sb * w
        per_cat_data_fine[cat] = dd

    print(f"S/B weights: {weights}")

    return dict(edges_fine=edges_fine, total_data_fine=total_data_fine,
                total_bkg_fine=total_bkg_fine, total_sb_fine=total_sb_fine,
                per_cat_data_fine=per_cat_data_fine, weights=weights,
                cov_names=cov_names, cov=cov, mi=mi)


def _J_and_covbb(fine, group):
    """The linear map J (n_coarse x 14) from background coefficients to
    weighted display-bin background values, and the 14x14 background-
    coefficient covariance block -- the two pieces needed for exact
    linear error propagation at any binning `group`."""
    edges_fine = fine["edges_fine"]
    weights = fine["weights"]
    mi = fine["mi"]
    cov_names = fine["cov_names"]
    cov = fine["cov"]

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
        design_fine = fam.design_matrix(edges_fine, ci.bkg_order)
        n_coarse = design_fine.shape[0] // group
        design_coarse = design_fine[: n_coarse * group].reshape(n_coarse, group, -1).sum(axis=1)
        J_blocks.append(weights[cat] * design_coarse)
        all_idx.extend(bkg_param_idx[cat])
    J = np.concatenate(J_blocks, axis=1)
    cov_bb = cov[np.ix_(all_idx, all_idx)]
    return J, cov_bb


def build_data(fine, group):
    """Rebin the (already computed, unchanged) fine curves/data into
    `group`-sized display bins -- pure re-grouping arithmetic, no fit."""
    edges_fine = fine["edges_fine"]
    weights = fine["weights"]

    coarse_edges, data_coarse = rebin_sum(edges_fine, fine["total_data_fine"], group)
    _, bkg_coarse = rebin_sum(edges_fine, fine["total_bkg_fine"], group)
    _, sb_coarse = rebin_sum(edges_fine, fine["total_sb_fine"], group)
    centers = 0.5 * (coarse_edges[:-1] + coarse_edges[1:])

    per_cat_data_coarse = {}
    for cat in M.CATEGORIES:
        _, per_cat_data_coarse[cat] = rebin_sum(edges_fine, fine["per_cat_data_fine"][cat], group)
    # Properly propagated Poisson error on the weighted sum:
    # Var(sum_c w_c n_c) = sum_c w_c^2 * n_c (n_c independent Poisson, raw counts as variance estimator).
    data_err = np.sqrt(sum(weights[cat] ** 2 * per_cat_data_coarse[cat] for cat in M.CATEGORIES))

    # --- +-1 sigma background band via exact linear error propagation ---
    J, cov_bb = _J_and_covbb(fine, group)
    band_var = np.einsum("ij,jk,ik->i", J, cov_bb, J)
    band_sigma = np.sqrt(np.maximum(band_var, 0.0))

    return dict(centers=centers, data_coarse=data_coarse, data_err=data_err,
                bkg_coarse=bkg_coarse, sb_coarse=sb_coarse, band_sigma=band_sigma,
                weights=weights, coarse_edges=coarse_edges)


def verify_rebinning_consistency(fine):
    """Rebinned-not-refitted check: the 2 GeV bins must equal the exact
    pairwise sum of the 1 GeV bins, since both come from summing the
    SAME fine (0.25 GeV) arrays -- no new fit, pure re-grouping
    arithmetic. Prints and returns the result."""
    d1 = build_data(fine, GROUP_1GEV)
    d2 = build_data(fine, GROUP_2GEV)

    def pairwise_sum(arr):
        n = len(arr) // 2
        return arr[: n * 2].reshape(n, 2).sum(axis=1)

    checks = {}
    for key in ("data_coarse", "bkg_coarse", "sb_coarse"):
        lhs = pairwise_sum(d1[key])
        rhs = d2[key][: len(lhs)]
        checks[key] = float(np.max(np.abs(lhs - rhs)))

    # Background-band variance does NOT simply add pairwise: adjacent 1 GeV
    # bins share the same 7 Bernstein coefficients per category, so they are
    # correlated (Cov(bin_a, bin_b) != 0). The correct identity is
    # Var(bin_a + bin_b) = Var(bin_a) + Var(bin_b) + 2*Cov(bin_a, bin_b),
    # i.e. the FULL 1 GeV covariance matrix (not just its diagonal, which is
    # all `band_sigma` stores) must be pairwise-summed and compared against
    # the 2 GeV variance computed directly from J/Cov at group=2GeV.
    J1, cov_bb = _J_and_covbb(fine, GROUP_1GEV)
    J2, _ = _J_and_covbb(fine, GROUP_2GEV)
    cov_coarse_1gev = J1 @ cov_bb @ J1.T  # full (n_1gev x n_1gev) covariance
    n2 = J2.shape[0]
    var2_from_1gev_full_cov = np.array([
        cov_coarse_1gev[2 * i, 2 * i] + cov_coarse_1gev[2 * i + 1, 2 * i + 1]
        + 2 * cov_coarse_1gev[2 * i, 2 * i + 1]
        for i in range(n2)
    ])
    var2_direct = np.einsum("ij,jk,ik->i", J2, cov_bb, J2)
    checks["band_variance_full_covariance_identity_max_abs_diff"] = float(
        np.max(np.abs(var2_from_1gev_full_cov - var2_direct)))
    # Also report the naive (diagonal-only, wrong) comparison for transparency --
    # this is expected to be large precisely BECAUSE adjacent bins are correlated,
    # not because anything is inconsistent.
    var1_diag_pairs = pairwise_sum(d1["band_sigma"] ** 2)
    checks["band_variance_diagonal_only_naive_max_abs_diff (expected large: bins are correlated)"] = float(
        np.max(np.abs(var1_diag_pairs - var2_direct)))

    print("\n=== Rebinning consistency check (2 GeV bins vs. paired 1 GeV bins) ===")
    for k, v in checks.items():
        print(f"  {k}: max abs diff = {v:.3e}")
    return checks


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


def draw_figure(d, sig_scan, x_range, bin_width_label, slide=False):
    """Calmer ATLAS-style figure: spectrum (top), background-subtracted
    residual (middle), and -- if `sig_scan` is available -- observed
    local significance vs m_H (bottom). No blinded-region band (removed
    per this task's explicit instruction; the blinding fact is stated
    in the caption text instead).

    `slide=True` (talk-slide cosmetic variant, display only): omits the
    "Independent reanalysis..." disclaimer text and shortens the info
    box (drops "(expected ...)" and the m_H line). Everything else --
    data, curves, band, significance panel, legend, axes -- is produced
    by the exact same code path as `slide=False`."""
    centers = d["centers"]

    three_panel = sig_scan is not None
    if three_panel:
        fig, (ax1, ax2, ax3) = plt.subplots(
            3, 1, figsize=(7.2, 10.4), sharex=True,
            gridspec_kw={"height_ratios": [3, 1, 1], "hspace": 0.08})
    else:
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(7.2, 8.4), sharex=True,
            gridspec_kw={"height_ratios": [3, 1.1], "hspace": 0.06})
        ax3 = None

    # --- top panel: spectrum ---
    ax1.fill_between(centers, d["bkg_coarse"] - d["band_sigma"], d["bkg_coarse"] + d["band_sigma"],
                      color="#3f7fa8", alpha=0.25, lw=0, zorder=1, label=r"Background $\pm1\sigma$ (fit covariance)")
    ax1.plot(centers, d["bkg_coarse"], color="#1f5fa8", ls="--", lw=1.8, zorder=2, label="Background component of S+B fit")
    ax1.plot(centers, d["sb_coarse"], color="#c1272d", ls="-", lw=1.9, zorder=3, label="Signal + background fit")
    ax1.errorbar(centers, d["data_coarse"], yerr=d["data_err"], fmt="ko", ms=4, lw=1.2,
                 capsize=0, zorder=4, label="Data (S/B-weighted)")
    ax1.set_ylabel(f"S/B-weighted events / {bin_width_label}")
    ax1.set_xlim(*x_range)
    mask = (centers >= x_range[0]) & (centers <= x_range[1])
    ax1.set_ylim(bottom=0, top=d["data_coarse"][mask].max() * 1.30)
    ax1.legend(loc="upper right", frameon=False)
    ax1.tick_params(direction="in", top=True, right=True, which="both")

    ax1.text(0.0, 1.02, "CMS Open Data", transform=ax1.transAxes, fontsize=15,
              fontweight="bold", va="bottom", ha="left", clip_on=False)
    ax1.text(1.0, 1.02, f"{LUMI_FB:.1f} fb" r"$^{-1}$" " (13 TeV), 2016 (Runs G+H)",
              transform=ax1.transAxes, fontsize=11.5, va="bottom", ha="right", clip_on=False)
    if not slide:
        ax1.text(0.02, 0.045, "Independent reanalysis of public data.\nNot a CMS publication; not reviewed or endorsed by CMS.",
                  transform=ax1.transAxes, fontsize=9.5, va="bottom", ha="left", style="italic", color="#444444")

    if slide:
        box_text = (
            r"$H\rightarrow\gamma\gamma$" "\n"
            f"{N_CANDIDATES:,} diphoton candidates" "\n"
            f"Local significance: {LOCAL_Z:.2f}" r"$\sigma$" "\n"
            r"$\mu$ = " f"{MU_HAT:.2f}" r"$^{+%.2f}_{-%.2f}$" % (MU_UP, MU_DOWN)
        )
    else:
        box_text = (
            r"$H\rightarrow\gamma\gamma$" "\n"
            f"{N_CANDIDATES:,} diphoton candidates" "\n"
            f"Local significance: {LOCAL_Z:.2f}" r"$\sigma$" f" (expected {LOCAL_Z_EXP:.2f}" r"$\sigma$" ")\n"
            r"$\mu$ = " f"{MU_HAT:.2f}" r"$^{+%.2f}_{-%.2f}$" % (MU_UP, MU_DOWN) + "\n"
            r"$m_H$ fixed to 125.09 GeV (primary fit)"
        )
    ax1.text(0.985, 0.60, box_text, transform=ax1.transAxes, fontsize=11, va="top", ha="right",
              bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#888888", lw=1.0, alpha=0.95))

    # --- middle panel: background-subtracted residual ---
    resid = d["data_coarse"] - d["bkg_coarse"]
    fitted_signal = d["sb_coarse"] - d["bkg_coarse"]
    ax2.fill_between(centers, -d["band_sigma"], d["band_sigma"], color="#3f7fa8", alpha=0.25, lw=0, zorder=1)
    ax2.axhline(0, color="#1f5fa8", ls="--", lw=1.5, zorder=2)
    ax2.plot(centers, fitted_signal, color="#c1272d", ls="-", lw=1.9, zorder=3, label="Fitted signal (S+B minus its own background)")
    ax2.errorbar(centers, resid, yerr=d["data_err"], fmt="ko", ms=4, lw=1.2, capsize=0, zorder=4)
    ax2.set_ylabel("Data $-$ bkg")
    ax2.legend(loc="lower right", frameon=False, fontsize=10.5)
    ax2.tick_params(direction="in", top=True, right=True, which="both")
    if not three_panel:
        ax2.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")

    # --- bottom panel: observed local significance vs m_H (already-stored scan) ---
    if three_panel:
        mH_scan, Z_scan = sig_scan
        ax3.plot(mH_scan, Z_scan, color="#1f5fa8", ls="-", marker="o", ms=3, lw=1.6, zorder=2)
        ax3.axhline(0, color="black", lw=1.0, zorder=1)
        ax3.set_ylabel("Local $Z$")
        ax3.set_xlabel(r"$m_{\gamma\gamma}$ [GeV]")
        ax3.set_ylim(bottom=min(-0.3, float(np.min(Z_scan)) - 0.3))
        ax3.tick_params(direction="in", top=True, right=True, which="both")

    return fig, (ax1, ax2, ax3) if three_panel else (ax1, ax2)


def build_caption(weights, has_sig_panel):
    third = (
        " A third panel shows the observed local significance Z vs m_H "
        "from the already-computed 110-150 GeV mass scan "
        "(stats/results/unblinded_postprocess.json's mh_scan.scan, 81 points, "
        "0.5 GeV steps -- not recomputed here); it is blank outside that "
        "pre-declared scan range even where the display window is wider."
    ) if has_sig_panel else ""
    return (
        f"{N_CANDIDATES:,} selected diphoton candidates. S/B-weighted combination of the EBEB and "
        f"notEBEB categories, weight w_c = S_c/B_c at the signal peak (m_H=125.09 GeV) from the same "
        f"signal+background fit: EBEB w={weights['EBEB']:.3f}, notEBEB w={weights['notEBEB']:.3f} "
        f"(identical weighting to spectrum_combined_SB_weighted.png). The fit itself always uses the "
        f"full 105-180 GeV range and 0.25 GeV bins, regardless of display choice below; only the "
        f"binning and x-axis window shown here differ. Headline: 2 GeV display bins, 105-160 GeV "
        f"window (hgg_money_plot.png/.pdf). Alternatives: 1 GeV display bins, same 105-160 GeV window "
        f"(hgg_money_plot_1gev.png/.pdf); 2 GeV display bins, full 105-180 GeV window "
        f"(hgg_money_plot_full_range.png/.pdf) -- all three rebin the identical underlying fit curves "
        f"and data, none re-fits. Slide variant (hgg_money_plot_slide.png/.pdf): identical data, curves, "
        f"band, and significance panel as the headline (2 GeV bins, 105-160 GeV) -- omits only the "
        f"'Independent reanalysis...' disclaimer text and, in the info box, the '(expected ...)' "
        f"significance qualifier and the m_H line; for talk slides, not a replacement for the headline. "
        f"Data error bars: propagated Poisson uncertainty on the weighted sum, "
        f"sigma = sqrt(sum_c w_c^2 * n_c). Background band: +-1sigma linear error propagation through "
        f"the fitted Bernstein background coefficients using the S+B fit's own Hesse covariance matrix."
        f"{third} "
        f"The 115-135 GeV signal region was blinded throughout the analysis (model, fit procedure, and "
        f"reporting thresholds all frozen beforehand) and opened only after pre-registration -- see "
        f"UNBLINDING_PLAN.md / FINAL_REPORT.md Section 8; no shaded band marks it on these plots (a "
        f"deliberate calmer-style choice), but the blinding itself is unchanged and total."
    )


def main_plot(cli_style="report"):
    """`cli_style="report"` (default): unchanged behavior -- produces the
    three report variants (headline, 1gev, full_range) plus the
    per-category chart and caption, exactly as before this option was
    added. `cli_style="slide"`: produces ONLY the new talk-slide
    cosmetic variant (hgg_money_plot_slide.png/.pdf, same 2 GeV/105-160
    data/curves/band/significance panel as the headline) and refreshes
    the caption text -- does NOT write or touch hgg_money_plot.png/.pdf
    or any of the other existing variant files."""
    style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fine = compute_fine_curves()

    sig_scan = load_significance_scan()
    if sig_scan is None:
        print("\nWARNING: local-p mass scan not found/empty in "
              f"{POSTPROCESS_JSON} -- producing two-panel versions only.")
    else:
        mH_scan, Z_scan = sig_scan
        print(f"\nLoaded stored significance scan: {len(mH_scan)} points, "
              f"mH in [{mH_scan.min():.1f}, {mH_scan.max():.1f}] GeV")

    if cli_style == "slide":
        d = build_data(fine, GROUP_2GEV)
        fig, axes = draw_figure(d, sig_scan, (105, 160), "2 GeV", slide=True)
        fig.savefig(OUT_DIR / "hgg_money_plot_slide.png", dpi=300, bbox_inches="tight")
        fig.savefig(OUT_DIR / "hgg_money_plot_slide.pdf", bbox_inches="tight")
        plt.close(fig)
        print("wrote hgg_money_plot_slide.png / .pdf (2 GeV bins, 105-160 GeV display, "
              f"{'3' if sig_scan is not None else '2'} panels, slide style -- "
              "hgg_money_plot.png/.pdf and the other variants were NOT touched)")

        caption = build_caption(d["weights"], sig_scan is not None)
        (OUT_DIR / "hgg_money_plot_caption.txt").write_text(caption, encoding="utf-8")
        print("\nCaption:\n" + caption)
        return None

    checks = verify_rebinning_consistency(fine)

    variants = [
        ("hgg_money_plot", GROUP_2GEV, (105, 160), "2 GeV"),
        ("hgg_money_plot_1gev", GROUP_1GEV, (105, 160), "1 GeV"),
        ("hgg_money_plot_full_range", GROUP_2GEV, (105, 180), "2 GeV"),
    ]
    for name, group, x_range, width_label in variants:
        d = build_data(fine, group)
        fig, axes = draw_figure(d, sig_scan, x_range, width_label)
        fig.savefig(OUT_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
        fig.savefig(OUT_DIR / f"{name}.pdf", bbox_inches="tight")
        plt.close(fig)
        print(f"wrote {name}.png / .pdf ({width_label} bins, {x_range[0]}-{x_range[1]} GeV display, "
              f"{'3' if sig_scan is not None else '2'} panels)")

    # --- per-category significance: unchanged from before, a SEPARATE small figure ---
    d_for_weights = build_data(fine, GROUP_2GEV)
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
    print("wrote hgg_per_category_significance.png / .pdf (unchanged)")

    caption = build_caption(d_for_weights["weights"], sig_scan is not None)
    (OUT_DIR / "hgg_money_plot_caption.txt").write_text(caption, encoding="utf-8")
    print("\nCaption:\n" + caption)

    return checks


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=["report", "slide"], default="report",
                         help="'report' (default): unchanged -- headline + 1gev + full_range + "
                              "per-category chart. 'slide': ONLY the talk-slide cosmetic variant "
                              "(hgg_money_plot_slide.png/.pdf); does not touch the other files.")
    args = parser.parse_args()
    main_plot(cli_style=args.style)
