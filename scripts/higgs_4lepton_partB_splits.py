#!/usr/bin/env python3
"""
H -> ZZ -> 4l Part B: cheap verification checks on the existing full-scale
result (535 primary candidates) -- NO new parsing. Reads the same parsed
ROOT chunks already on Lustre and reapplies the identical Part B selection
(Part A + sip3d<4, |dxy|<0.5 cm, |dz|<1.0 cm) via
scripts/higgs_4lepton_partB_report.py's load_events/build_selected_leptons/
run_selection, reused rather than rewritten.

TASK 1 -- split-sample test: rebuild the 70-180 GeV / 3 GeV mass histogram
separately for two independent splits (era: 2016G vs 2016H; event-number
parity: even vs odd) and report whether the 118-130 GeV excess / any
123.5-126.5 GeV feature appears in BOTH halves of BOTH splits. A real
signal should appear in both halves of a split; a fluctuation typically
will not.

TASK 2 -- unbinned extended-maximum-likelihood fit of a Gaussian signal on
a flat local background to the 115-135 GeV candidates, reporting fitted
mean/width/yield with 1-sigma uncertainties from the fit's Hessian. This is
a parameter-estimation fit ONLY.

NO significance/p-value/sigma is computed or implied anywhere. No
selection tuning: the exact same Part B working point (sip3d<4, |dxy|<0.5,
|dz|<1.0, Part A cuts unchanged) is used throughout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from higgs_4lepton_partB_report import load_events, build_selected_leptons, run_selection  # noqa: E402

BIN_LO, BIN_HI, N_BINS = 70.0, 180.0, 37

# Genuinely separate data-taking periods (2016 Run G vs Run H), each with its
# own DoubleEG/DoubleMuon/MuonEG trigger-stream record.
ERA_G = {30521, 30522, 30528}
ERA_H = {30554, 30555, 30561}


def window_count(masses, lo, hi):
    m = np.asarray(masses)
    return int(((m >= lo) & (m < hi)).sum())


def summarize_half(name, cands):
    m4l = np.array([c["m4l"] for c in cands]) if cands else np.array([])
    z1 = np.array([c["m_z1"] for c in cands]) if cands else np.array([])
    n_peak = int(((z1 >= 85) & (z1 <= 97)).sum()) if len(z1) else 0
    return {
        "label": name,
        "n_candidates": len(cands),
        "n_70_180": window_count(m4l, BIN_LO, BIN_HI),
        "n_118_130": window_count(m4l, 118.0, 130.0),
        "n_120_5_123_5_before": window_count(m4l, 120.5, 123.5),
        "n_123_5_126_5": window_count(m4l, 123.5, 126.5),
        "n_126_5_129_5_after": window_count(m4l, 126.5, 129.5),
        "n_zpeak_85_97": n_peak,
        "n_z1_total": len(z1),
        "zpeak_fraction": (n_peak / len(z1)) if len(z1) else None,
    }


def plot_split(halves, names, colors, out_png, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    edges = np.linspace(BIN_LO, BIN_HI, N_BINS + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    w = edges[1] - edges[0]

    fig, ax = plt.subplots(figsize=(11, 6))
    offsets = (-0.22, 0.22)
    for cands, name, color, off in zip(halves, names, colors, offsets):
        m = np.array([c["m4l"] for c in cands]) if cands else np.array([])
        counts, _ = np.histogram(m, bins=edges)
        ax.bar(centers + off * w, counts, width=w * 0.42, color=color, alpha=0.85,
               label=f"{name} ({len(cands)} candidates)")
    ax.axvline(125.0, color="#333333", ls="--", lw=1)
    ax.set_xlabel("4-lepton invariant mass [GeV]")
    ax.set_ylabel(f"candidates / {w:.2f} GeV")
    ax.set_title(f"{title}\nDescriptive only -- no significance, p-value, or sigma computed or implied")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def fit_gaussian_plus_flat(masses, lo=115.0, hi=135.0):
    """Unbinned extended-maximum-likelihood fit: Gaussian signal
    (mu, sigma, n_sig) on a FLAT local background (n_bkg = N - n_sig) over
    [lo, hi]. n_sig is reparametrized through a sigmoid (n_sig = N/(1+e^-p))
    so the optimizer can't wander into an unphysical n_sig<0 or >N region;
    sigma is fit in log-space to keep it positive. A parameter-estimation
    fit only -- no significance/p-value is derived from it anywhere.
    Uncertainties are the sqrt of the diagonal of the fit's BFGS inverse-
    Hessian approximation, propagated through the reparametrizations."""
    from scipy import optimize
    from scipy.stats import norm

    m = np.asarray(masses)
    N = len(m)
    width = hi - lo

    def transform(params):
        mu, log_sigma, p = params
        sigma = np.exp(log_sigma)
        n_sig = N / (1.0 + np.exp(-p))
        return mu, sigma, n_sig

    def neg_log_l(params):
        mu, sigma, n_sig = transform(params)
        n_bkg = N - n_sig
        norm_trunc = norm.cdf(hi, mu, sigma) - norm.cdf(lo, mu, sigma)
        norm_trunc = max(norm_trunc, 1e-12)
        sig_pdf = norm.pdf(m, mu, sigma) / norm_trunc
        bkg_pdf = 1.0 / width
        pdf = (n_sig * sig_pdf + n_bkg * bkg_pdf) / N
        pdf = np.clip(pdf, 1e-300, None)
        return -np.sum(np.log(pdf))

    x0 = np.array([125.0, np.log(2.0), 0.0])  # p=0 -> n_sig starts at N/2
    res = optimize.minimize(neg_log_l, x0, method="BFGS")

    mu_fit, sigma_fit, n_sig_fit = transform(res.x)
    p_fit = res.x[2]

    cov = res.hess_inv
    mu_err = float(np.sqrt(max(cov[0, 0], 0.0)))
    log_sigma_err = float(np.sqrt(max(cov[1, 1], 0.0)))
    sigma_err = float(sigma_fit * log_sigma_err)
    p_err = float(np.sqrt(max(cov[2, 2], 0.0)))
    dn_dp = n_sig_fit * (1.0 - n_sig_fit / N)  # d(n_sig)/dp
    n_sig_err = float(abs(dn_dp) * p_err)

    return {
        "n_candidates_fit_window": N,
        "fit_window_gev": [lo, hi],
        "background_model": "flat",
        "method": "unbinned extended max-likelihood (BFGS)",
        "mu_fit_gev": float(mu_fit), "mu_err_gev": mu_err,
        "sigma_fit_gev": float(sigma_fit), "sigma_err_gev": sigma_err,
        "n_sig_fit": float(n_sig_fit), "n_sig_err": n_sig_err,
        "n_bkg_fit": float(N - n_sig_fit),
        "converged": bool(res.success),
    }


def plot_fit(masses, fit, out_png, lo=115.0, hi=135.0, nbins_display=10):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import norm

    m = np.asarray(masses)
    edges = np.linspace(lo, hi, nbins_display + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    w = edges[1] - edges[0]
    counts, _ = np.histogram(m, bins=edges)

    mu, sigma, n_sig, n_bkg = fit["mu_fit_gev"], fit["sigma_fit_gev"], fit["n_sig_fit"], fit["n_bkg_fit"]
    xs = np.linspace(lo, hi, 400)
    norm_trunc = norm.cdf(hi, mu, sigma) - norm.cdf(lo, mu, sigma)
    sig_curve = n_sig * norm.pdf(xs, mu, sigma) / norm_trunc
    bkg_curve = np.full_like(xs, n_bkg / (hi - lo))
    total_curve = sig_curve + bkg_curve

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.bar(centers, counts, width=w * 0.9, color="#4477aa", alpha=0.6, label=f"data ({len(m)} candidates)")
    ax.plot(xs, total_curve * w, color="#cc3311", lw=1.8, label="fit: signal (Gaussian) + flat background")
    ax.plot(xs, bkg_curve * w, color="#888888", ls="--", lw=1.3, label="flat background component")
    ax.axvline(125.25, color="#333333", ls=":", lw=1.2, label="125.25 GeV (measured Higgs mass)")
    ax.set_xlabel("4-lepton invariant mass [GeV]")
    ax.set_ylabel(f"candidates / {w:.2f} GeV")
    ax.set_title(
        f"Unbinned fit: mu={mu:.2f}+/-{fit['mu_err_gev']:.2f} GeV, "
        f"sigma={sigma:.2f}+/-{fit['sigma_err_gev']:.2f} GeV, "
        f"n_sig={n_sig:.1f}+/-{fit['n_sig_err']:.1f}\n"
        "Parameter-estimation fit only -- no significance, p-value, or sigma-significance computed"
    )
    ax.legend(fontsize=8.5)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    events, n_events, file_rows = load_events(args.run_dir)
    print(f"loaded {n_events:,} events from {len(file_rows)} chunk file(s)")

    leptons = build_selected_leptons(events, use_sip3d=True, use_dxy=True, use_dz=True)
    cutflow, candidates = run_selection(events, leptons)
    print(f"primary candidates: {len(candidates)} (cross-check vs. the earlier full-scale run's 535)")

    # ---- TASK 1: split-sample test ----
    era_g = [c for c in candidates if c["source_record"] in ERA_G]
    era_h = [c for c in candidates if c["source_record"] in ERA_H]
    even = [c for c in candidates if c["event"] % 2 == 0]
    odd = [c for c in candidates if c["event"] % 2 == 1]

    splits = {"era_2016G": era_g, "era_2016H": era_h, "parity_even": even, "parity_odd": odd}
    split_summary = {k: summarize_half(k, v) for k, v in splits.items()}
    for k, s in split_summary.items():
        print(f"\n=== {k} ===")
        print(json.dumps(s, indent=2))

    plot_split([era_g, era_h], ["2016G (30521/30522/30528)", "2016H (30554/30555/30561)"],
               ["#4477aa", "#cc3311"], out / "plots" / "partB_split_era.png",
               "H->ZZ->4l Part B: split by data-taking era")
    plot_split([even, odd], ["even event number", "odd event number"],
               ["#228833", "#aa4499"], out / "plots" / "partB_split_parity.png",
               "H->ZZ->4l Part B: split by event-number parity")

    # ---- TASK 2: Gaussian + flat background fit, 115-135 GeV ----
    m_115_135 = np.array([c["m4l"] for c in candidates if 115.0 <= c["m4l"] <= 135.0])
    fit = fit_gaussian_plus_flat(m_115_135)
    print("\n=== Gaussian+flat unbinned fit, 115-135 GeV ===")
    print(json.dumps(fit, indent=2))
    plot_fit(m_115_135, fit, out / "plots" / "partB_115_135_fit.png")

    stats = {
        "n_primary_candidates": len(candidates),
        "split_summary": split_summary,
        "fit_115_135": fit,
    }
    (out / "partB_splits_and_fit_stats.json").write_text(json.dumps(stats, indent=2))
    print(f"\nwrote {out / 'partB_splits_and_fit_stats.json'}")


if __name__ == "__main__":
    main()
