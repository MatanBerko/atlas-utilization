"""
Statistical-model task, Part 5.2 companion: plots for the unblinded
result. NOT gated -- the data was already opened through the proper
gate by run_unblinded_analysis.py; this only visualizes that same
already-unblinded result. Re-derives the primary fit's full parameter
vector (background coefficients, nuisance values) via the IDENTICAL
fit call `run_unblinded_analysis.py` itself used (same mu_fixed, same
n_starts, same seed, same warm start) -- that script only saved
q0/Z/mu_hat, not the full best-fit parameter dict, and this is not a
new or different fit, just re-deriving the same already-reported
minimum for visualization.
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
from studies.hgg_cms.stats import fit as F  # noqa: E402
from studies.hgg_cms.background_model.families import FAMILIES  # noqa: E402

MH_NOMINAL = 125.09
DATA_FILE = r"C:\Users\matan\hgg_full_merged\data_full_range.root"
POSTPROCESS_JSON = Path(__file__).resolve().parents[1] / "results" / "unblinded_postprocess.json"
EXPECTED_SIG_JSON = Path(__file__).resolve().parents[1] / "results" / "expected_significance.json"
PLOTS_DIR = Path(__file__).resolve().parents[1] / "results" / "plots" / "unblinded"


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


def refit_primary(data_counts):
    names = M.full_param_names()
    base = F.default_start(names, mu_start=0.0)
    null = F.fit_model(data_counts, MH_NOMINAL, names, mu_fixed=0.0, n_starts=10, seed=1, base_start=base)
    alt = F.fit_model(data_counts, MH_NOMINAL, names, mu_fixed=None, n_starts=10, seed=2, base_start=base)
    return null, alt


def rebin_for_display(edges, counts, group=8):
    """0.25 GeV fit bins -> 2 GeV display bins (group=8) for a readable
    spectrum plot; the fit itself always uses the fine bins."""
    n = len(counts) // group
    coarse_edges = edges[::group][: n + 1]
    coarse_counts = counts[: n * group].reshape(n, group).sum(axis=1)
    return coarse_edges, coarse_counts


def bkg_curve(cat, params, edges_fine):
    mi = M.get_model_inputs()
    ci = mi.categories[cat]
    fam = FAMILIES[ci.bkg_family]
    bkg_names = fam.param_names(ci.bkg_order)
    bkg_params = np.array([params[f"bkg_{cat}_{n}"] for n in bkg_names])
    return fam.bin_expectation(edges_fine, ci.bkg_order, bkg_params)


def sb_curve(cat, params, edges_fine):
    return M.expected_counts(cat, params, MH_NOMINAL, edges_fine)


def plot_category_spectrum(cat, data_counts, null_params, alt_params, edges_fine):
    group = 8  # 0.25 * 8 = 2 GeV display bins
    coarse_edges, data_coarse = rebin_for_display(edges_fine, data_counts[cat], group)
    centers = 0.5 * (coarse_edges[:-1] + coarse_edges[1:])
    width = coarse_edges[1] - coarse_edges[0]

    bkg_fine = bkg_curve(cat, null_params, edges_fine)
    sb_fine = sb_curve(cat, alt_params, edges_fine)
    _, bkg_coarse = rebin_for_display(edges_fine, bkg_fine, group)
    _, sb_coarse = rebin_for_display(edges_fine, sb_fine, group)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    ax1.errorbar(centers, data_coarse, yerr=np.sqrt(np.maximum(data_coarse, 1)), fmt="ko", ms=3, label="Data")
    ax1.plot(centers, bkg_coarse, "b--", lw=1.5, label="Background-only fit")
    ax1.plot(centers, sb_coarse, "r-", lw=1.5, label="Signal + background fit")
    ax1.axvspan(115, 135, color="gray", alpha=0.08, lw=0)
    ax1.set_ylabel(f"Events / {width:.1f} GeV")
    ax1.set_title(f"{cat}: m_gamma-gamma spectrum (full range, unblinded)")
    ax1.legend(fontsize=9)

    resid = data_coarse - bkg_coarse
    ax2.errorbar(centers, resid, yerr=np.sqrt(np.maximum(data_coarse, 1)), fmt="ko", ms=3)
    ax2.plot(centers, sb_coarse - bkg_coarse, "r-", lw=1.5)
    ax2.axhline(0, color="b", ls="--", lw=1)
    ax2.axvspan(115, 135, color="gray", alpha=0.08, lw=0)
    ax2.set_xlabel("m_gamma-gamma [GeV]")
    ax2.set_ylabel("Data - bkg")

    fig.tight_layout()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOTS_DIR / f"spectrum_{cat}.png", dpi=140)
    plt.close(fig)
    print(f"  wrote spectrum_{cat}.png")


def plot_combined_sb_weighted(data_counts, null_params, alt_params, edges_fine):
    """S/B-weighted combination: each category's bin content is
    weighted by w_c = S_c(mH_nominal)/B_c(mH_nominal), the ratio of
    that category's OWN best-fit signal-peak height to its background
    height at m_H=125.09 GeV (a single scalar per category, not
    per-bin) -- the standard way of combining categories of different
    purity into one illustrative spectrum without distorting the
    background shape. Data, background, and signal+background curves
    are all weighted the same way before summing, so the background
    curve still traces the weighted data's background level correctly."""
    weights = {}
    for cat in M.CATEGORIES:
        # S and B both taken from the SAME (alt) fit for a clean, self-
        # consistent S/B ratio at the peak bin (not mixing the null
        # fit's own independently-floated background level in).
        peak_bin = np.searchsorted(edges_fine, MH_NOMINAL) - 1
        sb_at_peak = float(sb_curve(cat, alt_params, edges_fine)[peak_bin])
        b_at_peak = float(bkg_curve(cat, alt_params, edges_fine)[peak_bin])
        s_peak = sb_at_peak - b_at_peak
        weights[cat] = s_peak / b_at_peak if b_at_peak > 0 else 0.0

    group = 8
    total_data = None
    total_bkg = None
    total_sb = None
    for cat in M.CATEGORIES:
        w = weights[cat]
        d = data_counts[cat].astype(float) * w
        bk = bkg_curve(cat, null_params, edges_fine) * w
        sb = sb_curve(cat, alt_params, edges_fine) * w
        total_data = d if total_data is None else total_data + d
        total_bkg = bk if total_bkg is None else total_bkg + bk
        total_sb = sb if total_sb is None else total_sb + sb

    coarse_edges, data_coarse = rebin_for_display(edges_fine, total_data, group)
    _, bkg_coarse = rebin_for_display(edges_fine, total_bkg, group)
    _, sb_coarse = rebin_for_display(edges_fine, total_sb, group)
    centers = 0.5 * (coarse_edges[:-1] + coarse_edges[1:])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    ax1.errorbar(centers, data_coarse, yerr=np.sqrt(np.maximum(data_coarse, 1e-6)), fmt="ko", ms=3, label="Data (S/B-weighted)")
    ax1.plot(centers, bkg_coarse, "b--", lw=1.5, label="Background-only fit")
    ax1.plot(centers, sb_coarse, "r-", lw=1.5, label="Signal + background fit")
    ax1.axvspan(115, 135, color="gray", alpha=0.08, lw=0)
    ax1.set_ylabel("S/B-weighted events / 2 GeV")
    ax1.set_title(f"Combined (S/B-weighted): EBEB w={weights['EBEB']:.3f}, notEBEB w={weights['notEBEB']:.3f}")
    ax1.legend(fontsize=9)

    resid = data_coarse - bkg_coarse
    ax2.errorbar(centers, resid, yerr=np.sqrt(np.maximum(data_coarse, 1e-6)), fmt="ko", ms=3)
    ax2.plot(centers, sb_coarse - bkg_coarse, "r-", lw=1.5)
    ax2.axhline(0, color="b", ls="--", lw=1)
    ax2.axvspan(115, 135, color="gray", alpha=0.08, lw=0)
    ax2.set_xlabel("m_gamma-gamma [GeV]")
    ax2.set_ylabel("Data - bkg")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "spectrum_combined_SB_weighted.png", dpi=140)
    plt.close(fig)
    print("  wrote spectrum_combined_SB_weighted.png")
    return weights


