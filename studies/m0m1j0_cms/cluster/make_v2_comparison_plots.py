#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- v2: final data-vs-ttbar comparison plots.

Reads the two already-merged, already-post-processed ROOT files (data:
studies/m0m1j0_cms/v2/data/m0m1j0_data_postprocessed.root; ttbar:
studies/m0m1j0_cms/v2/ttbar/m0m1j0_ttbar_postprocessed.root) directly --
no cluster access needed, no recomputation, purely a plotting step over
already-committed numbers.

Produces exactly the 4 plots the task's "Final plots" section asks for,
under studies/m0m1j0_cms/v2/plots/:
  1. inclusive_m0m1j0_data.png        -- data, log y, the specified
                                          axis labels/legend.
  2. inclusive_m0m1j0_ttbar.png       -- ttbar, the same style.
  3. data_vs_ttbar_inclusive_normalized.png
     data_vs_ttbar_2mu1j0b_normalized.png
                                       -- both samples normalised to unit
                                          area, log y, for the inclusive
                                          histograms AND separately for
                                          the 2mu1j0b category -- clearly
                                          labeled "shapes only, not a
                                          background prediction".
  4. top5_categories_data.png / top5_categories_ttbar.png
                                       -- top-5 categories by event count,
                                          one plot per sample.

Usage:
    python make_v2_comparison_plots.py \
        --data-root studies/m0m1j0_cms/v2/data/m0m1j0_data_postprocessed.root \
        --ttbar-root studies/m0m1j0_cms/v2/ttbar/m0m1j0_ttbar_postprocessed.root \
        --out-dir studies/m0m1j0_cms/v2/plots
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

CAT_2MU1J0B = "mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx"
DATA_INCLUSIVE = "mass_m0m1j0_inclusive_ge2m_ge1j_v2_postprocessed"
TTBAR_INCLUSIVE = "mass_m0m1j0_inclusive_ge2m_ge1j_ttbar_postprocessed"


def _strip(root_name: str) -> str:
    name = root_name[len("ROI_"):] if root_name.startswith("ROI_") else root_name
    return re.sub(r"_width_\d+(?:_genWeightSum)?$", "", name)


def load_histograms(root_path: Path) -> dict:
    """{grouping_name: (values, edges)}."""
    f = uproot.open(str(root_path))
    out = {}
    for key in f.keys(cycle=False):
        h = f[key]
        out[_strip(key)] = (h.values(), h.axis().edges())
    return out


