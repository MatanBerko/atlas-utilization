#!/usr/bin/env python3
"""Plots for Part B (impact-parameter cuts on top of Part A). Reads the stats
JSON produced by scripts/higgs_4lepton_partB_report.py plus the pre-Part-B
baseline (reports/higgs_4lepton_zz/fullscale_stats.json, 2,216 candidates)
for direct comparison. Reuses Part A's plot_cutflow/plot_baseline_vs_cleaned/
plot_channel_breakdown/plot_z1_validation rather than rewriting them; only
plot_ip_cut_scan (comparing the sip3d/dxy/dz-only variants against the
combined selection) is new.

NO significance/p-value/sigma is computed anywhere. Purely descriptive.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent))
from higgs_4lepton_clean_plots import (  # noqa: E402
    plot_cutflow, plot_baseline_vs_cleaned, plot_channel_breakdown, plot_z1_validation,
)

RECORD_NAMES = {
    30521: "DoubleEG G", 30554: "DoubleEG H", 30522: "DoubleMuon G",
    30555: "DoubleMuon H", 30528: "MuonEG G", 30561: "MuonEG H",
}


def plot_ip_cut_scan(ip_cut_scan, out_png):
    """Bar chart of final-candidate counts across the 5 IP-cut variants
    (no cuts / sip3d-only / dxy-only / dz-only / all three combined),
    combined and per record -- shows which cut is doing the work."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    variant_names = list(ip_cut_scan.keys())
    short_labels = [n.split(" (")[0].replace("no_ip_cuts", "no IP cuts") for n in variant_names]

    records = sorted(
        int(r) for r in ip_cut_scan[variant_names[0]]["final_candidates_per_record"] if r != "combined"
    )

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    ax = axes[0]
    x = np.arange(len(variant_names))
    colors = plt.cm.tab10(np.linspace(0, 1, len(records)))
    for r, c in zip(records, colors):
        vals = [ip_cut_scan[n]["final_candidates_per_record"][str(r)] for n in variant_names]
        ax.plot(x, vals, marker="o", label=f"{r} ({RECORD_NAMES.get(r, '')})", color=c)
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels, fontsize=8, rotation=15, ha="right")
    ax.set_ylabel("final candidates")
    ax.set_title("Final candidates per record, by IP-cut variant")
    ax.legend(fontsize=7, loc="best")

    ax2 = axes[1]
    vals = [ip_cut_scan[n]["final_candidates_per_record"]["combined"] for n in variant_names]
    bars = ax2.bar(x, vals, color=["#888888", "#4477aa", "#66aa55", "#ccaa22", "#cc3311"][: len(vals)])
    for xi, v in zip(x, vals):
        ax2.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=9)
    ax2.set_xticks(x)
    ax2.set_xticklabels(short_labels, fontsize=8, rotation=15, ha="right")
    ax2.set_ylabel("final candidates (combined, all 6 records)")
    ax2.set_title("Combined final candidates, by IP-cut variant")

    fig.suptitle(
        "H->ZZ->4l Part B: individual vs. combined effect of sip3d/dxy/dz cuts\n"
        "each variant applied independently against the SAME Part A baseline (not a sequential cut-flow)"
    )
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    print(f"wrote {out_png}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats-json", required=True, type=Path)
    ap.add_argument("--baseline-json", required=True, type=Path,
                     help="pre-Part-B fullscale_stats.json (2,216 candidates) for comparison")
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    d = json.loads(args.stats_json.read_text())
    base = json.loads(args.baseline_json.read_text())
    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)

    plot_cutflow(d["primary_cutflow"], out / "plots" / "partB_cutflow.png")
    plot_ip_cut_scan(d["ip_cut_scan"], out / "plots" / "partB_ip_cut_scan.png")
    plot_baseline_vs_cleaned(
        base["candidates"], d["primary_candidates"],
        out / "plots" / "partB_mass_baseline_vs_partB.png",
        baseline_label="pre-Part-B laptop baseline (no A1/A2, no IP cuts)",
        cleaned_label="Part B (A1+A2+sip3d+dxy+dz)",
    )
    plot_channel_breakdown(d["primary_candidates_by_channel"], out / "plots" / "partB_channel_breakdown.png")
    plot_z1_validation(d["primary_candidates"], out / "plots" / "partB_z1_validation.png",
                        "Part B selection (Part A + sip3d/dxy/dz)")


if __name__ == "__main__":
    main()
