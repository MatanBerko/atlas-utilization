#!/usr/bin/env python3
"""
Stage 3 of the H -> gamma gamma rediscovery exercise: resolution-matched
binning, restricted mass window, and analysis-grade photon cuts, on top of
Stage 2's full-scale (133/133 files) output.

Reads Stage 2's ALREADY-PARSED photon collections directly (no re-fetch, no
re-parse) and applies, purely as a post-hoc filter on saved data:

  1. ECAL barrel/endcap transition exclusion: reject photons with
     1.4442 < |eta| < 1.566. Confirmed (not assumed) against the CMS
     Collaboration's own photon-reconstruction performance paper (JINST,
     arXiv:1502.02702): "...excluding the last two crystals at each end of
     the barrel (|eta|<1.4442) ... this area is removed from the fiducial
     region by excluding the first ring of trigger towers of the endcaps
     (|eta|>1.566)." This is a fixed ECAL crystal/trigger-tower geometry
     boundary, not a per-production calibration, so it applies unchanged to
     this UL2016 NanoAODv9 production. A live cross-check against a fresh
     NanoAOD file (looking for a supercluster-eta flag like Photon_isScEtaEB)
     was attempted but blocked by a genuine network outage on this machine
     (raw TCP to eospublic.cern.ch:1094 times out) -- reported here plainly,
     not silently skipped. Applied directly to the NanoAOD Photon_eta branch:
     photons travel in straight lines from the primary vertex, so there is no
     track-vs-supercluster eta ambiguity the way there can be for electrons.

  2. cutBased >= 2 (medium) as the PRIMARY ID, with >=1 (loose, Stage 2's own
     value) and >=3 (tight) computed alongside for comparison. Since Stage 2's
     parsed output already only contains photons with cutBased>=1, loose is
     already exactly what's on disk; medium/tight are strict subsets of it,
     so no data is missing for any of the three variants.

  3. Asymmetric pT: leading photon pT > m_gammagamma/3, subleading pT >
     m_gammagamma/4 -- applied at the PAIR level, in this script, after the
     mass is computed from the 2 leading surviving photons at each cut stage.
     This is deliberately NOT forced into services/calculations/physics_calcs.py's
     per-object kinematic-cut machinery (which cannot express a cut that
     depends on the pair's own computed mass) -- see build_cutflow() below for
     exactly where this happens.

Cut-flow order per variant: Stage 2 candidates -> ECAL gap -> ID threshold ->
asymmetric pT -> final (100-180 GeV window, what actually feeds the
histograms).

Usage (inside the pipeline's Docker image, no XRootD needed):
    python scripts/higgs_diphoton_stage3_report.py \
        --stage2-run-dir output/cms_higgs_diphoton_stage2_20260907_201708 \
        --out-dir reports/higgs_diphoton_stage3_resolution
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

# ECAL barrel/endcap transition, confirmed against arXiv:1502.02702 (see
# module docstring). Fixed detector geometry, not production-specific.
ECAL_GAP_LOW, ECAL_GAP_HIGH = 1.4442, 1.566

ID_VARIANTS = {"loose": 1, "medium": 2, "tight": 3}
PRIMARY_VARIANT = "medium"

MASS_WINDOW = (100.0, 180.0)
BUMPNET_MIN_BINS = 30
BUMPNET_MIN_ENTRIES = 100
HIGGS_MASS_GEV = 125.0

BUMPNET_NAME = "mass_g0g1_cat_0ex_0mx_0jx_2gx_0tx_0bx"


def load_photons(run_dir: Path):
    """Read Stage 2's parsed chunks; return per-event jagged awkward arrays
    (pt, eta, phi, mass, cutBased) plus a flat source_record array aligned to
    events (used only for optional per-record bookkeeping)."""
    import awkward as ak
    import uproot

    parsed = sorted((run_dir / "parsed_data").glob("*.root"))
    if not parsed:
        raise FileNotFoundError(f"no parsed .root chunks in {run_dir/'parsed_data'}")

    pt_parts, eta_parts, phi_parts, mass_parts, cb_parts, src_parts = (
        [], [], [], [], [], []
    )
    n_events = 0
    file_rows = []
    for chunk in parsed:
        arr = uproot.open(chunk)["events"].arrays(
            ["Photons_pt", "Photons_eta", "Photons_phi", "Photons_mass",
             "Photons_cutBased", "source_record"],
            library="ak",
        )
        n_events += len(arr)
        file_rows.append({"file": chunk.name, "events": len(arr)})
        pt_parts.append(arr["Photons_pt"])
        eta_parts.append(arr["Photons_eta"])
        phi_parts.append(arr["Photons_phi"])
        mass_parts.append(arr["Photons_mass"])
        cb_parts.append(arr["Photons_cutBased"])
        src_parts.append(arr["source_record"])

    pt = ak.concatenate(pt_parts)
    eta = ak.concatenate(eta_parts)
    phi = ak.concatenate(phi_parts)
    mass = ak.concatenate(mass_parts)
    cb = ak.concatenate(cb_parts)
    src = ak.concatenate(src_parts)
    return pt, eta, phi, mass, cb, src, n_events, file_rows


def leading_pair_mass(pt, eta, phi, mass, mask):
    """Given a per-photon boolean mask, keep only masked photons, take the 2
    leading (by pt) per event, and compute the diphoton invariant mass for
    events with >=2 survivors. Returns (has_pair, lead_pt, sub_pt, pair_mass)
    -- all flat numpy arrays aligned to the FULL event list (NaN/False where
    an event has <2 surviving photons)."""
    import awkward as ak
    import vector

    vector.register_awkward()

    pt_m, eta_m, phi_m, mass_m = pt[mask], eta[mask], phi[mask], mass[mask]
    order = ak.argsort(pt_m, axis=1, ascending=False)
    pt_m, eta_m, phi_m, mass_m = pt_m[order], eta_m[order], phi_m[order], mass_m[order]

    n_events = len(pt)
    has_pair = np.asarray(ak.num(pt_m, axis=1) >= 2)

    pt2 = pt_m[has_pair][:, :2]
    eta2 = eta_m[has_pair][:, :2]
    phi2 = phi_m[has_pair][:, :2]
    mass2 = mass_m[has_pair][:, :2]

    vecs = vector.zip({"pt": pt2, "eta": eta2, "phi": phi2, "mass": mass2})
    diphoton = vecs[:, 0] + vecs[:, 1]
    pair_mass_sub = np.asarray(ak.to_numpy(diphoton.mass), dtype=float)
    lead_pt_sub = np.asarray(ak.to_numpy(pt2[:, 0]), dtype=float)
    sub_pt_sub = np.asarray(ak.to_numpy(pt2[:, 1]), dtype=float)

    lead_pt = np.full(n_events, np.nan)
    sub_pt = np.full(n_events, np.nan)
    pair_mass = np.full(n_events, np.nan)
    lead_pt[has_pair] = lead_pt_sub
    sub_pt[has_pair] = sub_pt_sub
    pair_mass[has_pair] = pair_mass_sub
    return has_pair, lead_pt, sub_pt, pair_mass


def build_cutflow(pt, eta, phi, mass, cb, n_events: int) -> dict:
    """Per-variant cut-flow: Stage 2 candidates -> ECAL gap -> ID -> asymmetric
    pT -> final (100-180 GeV). Returns counts and, for the primary variant,
    the final pair masses for histogramming."""
    abseta = abs(eta)
    gap_reject = (abseta > ECAL_GAP_LOW) & (abseta < ECAL_GAP_HIGH)
    gap_keep_mask = ~gap_reject

    # "After ECAL gap" alone (loose ID, i.e. Stage 2's own data, unchanged):
    has_pair_gap, _, _, mass_gap = leading_pair_mass(pt, eta, phi, mass, gap_keep_mask)
    n_after_gap = int(has_pair_gap.sum())

    results = {"n_stage2_candidates": n_events, "n_after_ecal_gap": n_after_gap}
    variant_masses = {}

    for name, threshold in ID_VARIANTS.items():
        id_mask = gap_keep_mask & (cb >= threshold)
        has_pair_id, lead_pt, sub_pt, pair_mass = leading_pair_mass(
            pt, eta, phi, mass, id_mask
        )
        n_after_id = int(has_pair_id.sum())

        # Asymmetric pT (PAIR-level cut, computed here from pair_mass -- see
        # module docstring for why this cannot live in physics_calcs.py's
        # per-object kinematic-cut machinery).
        asym_pass = (
            has_pair_id
            & (lead_pt > pair_mass / 3.0)
            & (sub_pt > pair_mass / 4.0)
        )
        n_after_asym = int(np.nansum(asym_pass))

        in_window = asym_pass & (pair_mass >= MASS_WINDOW[0]) & (pair_mass <= MASS_WINDOW[1])
        n_final = int(np.nansum(in_window))

        results[name] = {
            "cutbased_threshold": threshold,
            "n_after_ecal_gap": n_after_gap,  # same for all variants
            "n_after_id": n_after_id,
            "n_after_asymmetric_pt": n_after_asym,
            "n_final_100_180_gev": n_final,
        }
        variant_masses[name] = pair_mass[in_window]

    return results, variant_masses


def build_hist(masses: np.ndarray, bin_width: float):
    lo, hi = MASS_WINDOW
    nbins = int(round((hi - lo) / bin_width))
    edges = np.linspace(lo, hi, nbins + 1)
    counts, _ = np.histogram(masses, bins=edges)
    return edges, counts, nbins


def write_bumpnet_root(edges, counts, bin_width: float, out_root: Path) -> str:
    import uproot

    out_root.parent.mkdir(parents=True, exist_ok=True)
    name = f"{BUMPNET_NAME}_width_{bin_width}"
    with uproot.recreate(str(out_root)) as f:
        f[name] = (counts, edges)
    return name


def plot_cutflow(results: dict, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    stages = ["Stage 2\ncandidates", "after\nECAL gap", "after\nID",
              "after\nasym. pT", "final\n(100-180 GeV)"]
    colors = {"loose": "#4477aa", "medium": "#cc3311", "tight": "#228833"}

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(stages))
    w = 0.25
    for i, name in enumerate(("loose", "medium", "tight")):
        r = results[name]
        vals = [
            results["n_stage2_candidates"],
            results["n_after_ecal_gap"],
            r["n_after_id"],
            r["n_after_asymmetric_pt"],
            r["n_final_100_180_gev"],
        ]
        ax.bar(x + (i - 1) * w, vals, w, color=colors[name],
               label=f"{name} (cutBased>={ID_VARIANTS[name]})")
        for xi, v in zip(x, vals):
            ax.text(xi + (i - 1) * w, v, f"{v:,}", ha="center", va="bottom",
                     fontsize=6.5, rotation=90)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=9)
    ax.set_ylabel("diphoton candidates")
    ax.set_title(
        "H -> gamma gamma  Stage 3 cut-flow  (full scale, 133/133 files)\n"
        "ECAL gap: reject 1.4442<|eta|<1.566  |  asym. pT: lead>m/3, sublead>m/4  |  "
        "medium (cutBased>=2) is the PRIMARY selection",
        fontsize=9.5)
    ax.legend(fontsize=9)
    ax.set_ylim(bottom=max(1, min(
        results[v]["n_final_100_180_gev"] for v in ("loose", "medium", "tight")
    ) * 0.5))
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def plot_bumpnet_style(edges, counts, bin_width: float, out_png: Path) -> None:
    """Figure-15-style 2-panel plot: (top) data + smooth background fit,
    (middle) residual counts. NO significance/pull/p-value panel or number --
    illustrative only, stated explicitly on the plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    centers = 0.5 * (edges[:-1] + edges[1:])
    n_total = int(counts.sum())

    # 4th-order polynomial background fit (matches the ATLAS convention the
    # BumpNet paper itself references for this exact figure), weighted by
    # Poisson errors (sqrt(N), floor 1 to avoid div-by-zero on empty bins).
    sigma = np.sqrt(np.clip(counts, 1, None))
    coeffs = np.polyfit(centers, counts, deg=4, w=1.0 / sigma)
    fit_curve = np.polyval(coeffs, centers)
    residual = counts - fit_curve

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9, 8), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
    )

    ax1.errorbar(centers, counts, yerr=np.sqrt(counts), fmt="o", ms=3.5,
                 color="#222222", label=f"data ({n_total:,} entries)")
    ax1.plot(centers, fit_curve, color="#cc3311", lw=1.6,
              label="4th-order polynomial background fit (illustrative)")
    ax1.axvline(HIGGS_MASS_GEV, color="#4477aa", ls="--", lw=1.1,
                 label=f"m = {HIGGS_MASS_GEV:.0f} GeV")
    ax1.set_ylabel(f"candidates / {bin_width:.0f} GeV")
    ax1.set_title(
        f"CMS Open Data DoubleEG, full scale - diphoton mass, {n_total:,} "
        f"entries, {len(counts)} x {bin_width:.0f} GeV bins, medium ID "
        "(cutBased>=2) + ECAL gap + asymmetric pT\n"
        "Background fit is ILLUSTRATIVE ONLY - no significance, p-value, or "
        "sigma is computed here. That determination is BumpNet's job.",
        fontsize=8.7)
    ax1.legend(fontsize=8)

    ax2.axhline(0, color="#888888", lw=1.0)
    ax2.bar(centers, residual, width=bin_width * 0.9, color="#4477aa")
    ax2.axvline(HIGGS_MASS_GEV, color="#4477aa", ls="--", lw=1.1)
    ax2.set_xlabel("diphoton invariant mass  [GeV]")
    ax2.set_ylabel("data - fit\n(counts)")
    ax2.text(
        0.5, -0.38,
        "Residual panel shows raw (data - fit) counts only - NOT a pull, "
        "significance, or sigma value. No third (significance) panel is "
        "included, by design: determining significance is BumpNet's job, "
        "not this script's.",
        transform=ax2.transAxes, ha="center", va="top", fontsize=7.3,
        style="italic", wrap=True,
    )

    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return coeffs.tolist()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage2-run-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    out = args.out_dir
    (out / "plots").mkdir(parents=True, exist_ok=True)
    (out / "histograms").mkdir(parents=True, exist_ok=True)

    pt, eta, phi, mass, cb, src, n_events, file_rows = load_photons(args.stage2_run_dir)
    print(f"loaded {n_events:,} Stage 2 candidate events from {len(file_rows)} chunk(s)")

    results, variant_masses = build_cutflow(pt, eta, phi, mass, cb, n_events)
    plot_cutflow(results, out / "plots" / "diphoton_stage3_cutflow.png")

    primary_masses = variant_masses[PRIMARY_VARIANT]

    edges2, counts2, nbins2 = build_hist(primary_masses, bin_width=2.0)
    edges1, counts1, nbins1 = build_hist(primary_masses, bin_width=1.0)

    hist2_name = write_bumpnet_root(
        edges2, counts2, 2.0, out / "histograms" / "diphoton_stage3_2gev_bumpnet.root"
    )
    hist1_name = write_bumpnet_root(
        edges1, counts1, 1.0, out / "histograms" / "diphoton_stage3_1gev_bumpnet.root"
    )

    fit_coeffs = plot_bumpnet_style(
        edges2, counts2, 2.0, out / "plots" / "diphoton_stage3_2gev_bumpnet_style.png"
    )

    def bar(n, nb):
        return {
            "n_bins": nb, "entries": int(n.sum()),
            "n_nonempty_bins": int((n > 0).sum()),
            "meets_bin_bar": nb > BUMPNET_MIN_BINS,
            "meets_entry_bar": int(n.sum()) >= BUMPNET_MIN_ENTRIES,
        }

    stats = {
        "stage2_run_dir": str(args.stage2_run_dir),
        "n_stage2_candidates": n_events,
        "ecal_gap_boundaries": {
            "low": ECAL_GAP_LOW, "high": ECAL_GAP_HIGH,
            "source": "CMS Collaboration photon-reconstruction performance "
                       "paper, arXiv:1502.02702 (JINST) - fixed ECAL crystal/"
                       "trigger-tower geometry, not production-specific. Live "
                       "NanoAOD cross-check attempted, blocked by a network "
                       "outage (TCP to eospublic.cern.ch:1094 timed out) -- "
                       "see report for detail.",
        },
        "id_variants": ID_VARIANTS,
        "primary_variant": PRIMARY_VARIANT,
        "mass_window_gev": list(MASS_WINDOW),
        "cutflow": results,
        "histogram_2gev": {
            "root_file": str(out / "histograms" / "diphoton_stage3_2gev_bumpnet.root"),
            "hist_name": hist2_name,
            "bin_width_gev": 2.0,
            **bar(counts2, nbins2),
        },
        "histogram_1gev": {
            "root_file": str(out / "histograms" / "diphoton_stage3_1gev_bumpnet.root"),
            "hist_name": hist1_name,
            "bin_width_gev": 1.0,
            **bar(counts1, nbins1),
        },
        "background_fit": {
            "form": "4th-order polynomial (numpy.polyfit, deg=4, weighted by "
                    "Poisson sqrt(N) per bin)",
            "why": "matches the ATLAS convention the BumpNet paper's own "
                   "H->gamma gamma figure (Fig. 15) is based on",
            "coefficients_highest_degree_first": fit_coeffs,
            "caveat": "ILLUSTRATIVE ONLY -- no significance, p-value, or "
                      "sigma computed or implied anywhere in this script.",
        },
    }
    (out / "diphoton_stage3_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
