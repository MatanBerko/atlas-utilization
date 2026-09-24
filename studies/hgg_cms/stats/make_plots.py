"""
Statistical-model task: renders the plots STATS_REPORT.md references
from `results/expected_significance.json` (Part 3, computed for real)
and -- once pasted back -- `results/hgg_stats_merged.json` (Parts 2 and
3.3/3.5, from the cluster). Run again after the cluster results land to
fill in the toy-based plots that are placeholders until then.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PLOTS_DIR = RESULTS_DIR / "plots"


def plot_mass_scan():
    d = json.loads((RESULTS_DIR / "expected_significance.json").read_text(encoding="utf-8"))
    scan = d["part_3_4_mass_scan"]["scan"]
    mH = [r["mH"] for r in scan]
    Z = [r["Z"] for r in scan]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(mH, Z, "-o", ms=3, color="#1f5fa8")
    ax.axvline(125.09, color="gray", ls="--", lw=1, label="m_H = 125.09 GeV (truth)")
    ax.axhline(3, color="orange", ls=":", lw=1, label="Z = 3 (evidence)")
    ax.axhline(5, color="crimson", ls=":", lw=1, label="Z = 5 (observation)")
    ax.set_xlabel("Tested m_H hypothesis [GeV]")
    ax.set_ylabel("Expected local Z (Asimov, mu=1, full model)")
    ax.set_title("Expected local significance vs m_H\n(one Asimov dataset, truth at 125.09 GeV)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOTS_DIR / "expected_local_significance_vs_mH.png", dpi=140)
    plt.close(fig)
    print(f"wrote {PLOTS_DIR / 'expected_local_significance_vs_mH.png'}")


def _bar_from_hist(ax, h, **kwargs):
    edges = np.array(h["bin_edges"])
    counts = np.array(h["counts"])
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = edges[1] - edges[0]
    density = counts / (counts.sum() * width) if counts.sum() else counts
    ax.bar(centers, density, width=width * 0.95, **kwargs)
    return density, centers


def plot_q0_distribution(d):
    h = d.get("part_2_1_background_only", {}).get("Z_histogram")
    if not h or h["n"] == 0:
        print("  no bkg_only Z_histogram in merged JSON -- skipping q0 plot")
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    _bar_from_hist(ax, h, color="#1f5fa8", alpha=0.75, label=f"background-only toys (n={h['n']})")
    from scipy import stats as sps
    zz = np.linspace(0.001, max(h["bin_edges"]), 400)
    # half-delta(0) + half-chi2_1 in Z: the Z>0 half is a folded unit
    # normal, density = 2*phi(z) for z>0, weight 1/2 (the other half is
    # the delta at Z=0, not drawn as a density spike).
    ax.plot(zz, sps.norm.pdf(zz) * 2 * 0.5, "r-", lw=2,
            label="asymptotic: 1/2 delta(0) + 1/2 chi2_1 (Z>0 half shown)")
    ax.set_xlabel("Z = sqrt(q0)")
    ax.set_ylabel("density")
    ax.set_title("Background-only toy q0 distribution vs asymptotic")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "q0_distribution.png", dpi=140)
    plt.close(fig)
    print(f"  wrote {PLOTS_DIR / 'q0_distribution.png'}")


def plot_pull_distributions(d):
    sig = d.get("part_2_2_signal_injection", {})
    if not sig:
        print("  no sig_injection block in merged JSON -- skipping pull plot")
        return
    fig, axes = plt.subplots(1, len(sig), figsize=(5 * len(sig), 4.5), squeeze=False)
    for ax, (mu_str, entry) in zip(axes[0], sorted(sig.items(), key=lambda kv: float(kv[0]))):
        true_h = entry.get("true_pull_histogram")
        if true_h and true_h["n"] > 0:
            _bar_from_hist(ax, true_h, color="#2a9d3f", alpha=0.75)
            from scipy import stats as sps
            xx = np.linspace(-4, 4, 300)
            ax.plot(xx, sps.norm.pdf(xx), "r-", lw=2, label="unit normal")
            ax.set_xlabel("pull = (mu_hat - mu_true) / mu_err")
            ax.set_title(f"mu_true={mu_str}\nTRUE pull (n={true_h['n']})")
        else:
            resid_h = entry.get("mu_hat_residual_histogram")
            if resid_h and resid_h["n"] > 0:
                _bar_from_hist(ax, resid_h, color="#e07a1f", alpha=0.75)
            ax.set_xlabel("mu_hat - mu_true  (NOT divided by mu_err -- see STATS_REPORT.md)")
            ax.set_title(f"mu_true={mu_str}\nresidual only, no mu_err in this toy set")
        ax.set_ylabel("density")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "pull_distributions.png", dpi=140)
    plt.close(fig)
    print(f"  wrote {PLOTS_DIR / 'pull_distributions.png'}")


def plot_expected_band(d):
    band = d.get("part_3_3_expected_band_mu1")
    if not band or not band.get("Z_histogram"):
        print("  no part_3_3_expected_band_mu1 in merged JSON -- skipping band plot")
        return
    h = band["Z_histogram"]
    fig, ax = plt.subplots(figsize=(7, 5))
    _bar_from_hist(ax, h, color="#5b3fa8", alpha=0.75, label=f"mu_true=1 toys (n={h['n']})")
    ax.axvline(band["median_Z"], color="k", lw=2, label=f"median Z = {band['median_Z']:.2f}")
    ax.axvspan(band["Z_16pct"], band["Z_84pct"], color="gray", alpha=0.25,
               label=f"16-84% band [{band['Z_16pct']:.2f}, {band['Z_84pct']:.2f}]")
    ax.axvline(3, color="orange", ls=":", label="Z=3")
    ax.axvline(5, color="crimson", ls=":", label="Z=5")
    ax.set_xlabel("Z (observed per toy)")
    ax.set_ylabel("density")
    ax.set_title("Expected significance band at mu_true=1, m_H=125.09 GeV")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "expected_Z_band.png", dpi=140)
    plt.close(fig)
    print(f"  wrote {PLOTS_DIR / 'expected_Z_band.png'}")


def plot_max_local_z(d):
    le = d.get("part_3_5_look_elsewhere", {})
    h = le.get("max_Z_histogram")
    if not h or h["n"] == 0:
        print("  no part_3_5_look_elsewhere max_Z_histogram in merged JSON -- skipping max-Z plot")
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    _bar_from_hist(ax, h, color="#a83f5b", alpha=0.75, label=f"background-only toys (n={h['n']})")
    ax.axvline(3, color="orange", ls=":", label="local Z=3")
    gv = le.get("gross_vitells")
    title = "Max local Z over 110-150 GeV (background-only toys)"
    if gv:
        title += (f"\ntrials factor @Z=3: toys={le['trials_factor']['local_Z_3.0']['trials_factor']:.1f}, "
                  f"GV={gv['trials_factor_at_local_Z_3']:.1f}")
    ax.set_xlabel("max local Z over the scan")
    ax.set_ylabel("density")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "max_local_Z_distribution.png", dpi=140)
    plt.close(fig)
    print(f"  wrote {PLOTS_DIR / 'max_local_Z_distribution.png'}")


def plot_toy_results_if_available():
    merged_path = RESULTS_DIR / "hgg_stats_merged.json"
    if not merged_path.exists():
        print(f"{merged_path} not found -- cluster toy results not pasted back yet; "
              f"skipping q0/pull/band plots (see STATS_REPORT.md's own PENDING notes).")
        return
    d = json.loads(merged_path.read_text(encoding="utf-8"))
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"found {merged_path} -- rendering toy-based plots:")
    plot_q0_distribution(d)
    plot_pull_distributions(d)
    plot_expected_band(d)
    plot_max_local_z(d)


if __name__ == "__main__":
    plot_mass_scan()
    plot_toy_results_if_available()
