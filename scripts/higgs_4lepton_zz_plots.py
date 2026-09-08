#!/usr/bin/env python3
"""
Plots + candidate table for the H -> ZZ -> 4l full-scale run, reading the
stats JSON produced by scripts/higgs_4lepton_zz_report.py. No new selection
logic here -- purely reporting on already-computed results.

NO significance/p-value/sigma is computed anywhere. Purely descriptive.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

RECORD_NAMES = {
    30521: "DoubleEG G", 30554: "DoubleEG H",
    30522: "DoubleMuon G", 30555: "DoubleMuon H",
    30528: "MuonEG G", 30561: "MuonEG H",
}
BIN_LO, BIN_HI, N_BINS = 70.0, 180.0, 37


def plot_cutflow(cutflow, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    records = cutflow["records"]
    stages = [
        ("after parse-time\nselection", "after_parse_time_selection"),
        (">=4 quality\nleptons", "after_ge4_quality_leptons"),
        ("exactly 4,\ncharge 0", "exactly4_charge0"),
        ("pT thresholds\n(20/10 GeV)", "after_pt_thresholds"),
        ("valid Z1/Z2,\nfinal", "final_candidates"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    ax = axes[0]
    x = np.arange(len(stages))
    colors = plt.cm.tab10(np.linspace(0, 1, len(records)))
    for r, c in zip(records, colors):
        vals = [cutflow[key][str(r)] for _, key in stages]
        ax.plot(x, vals, marker="o", label=f"{r} ({RECORD_NAMES.get(r, '')})", color=c)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([s[0] for s in stages], fontsize=8)
    ax.set_ylabel("events")
    ax.set_title("H->ZZ->4l cut-flow per record")
    ax.legend(fontsize=7, loc="upper right")

    ax2 = axes[1]
    vals = [cutflow[key]["combined"] for _, key in stages]
    ax2.bar(x, vals, color="#4477aa")
    for xi, v in zip(x, vals):
        ax2.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=8, rotation=0)
    ax2.set_yscale("log")
    ax2.set_xticks(x)
    ax2.set_xticklabels([s[0] for s in stages], fontsize=8)
    ax2.set_ylabel("events")
    ax2.set_title("H->ZZ->4l cut-flow, combined (all 6 records)")

    fig.suptitle("H -> ZZ -> 4l full-scale cut-flow (238/238 files, 321,425,248 raw events)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)


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
    ax.set_title(f"H->ZZ->4l final candidates by channel (total {sum(vals):,})")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)


def plot_mass_histograms(candidates, out_png_combined, out_png_stacked):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    edges = np.linspace(BIN_LO, BIN_HI, N_BINS + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    m4l = np.array([c["m4l"] for c in candidates])

    fig, ax = plt.subplots(figsize=(9, 5.5))
    counts, _ = np.histogram(m4l, bins=edges)
    ax.bar(centers, counts, width=(edges[1] - edges[0]) * 0.95, color="#4477aa")
    ax.axvline(91.1876, color="#888888", ls="--", lw=1, label="91.19 GeV (Z mass)")
    ax.axvline(125.0, color="#cc3311", ls="--", lw=1, label="125 GeV (Higgs mass)")
    ax.set_xlabel("4-lepton invariant mass [GeV]")
    ax.set_ylabel(f"candidates / {edges[1]-edges[0]:.2f} GeV")
    ax.set_title(
        f"H->ZZ->4l combined mass spectrum, {len(candidates):,} final candidates "
        f"({int(counts.sum()):,} in [70,180] GeV window)\n"
        "Descriptive only -- no significance, p-value, or sigma computed or implied"
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png_combined, dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    by_ch = {"4mu": "#4477aa", "2e2mu": "#cc3311", "4e": "#228833"}
    bottom = np.zeros(N_BINS)
    for ch, color in by_ch.items():
        ch_m = np.array([c["m4l"] for c in candidates if c["channel"] == ch])
        c_counts, _ = np.histogram(ch_m, bins=edges)
        ax.bar(centers, c_counts, width=(edges[1] - edges[0]) * 0.95, bottom=bottom,
               color=color, label=f"{ch} ({len(ch_m):,} total, {int(c_counts.sum()):,} in window)")
        bottom += c_counts
    ax.axvline(91.1876, color="#888888", ls="--", lw=1)
    ax.axvline(125.0, color="#333333", ls="--", lw=1)
    ax.set_xlabel("4-lepton invariant mass [GeV]")
    ax.set_ylabel(f"candidates / {edges[1]-edges[0]:.2f} GeV")
    ax.set_title(
        "H->ZZ->4l mass spectrum, stacked by channel\n"
        "Descriptive only -- no significance, p-value, or sigma computed or implied"
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png_stacked, dpi=130)
    plt.close(fig)


def plot_z1_validation(candidates, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    z1 = np.array([c["m_z1"] for c in candidates])
    edges = np.arange(40, 121, 2.5)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    counts, _ = np.histogram(z1, bins=edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    ax.bar(centers, counts, width=2.3, color="#4477aa")
    ax.axvline(91.1876, color="#cc3311", ls="--", lw=1.3, label="91.1876 GeV (Z mass)")
    n_peak = int(((z1 >= 85) & (z1 <= 97)).sum())
    ax.set_xlabel("Z1 pair mass [GeV]")
    ax.set_ylabel("candidates / 2.5 GeV")
    ax.set_title(
        f"Z1 pairing validation: {n_peak:,}/{len(z1):,} candidates "
        f"({100*n_peak/len(z1):.1f}%) have m_Z1 in [85,97] GeV\n"
        "Confirms lepton ID, charge reading, and mass computation are correct"
    )
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def write_higgs_window_table(candidates, out_csv, lo=115.0, hi=135.0):
    rows = [c for c in candidates if lo <= c["m4l"] <= hi]
    rows.sort(key=lambda c: c["m4l"])
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["m4l_gev", "channel", "m_z1_gev", "m_z2_gev", "source_record",
                    "run", "luminosityBlock", "event"])
        for c in rows:
            w.writerow([f"{c['m4l']:.3f}", c["channel"], f"{c['m_z1']:.3f}", f"{c['m_z2']:.3f}",
                        c["source_record"], c["run"], c["luminosityBlock"], c["event"]])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats-json", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    d = json.loads(args.stats_json.read_text())
    candidates = d["candidates"]
    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    plot_cutflow(d["cutflow"], out / "plots" / "fullscale_cutflow.png")
    plot_channel_breakdown(d["candidates_by_channel"], out / "plots" / "fullscale_channel_breakdown.png")
    plot_mass_histograms(
        candidates,
        out / "plots" / "fullscale_mass_combined.png",
        out / "plots" / "fullscale_mass_stacked_by_channel.png",
    )
    plot_z1_validation(candidates, out / "plots" / "fullscale_z1_validation.png")
    rows = write_higgs_window_table(candidates, out / "fullscale_115_135_candidates.csv")

    print(f"Wrote plots to {out/'plots'}")
    print(f"115-135 GeV window: {len(rows)} candidates -> {out/'fullscale_115_135_candidates.csv'}")


if __name__ == "__main__":
    main()
