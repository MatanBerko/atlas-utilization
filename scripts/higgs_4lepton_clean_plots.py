#!/usr/bin/env python3
"""Plots for Part A (cheap cuts on existing data). Reads partA_stats.json."""
import argparse
import json
from pathlib import Path

import numpy as np

RECORD_NAMES = {
    30521: "DoubleEG G", 30554: "DoubleEG H", 30522: "DoubleMuon G",
    30555: "DoubleMuon H", 30528: "MuonEG G", 30561: "MuonEG H",
}
BIN_LO, BIN_HI, N_BINS = 70.0, 180.0, 37


def plot_cutflow(cutflow, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    stages = [
        ("parse-time\nselection", "after_parse_time_selection"),
        (">=4 quality\nleptons", "after_ge4_quality_leptons"),
        ("exactly 4,\ncharge 0", "exactly4_charge0"),
        ("A1: low-mass\nveto (>4 GeV)", "after_low_mass_veto"),
        ("A2: ghost\nremoval (dR>0.02)", "after_ghost_removal"),
        ("pT thresholds\n(20/10 GeV)", "after_pt_thresholds"),
        ("valid Z1/Z2,\nfinal", "final_candidates"),
    ]
    records = cutflow["records"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    ax = axes[0]
    x = np.arange(len(stages))
    colors = plt.cm.tab10(np.linspace(0, 1, len(records)))
    for r, c in zip(records, colors):
        vals = [cutflow[key][str(r)] for _, key in stages]
        ax.plot(x, vals, marker="o", label=f"{r} ({RECORD_NAMES.get(r, '')})", color=c)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([s[0] for s in stages], fontsize=7.5)
    ax.set_ylabel("events")
    ax.set_title("Cut-flow per record (Part A: A1 low-mass veto + A2 ghost removal added)")
    ax.legend(fontsize=7, loc="upper right")

    ax2 = axes[1]
    vals = [cutflow[key]["combined"] for _, key in stages]
    bars = ax2.bar(x, vals, color="#4477aa")
    for xi, v in zip(x, vals):
        ax2.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=8)
    # highlight A1/A2 marginal drops
    ax2.set_yscale("log")
    ax2.set_xticks(x)
    ax2.set_xticklabels([s[0] for s in stages], fontsize=7.5)
    ax2.set_ylabel("events")
    ax2.set_title("Cut-flow, combined (all 6 records)")

    fig.suptitle("H->ZZ->4l Part A cut-flow: cheap background-rejection cuts on existing parsed data")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def plot_baseline_vs_cleaned(baseline_cands, cleaned_cands, out_png,
                              baseline_label="baseline (no A1/A2)",
                              cleaned_label="cleaned (+A1 low-mass veto +A2 ghost removal)"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    edges = np.linspace(BIN_LO, BIN_HI, N_BINS + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    m_base = np.array([c["m4l"] for c in baseline_cands])
    m_clean = np.array([c["m4l"] for c in cleaned_cands])
    c_base, _ = np.histogram(m_base, bins=edges)
    c_clean, _ = np.histogram(m_clean, bins=edges)

    fig, ax = plt.subplots(figsize=(10, 6))
    w = (edges[1] - edges[0])
    ax.bar(centers - w * 0.22, c_base, width=w * 0.42, color="#cc3311", alpha=0.75,
           label=f"{baseline_label}, {int(c_base.sum())} in window")
    ax.bar(centers + w * 0.22, c_clean, width=w * 0.42, color="#4477aa",
           label=f"{cleaned_label}, {int(c_clean.sum())} in window")
    ax.axvline(91.1876, color="#888888", ls="--", lw=1)
    ax.axvline(125.0, color="#333333", ls="--", lw=1)
    ax.set_xlabel("4-lepton invariant mass [GeV]")
    ax.set_ylabel(f"candidates / {w:.2f} GeV")
    ax.set_title(
        "H->ZZ->4l mass spectrum: baseline vs. Part A cleaned selection\n"
        "Descriptive only -- no significance, p-value, or sigma computed or implied"
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def plot_channel_breakdown(by_channel, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    channels = ["4mu", "2e2mu", "4e"]
    vals = [by_channel.get(c, 0) for c in channels]
    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(channels, vals, color=["#4477aa", "#cc3311", "#228833"])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}", ha="center", va="bottom")
    ax.set_ylabel("final candidates")
    ax.set_title(f"Part A cleaned candidates by channel (total {sum(vals):,})")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def plot_z1_validation(candidates, out_png, label):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    z1 = np.array([c["m_z1"] for c in candidates])
    edges = np.arange(40, 121, 2.5)
    centers = 0.5 * (edges[:-1] + edges[1:])
    counts, _ = np.histogram(z1, bins=edges)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.bar(centers, counts, width=2.3, color="#4477aa")
    ax.axvline(91.1876, color="#cc3311", ls="--", lw=1.3, label="91.1876 GeV (Z mass)")
    n_peak = int(((z1 >= 85) & (z1 <= 97)).sum())
    ax.set_xlabel("Z1 pair mass [GeV]")
    ax.set_ylabel("candidates / 2.5 GeV")
    ax.set_title(
        f"{label}: {n_peak:,}/{len(z1):,} candidates ({100*n_peak/len(z1):.1f}%) "
        f"have m_Z1 in [85,97] GeV"
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats-json", required=True, type=Path)
    ap.add_argument("--baseline-json", required=True, type=Path,
                     help="the earlier fullscale_stats.json for baseline candidates")
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    d = json.loads(args.stats_json.read_text())
    base = json.loads(args.baseline_json.read_text())
    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    plot_cutflow(d["cleaned_cutflow"], out / "plots" / "partA_cutflow.png")
    plot_baseline_vs_cleaned(base["candidates"], d["cleaned_candidates"],
                              out / "plots" / "partA_mass_baseline_vs_cleaned.png")
    plot_channel_breakdown(d["cleaned_candidates_by_channel"], out / "plots" / "partA_channel_breakdown.png")
    plot_z1_validation(d["cleaned_candidates"], out / "plots" / "partA_z1_validation.png",
                        "Part A cleaned selection")


if __name__ == "__main__":
    main()