def plot_inclusive_single(values: np.ndarray, edges: np.ndarray, label: str, title: str, out_path: Path):
    nonzero = np.nonzero(values)[0]
    last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
    centers = (edges[:-1] + edges[1:]) / 2
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.step(centers[:last_bin], values[:last_bin], where="mid", color="#c44e52", label=label)
    ax.set_yscale("log")
    ax.set_xlabel("m(μμ j) [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_normalized_overlay(data_vv: tuple, ttbar_vv: tuple, title: str, out_path: Path):
    d_values, d_edges = data_vv
    t_values, t_edges = ttbar_vv
    assert np.array_equal(d_edges, t_edges), "data and ttbar must share the same fixed grid"

    nonzero = np.nonzero(d_values + t_values)[0]
    last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
    centers = (d_edges[:-1] + d_edges[1:]) / 2

    d_norm = d_values / d_values.sum() if d_values.sum() > 0 else d_values
    t_norm = t_values / t_values.sum() if t_values.sum() > 0 else t_values

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.step(centers[:last_bin], d_norm[:last_bin], where="mid", color="#4c72b0",
             label=f"CMS Open Data 2016G+H, DoubleMuon (n={int(d_values.sum())})")
    ax.step(centers[:last_bin], t_norm[:last_bin], where="mid", color="#8172b3",
             label=f"ttbar MC, TTTo2L2Nu (n={int(t_values.sum())})")
    ax.set_yscale("log")
    ax.set_xlabel("m(μμ j) [GeV]")
    ax.set_ylabel("Normalized events / 10 GeV")
    ax.set_title(f"{title}\n(shapes only, not a background prediction)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_top5(hists: dict, inclusive_label: str, title: str, out_path: Path):
    scored = []
    for label, (values, edges) in hists.items():
        if label == inclusive_label:
            continue
        scored.append((int(values.sum()), label, values, edges))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:5]

    fig, ax = plt.subplots(figsize=(8, 5))
    for n, label, values, edges in top:
        nonzero = np.nonzero(values)[0]
        last_bin = int(nonzero.max()) + 1 if len(nonzero) else 10
        centers = (edges[:-1] + edges[1:]) / 2
        ax.step(centers[:last_bin], values[:last_bin], where="mid", label=f"{label} (n={n})")
    ax.set_yscale("log")
    ax.set_xlabel("m0m1j0 [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title(title)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return [{"category": label, "n_events": n} for n, label, _, _ in top]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", required=True)
    p.add_argument("--ttbar-root", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data_hists = load_histograms(Path(args.data_root))
    ttbar_hists = load_histograms(Path(args.ttbar_root))

    if DATA_INCLUSIVE not in data_hists:
        raise ValueError(f"{DATA_INCLUSIVE!r} not found in {args.data_root} -- found: {sorted(data_hists)}")
    if TTBAR_INCLUSIVE not in ttbar_hists:
        raise ValueError(f"{TTBAR_INCLUSIVE!r} not found in {args.ttbar_root} -- found: {sorted(ttbar_hists)}")
    if CAT_2MU1J0B not in data_hists:
        raise ValueError(f"{CAT_2MU1J0B!r} not found in data histograms -- found: {sorted(data_hists)}")
    if CAT_2MU1J0B not in ttbar_hists:
        raise ValueError(f"{CAT_2MU1J0B!r} not found in ttbar histograms -- found: {sorted(ttbar_hists)}")

    # 1 & 2: single-sample inclusive plots
    d_values, d_edges = data_hists[DATA_INCLUSIVE]
    plot_inclusive_single(
        d_values, d_edges, "CMS Open Data 2016G+H, DoubleMuon",
        "m0m1j0 -- CMS Open Data 2016G+H, DoubleMuon (post-processed)",
        out_dir / "inclusive_m0m1j0_data.png",
    )
    t_values, t_edges = ttbar_hists[TTBAR_INCLUSIVE]
    plot_inclusive_single(
        t_values, t_edges, "ttbar MC, TTTo2L2Nu (record 67801)",
        "m0m1j0 -- ttbar MC, TTTo2L2Nu (post-processed)",
        out_dir / "inclusive_m0m1j0_ttbar.png",
    )

    # 3: normalized shape overlays
    plot_normalized_overlay(
        data_hists[DATA_INCLUSIVE], ttbar_hists[TTBAR_INCLUSIVE],
        "m0m1j0 shape comparison: data vs ttbar (inclusive)",
        out_dir / "data_vs_ttbar_inclusive_normalized.png",
    )
    plot_normalized_overlay(
        data_hists[CAT_2MU1J0B], ttbar_hists[CAT_2MU1J0B],
        "m0m1j0 shape comparison: data vs ttbar (2mu1j0b category)",
        out_dir / "data_vs_ttbar_2mu1j0b_normalized.png",
    )

    # 4: top-5 categories per sample
    top5_data = plot_top5(data_hists, DATA_INCLUSIVE, "Data (post-processed): top 5 categories", out_dir / "top5_categories_data.png")
    top5_ttbar = plot_top5(ttbar_hists, TTBAR_INCLUSIVE, "ttbar MC (post-processed): top 5 categories", out_dir / "top5_categories_ttbar.png")

    print("wrote 8 PNGs under", out_dir)
    print("top5 data:", top5_data)
    print("top5 ttbar:", top5_ttbar)


if __name__ == "__main__":
    main()
