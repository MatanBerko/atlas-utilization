#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- selection-variants task (supervisor request).
Final assembly step: combines the two per-sample merge summaries
(merge_variants_data_summary.json, merge_variants_ttbar_summary.json) into
ONE comparison_summary.json (the task's own "single comparison JSON"
requirement), and produces every required PNG plot plus the optional
ttbar-cross-section-scaled comparison.

Run LOCALLY (not on the cluster) once both merge_variants.py invocations
(--sample data, --sample ttbar) have completed and written their per-
variant ROOT files under --variants-dir.

Usage:
    python make_variants_plots.py \
        --variants-dir studies/m0m1j0_cms/v3_variants
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms import variants  # noqa: E402
from studies.m0m1j0_cms.cluster.merge_variants import INCLUSIVE_LABEL_TEMPLATE  # noqa: E402

# ttbar cross-section scaling -- task's own "optional extra". Values given
# directly by the task, not derived: sigma(TTTo2L2Nu) = 88.29 pb (a
# standard/PDG-adjacent NNLO value for this process -- NOT published on the
# CERN Open Data portal for this record, confirmed absent in RECIPE.md
# section 8), L = 16.393 fb^-1 (the DoubleMuon dataset's luminosity, itself
# UNVERIFIED for DoubleMuon specifically -- established for DoubleEG, per
# the task's own instruction to say so).
TTBAR_XSEC_PB = 88.29
DOUBLEMUON_LUMI_FB_INV = 16.393
TTBAR_N_GENERATED = 43_546_000  # record 67801's own published total event count


def load_root_hist(root_path: Path, key_substr: str):
    """Finds the one key in root_path containing key_substr and returns
    (values, edges) via uproot's own .to_numpy()."""
    f = uproot.open(str(root_path))
    keys = [k.split(";")[0] for k in f.keys()]
    matches = [k for k in keys if key_substr in k]
    if not matches:
        return None
    values, edges = f[matches[0]].to_numpy()
    return values, edges


def inclusive_hist(variants_dir: Path, sample: str, variant_key: str):
    root_path = variants_dir / f"{sample}_{variant_key}.root"
    if not root_path.exists():
        return None
    return load_root_hist(root_path, "inclusive")


def overlay_with_ratio(sample: str, base_key: str, other_key: str, variants_dir: Path, out_path: Path, caption_extra: str = ""):
    h0 = inclusive_hist(variants_dir, sample, base_key)
    h1 = inclusive_hist(variants_dir, sample, other_key)
    if h0 is None or h1 is None:
        print(f"SKIP {out_path}: missing histogram(s) for {sample} {base_key}/{other_key}")
        return

    v0, edges = h0
    v1, _ = h1
    centers = 0.5 * (edges[:-1] + edges[1:])

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, sharex=True, figsize=(8, 7), gridspec_kw={"height_ratios": [3, 1]}
    )
    ax_top.step(centers, v0, where="mid", label=base_key, color="black")
    ax_top.step(centers, v1, where="mid", label=other_key, color="tab:red")
    ax_top.set_yscale("log")
    ax_top.set_ylabel("Events / 10 GeV")
    ax_top.set_title(f"{sample}: {base_key} vs {other_key}")
    ax_top.legend()
    plt.setp(ax_top.get_xticklabels(), visible=False)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(v0 > 0, v1 / v0, np.nan)
    ax_bot.axhline(1.0, color="grey", linewidth=0.8, linestyle="--")
    ax_bot.step(centers, ratio, where="mid", color="tab:red")
    ax_bot.set_xlabel(r"m($\mu\mu$j) [GeV]")
    ax_bot.set_ylabel(f"{other_key}/{base_key}")
    ax_bot.set_ylim(0, max(2.0, np.nanpercentile(ratio, 99) if np.isfinite(ratio).any() else 2.0))

    if caption_extra:
        fig.text(0.5, 0.005, caption_extra, ha="center", fontsize=7, wrap=True)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"wrote {out_path}")