def plot_local_p_curve():
    pp = json.loads(POSTPROCESS_JSON.read_text(encoding="utf-8"))
    exp = json.loads(EXPECTED_SIG_JSON.read_text(encoding="utf-8")) if EXPECTED_SIG_JSON.exists() else None

    obs = pp["mh_scan"]["scan"]
    mH_obs = [r["mH"] for r in obs]
    Z_obs = [r["Z"] for r in obs]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(mH_obs, Z_obs, "-o", ms=3, color="k", label="Observed")
    if exp:
        exp_scan = exp["part_3_4_mass_scan"]["scan"]
        mH_exp = [r["mH"] for r in exp_scan]
        Z_exp = [r["Z"] for r in exp_scan]
        ax.plot(mH_exp, Z_exp, "--", color="#1f5fa8", label="Expected (mu=1 Asimov)")
    ax.axvline(125.09, color="gray", ls=":", lw=1, label="m_H = 125.09 GeV")
    ax.axhline(3, color="orange", ls=":", lw=1)
    ax.axhline(5, color="crimson", ls=":", lw=1)
    ax.set_xlabel("m_H hypothesis [GeV]")
    ax.set_ylabel("Local Z = sqrt(q0)")
    ax.set_title("Observed local significance vs m_H, with expectation overlaid")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "local_p_curve.png", dpi=140)
    plt.close(fig)
    print("  wrote local_p_curve.png")


