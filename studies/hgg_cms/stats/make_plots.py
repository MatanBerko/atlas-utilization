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


def plot_toy_results_if_available():
    merged_path = RESULTS_DIR / "hgg_stats_merged.json"
    if not merged_path.exists():
        print(f"{merged_path} not found -- cluster toy results not pasted back yet; "
              f"skipping q0/pull/band plots (see STATS_REPORT.md's own PENDING notes).")
        return
    d = json.loads(merged_path.read_text(encoding="utf-8"))
    print(f"found {merged_path} -- toy-based plots not yet implemented in this pass; "
          f"re-run this script after wiring in the merged toy arrays.")


if __name__ == "__main__":
    plot_mass_scan()
    plot_toy_results_if_available()