def dimuon_low_mass_overlay(comparison: dict, out_path: Path):
    """Required plot 5: data dimuon mass, 0-200 GeV (left) and a 0-10 GeV
    zoom (right), V0 vs V1 overlaid -- built from the per-job dimuon-mass
    histograms (run_m0m1j0_variants_on_file.py's
    low_mass_dimuon_diagnostic), summed across all jobs at merge time
    (merge_variants.load_per_variant_diagnostics). Same diagnostic
    population as the low-mass fraction numbers (>=2mu, >=1 jet after this
    variant's own cleaning)."""
    v0 = comparison["data"]["V0_baseline"]["diagnostics"]
    v1 = comparison["data"]["V1_no_muon_iso"]["diagnostics"]

    fig, (ax_full, ax_zoom) = plt.subplots(1, 2, figsize=(12, 5))
    for ax, counts_key, edges_key, title in (
        (ax_full, "dimuon_mass_hist_full_counts", "dimuon_mass_hist_full_edges", "0-200 GeV"),
        (ax_zoom, "dimuon_mass_hist_zoom_counts", "dimuon_mass_hist_zoom_edges", "0-10 GeV zoom"),
    ):
        edges = np.array(v0[edges_key])
        centers = 0.5 * (edges[:-1] + edges[1:])
        ax.step(centers, v0[counts_key], where="mid", label="V0_baseline", color="black")
        ax.step(centers, v1[counts_key], where="mid", label="V1_no_muon_iso", color="tab:red")
        ax.set_yscale("log")
        ax.set_xlabel(r"m($\mu\mu$) [GeV]")
        ax.set_ylabel("Events / bin")
        ax.set_title(f"data: dimuon mass, {title}")
        ax.legend()
    fig.suptitle("Effect of the muon isolation cut on collimated low-mass dimuon pairs")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"wrote {out_path}")


def shape_comparison(variants_dir: Path, out_path: Path):
    h_data = inclusive_hist(variants_dir, "data", "V0_baseline")
    h_ttbar = inclusive_hist(variants_dir, "ttbar", "V0_baseline")
    if h_data is None or h_ttbar is None:
        print(f"SKIP {out_path}: missing V0 inclusive histogram for data or ttbar")
        return
    v_data, edges = h_data
    v_ttbar, _ = h_ttbar
    centers = 0.5 * (edges[:-1] + edges[1:])

    v_data_norm = v_data / v_data.sum() if v_data.sum() > 0 else v_data
    v_ttbar_norm = v_ttbar / v_ttbar.sum() if v_ttbar.sum() > 0 else v_ttbar

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.step(centers, v_data_norm, where="mid", label="data (V0)", color="black")
    ax.step(centers, v_ttbar_norm, where="mid", label="ttbar (V0)", color="tab:blue")
    ax.set_yscale("log")
    ax.set_xlabel(r"m($\mu\mu$j) [GeV]")
    ax.set_ylabel("Events / 10 GeV (normalised to unit area)")
    ax.set_title("shapes only, not a background prediction")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"wrote {out_path}")