def plot_mu_profile_scan(data_counts, alt_params):
    names = M.full_param_names()
    base = F.default_start(names, mu_start=1.0)
    mu_hat = alt_params["mu"]
    mus = np.linspace(mu_hat - 1.2, mu_hat + 1.2, 25)
    nlls = []
    warm = dict(alt_params)
    for mu_val in mus:
        fr = F.fit_model(data_counts, MH_NOMINAL, names, mu_fixed=float(mu_val), n_starts=2, base_start=warm)
        nlls.append(fr.nll)
        if fr.valid:
            warm = dict(fr.params)
            warm["mu"] = mu_val
    nlls = np.array(nlls)
    nll_hat = nlls.min()
    twice_dnll = 2.0 * (nlls - nll_hat)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(mus, twice_dnll, "b-o", ms=3)
    ax.axhline(1.0, color="orange", ls="--", lw=1, label="Delta(-2lnL) = 1 (1 sigma)")
    ax.axhline(4.0, color="crimson", ls="--", lw=1, label="Delta(-2lnL) = 4 (2 sigma)")
    ax.axvline(mu_hat, color="k", ls=":", lw=1)
    ax.set_xlabel("mu")
    ax.set_ylabel("-2 Delta ln L")
    ax.set_title(f"Profile-likelihood scan of mu (mu_hat={mu_hat:.3f})")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "mu_profile_scan.png", dpi=140)
    plt.close(fig)
    print("  wrote mu_profile_scan.png")


def plot_robustness_summary(primary_Z, primary_mu):
    pp = json.loads(POSTPROCESS_JSON.read_text(encoding="utf-8"))
    rows = [("Primary (105-180, full model)", primary_Z, primary_mu)]
    rows.append(("(i) 110-180, stat-only", pp["robustness_i_110_180"]["Z"], pp["robustness_i_110_180"]["mu_hat"]))
    rows.append(("(ii) bernstein_5", pp["robustness_ii_bernstein5"]["Z"], pp["robustness_ii_bernstein5"]["mu_hat"]))
    rows.append(("(iii) no spurious terms", pp["robustness_iii_no_spurious"]["Z"], pp["robustness_iii_no_spurious"]["mu_hat"]))
    rows.append(("(iv) EBEB alone", None, None))  # filled from primary JSON in the caller if desired
    rows.append(("(iv) notEBEB alone", None, None))
    rp = pp["robustness_v_run_periods"]
    rows.append(("(v) Run2016G", rp["Run2016G"]["Z"], rp["Run2016G"]["mu_hat"]))
    rows.append(("(v) Run2016H", rp["Run2016H"]["Z"], rp["Run2016H"]["mu_hat"]))
    rows.append(("(vi) scale/res fixed", pp["robustness_vi_scale_res_fixed"]["Z"],
                 pp["robustness_vi_scale_res_fixed"]["mu_hat"]))
    rows = [r for r in rows if r[1] is not None]

    labels = [r[0] for r in rows]
    zs = [r[1] for r in rows]
    mus = [r[2] for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    y = np.arange(len(labels))
    ax1.barh(y, zs, color="#3f7fa8")
    ax1.axvline(primary_Z, color="k", ls="--", lw=1)
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels, fontsize=8)
    ax1.set_xlabel("Z")
    ax1.set_title("Local Z across robustness checks")
    ax1.invert_yaxis()

    ax2.barh(y, mus, color="#a83f5b")
    ax2.axvline(primary_mu, color="k", ls="--", lw=1)
    ax2.axvline(1.0, color="gray", ls=":", lw=1)
    ax2.set_yticks(y)
    ax2.set_yticklabels([])
    ax2.set_xlabel("mu_hat")
    ax2.set_title("mu_hat across robustness checks")
    ax2.invert_yaxis()

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "robustness_summary.png", dpi=140)
    plt.close(fig)
    print("  wrote robustness_summary.png")


def main():
    print("Refitting primary (same procedure as run_unblinded_analysis.py) to get full parameters...")
    data_counts = load_real_data_counts()
    null, alt = refit_primary(data_counts)
    print(f"  mu_hat={alt.params['mu']:.4f} (cross-check against the gated primary result)")

    edges_fine = M.edges()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Plotting category spectra...")
    for cat in M.CATEGORIES:
        plot_category_spectrum(cat, data_counts, null.params, alt.params, edges_fine)

    print("Plotting S/B-weighted combined spectrum...")
    plot_combined_sb_weighted(data_counts, null.params, alt.params, edges_fine)

    print("Plotting local-p curve...")
    plot_local_p_curve()

    print("Plotting mu profile-likelihood scan...")
    plot_mu_profile_scan(data_counts, alt.params)

    print("Plotting robustness summary...")
    q0info = F.q0_from_fits(null, alt)
    plot_robustness_summary(q0info["Z"], alt.params["mu"])

    print("done")


if __name__ == "__main__":
    main()