def ttbar_luminosity_scaled_plot(variants_dir: Path, out_path: Path) -> dict:
    """Optional extra (task's own explicit request): data V0 vs ttbar V0
    scaled to the data's luminosity. scale = sigma*L/N_generated. Returns
    the numbers used, for embedding in the JSON."""
    h_data = inclusive_hist(variants_dir, "data", "V0_baseline")
    h_ttbar = inclusive_hist(variants_dir, "ttbar", "V0_baseline")
    scale = (TTBAR_XSEC_PB * DOUBLEMUON_LUMI_FB_INV * 1000.0) / TTBAR_N_GENERATED  # pb * fb^-1 -> pb * pb^-1 (x1000)
    numbers = {
        "sigma_ttbar_pb": TTBAR_XSEC_PB,
        "luminosity_fb_inv": DOUBLEMUON_LUMI_FB_INV,
        "n_generated_ttbar": TTBAR_N_GENERATED,
        "scale_factor": scale,
        "caveat": (
            "cross section not published on the CERN Open Data portal -- standard value used; "
            "DoubleMuon luminosity not independently verified (established for DoubleEG); "
            "~10% uncertainty; no pileup reweighting or scale factors applied"
        ),
    }
    if h_data is None or h_ttbar is None:
        print(f"SKIP {out_path}: missing V0 inclusive histogram for data or ttbar")
        return numbers

    v_data, edges = h_data
    v_ttbar, _ = h_ttbar
    v_ttbar_scaled = v_ttbar * scale
    centers = 0.5 * (edges[:-1] + edges[1:])

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.step(centers, v_data, where="mid", label="data (V0)", color="black")
    ax.step(centers, v_ttbar_scaled, where="mid", label=f"ttbar (V0) x {scale:.5f}", color="tab:blue")
    ax.set_yscale("log")
    ax.set_xlabel(r"m($\mu\mu$j) [GeV]")
    ax.set_ylabel("Events / 10 GeV")
    ax.set_title("OPTIONAL / SCOPE-LIMITED -- see caption")
    fig.text(
        0.5, 0.005,
        "cross section not published on the CERN Open Data portal -- standard value used; DoubleMuon\n"
        "luminosity not independently verified (established for DoubleEG); ~10% uncertainty; no pileup\n"
        "reweighting or scale factors applied",
        ha="center", fontsize=7, wrap=True,
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"wrote {out_path}")
    return numbers


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants-dir", required=True)
    args = p.parse_args()

    variants_dir = Path(args.variants_dir)
    plots_dir = variants_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    data_summary = json.loads((variants_dir / "merge_variants_data_summary.json").read_text())
    ttbar_summary = json.loads((variants_dir / "merge_variants_ttbar_summary.json").read_text())

    if not data_summary.get("complete") or not ttbar_summary.get("complete"):
        print("One or both merge summaries are not marked complete -- refusing to build the final comparison JSON/plots.")
        sys.exit(1)

    comparison = {
        "data": data_summary["per_variant"],
        "ttbar": ttbar_summary["per_variant"],
        "note": "Diagnostics (low-mass dimuon fractions, V2 jet-muon overlap) are DATA-ONLY per the task's own spec.",
    }

    # --- Required plots 1-3: data V0 vs V1/V2/V3 ---
    overlay_with_ratio("data", "V0_baseline", "V1_no_muon_iso", variants_dir, plots_dir / "data_V0_vs_V1.png")
    overlay_with_ratio("data", "V0_baseline", "V2_no_jet_lepton_cleaning", variants_dir, plots_dir / "data_V0_vs_V2.png")
    overlay_with_ratio(
        "data", "V0_baseline", "V3_single_muon_trigger", variants_dir, plots_dir / "data_V0_vs_V3.png",
        caption_extra=variants.VARIANT_DESCRIPTIONS["V3_single_muon_trigger"],
    )

    # --- Required plot 4: same three for ttbar ---
    overlay_with_ratio("ttbar", "V0_baseline", "V1_no_muon_iso", variants_dir, plots_dir / "ttbar_V0_vs_V1.png")
    overlay_with_ratio("ttbar", "V0_baseline", "V2_no_jet_lepton_cleaning", variants_dir, plots_dir / "ttbar_V0_vs_V2.png")
    overlay_with_ratio(
        "ttbar", "V0_baseline", "V3_single_muon_trigger", variants_dir, plots_dir / "ttbar_V0_vs_V3.png",
        caption_extra=variants.VARIANT_DESCRIPTIONS["V3_single_muon_trigger"],
    )

    # --- Required plot 5: dimuon mass low-mass diagnostic, V0 vs V1 ---
    dimuon_low_mass_overlay(comparison, plots_dir / "data_dimuon_lowmass_V0_vs_V1.png")

    # --- Required plot 6: data V0 vs ttbar V0, shapes only ---
    shape_comparison(variants_dir, plots_dir / "data_vs_ttbar_V0_shapes.png")

    # --- Optional extra: luminosity-scaled ttbar overlay ---
    ttbar_scale_numbers = ttbar_luminosity_scaled_plot(variants_dir, plots_dir / "OPTIONAL_data_vs_ttbar_lumi_scaled.png")
    comparison["optional_ttbar_luminosity_scaling"] = ttbar_scale_numbers

    out_json = variants_dir / "comparison_summary.json"
    out_json.write_text(json.dumps(comparison, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out_json}")


if __name__ == "__main__":
    main()
