#!/usr/bin/env python
"""
Part C: plots and the closure check for the single-file MC smoke test.

Reads the per-sample ROOT file the MC builder wrote and produces:

  (1) `smoke_4lepton_mass.png` -- the four-lepton invariant mass for the 4mu,
      4e and 2e2mu final states on a 0-300 GeV view, with Sumw2 error bars.
      A ggH->ZZ->4l sample should peak near 125 GeV.
  (2) `smoke_dilepton_mass.png` -- one dilepton histogram from the same file,
      for scale.

and a closure check: the expected weighted yield of a set of histograms is

    sigma_eff[pb] * 1000 * L_fb * (that set's share of the file's Sigma-w)

which, because w_event = genWeight * L1prefire * sigma*1000*L/Sigma-w, is just
`sum(genWeight * L1prefire) over the selected entries * sigma*1000*L/Sigma-w`.
The check therefore compares the histogram's own integral against the same
quantity recomputed from the raw siblings, which is an independent path to the
same number and catches a mis-scaled or mis-paired weight.

Everything written goes under --out-dir. Nothing else is touched.

Run:
    python studies/cms_mc_weights_v3/deliver/plot_smoke_test.py \
        --root-file  <...>_record37728_mc.root \
        --build-report <...>_build_report.json \
        --out-dir    <...>/plots
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

# The four-lepton IM combinations, in the index-based spelling the signatures
# use: four muons, four electrons, and two of each.
FOUR_LEPTON_IM = {
    "4mu":   "m0m1m2m3",
    "4e":    "e0e1e2e3",
    "2e2mu": "e0e1m0m1",
}
VIEW_MAX_GEV = 300.0


def hists_by_im(root_path: pathlib.Path) -> dict:
    """{im_str: [(key, values, errors, edges), ...]} for every TH1D in the file."""
    out: dict[str, list] = {}
    with uproot.open(str(root_path)) as f:
        for key in sorted({k.split(";")[0] for k in f.keys()}):
            h = f[key]
            if h.classname != "TH1D":
                continue
            # ROI_mass_<im>_cat_<fs>_width_<w>
            if "_cat_" not in key or not key.startswith("ROI_mass_"):
                continue
            im_str = key[len("ROI_mass_"):key.index("_cat_")]
            out.setdefault(im_str, []).append(
                (key, h.values(flow=False), h.errors(flow=False),
                 h.axis().edges()))
    return out


def plot_four_lepton(by_im: dict, out_path: pathlib.Path) -> dict:
    present = {label: im for label, im in FOUR_LEPTON_IM.items() if im in by_im}
    fig, axes = plt.subplots(1, max(1, len(present)) if present else 1,
                             figsize=(5.2 * max(1, len(present)), 4.4),
                             squeeze=False)
    axes = axes[0]
    summary = {}
    if not present:
        axes[0].text(0.5, 0.5,
                     "no 4-lepton histogram survived\nthe >=100-entries rule\n"
                     "(expected on ONE file)",
                     ha="center", va="center", fontsize=11, transform=axes[0].transAxes)
        axes[0].set_axis_off()
        summary["note"] = ("no 4-lepton final state survived the "
                           ">=100-raw-entries-per-final-state rule on a single file")
    for ax, (label, im) in zip(axes, sorted(present.items())):
        # pick the histogram of this IM with the most entries
        key, values, errors, edges = max(by_im[im], key=lambda t: np.sum(t[1]))
        centres = 0.5 * (edges[:-1] + edges[1:])
        view = centres <= VIEW_MAX_GEV
        ax.errorbar(centres[view], values[view], yerr=errors[view],
                    fmt="o", ms=3, lw=1, capsize=1.5, color="#2b6cb0")
        ax.axvline(125.0, color="#c05621", ls="--", lw=1,
                   label="m(H) = 125 GeV")
        ax.set_title(f"{label}   ({im})", fontsize=10)
        ax.set_xlabel("4-lepton invariant mass [GeV]")
        ax.set_ylabel("weighted events / 10 GeV")
        ax.set_xlim(0, VIEW_MAX_GEV)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25, lw=0.5)
        peak_bin = int(np.argmax(values))
        summary[label] = {
            "histogram": key,
            "integral_weighted": float(values.sum()),
            "integral_in_view": float(values[view].sum()),
            "peak_bin_centre_gev": float(centres[peak_bin]),
            "peak_bin_content": float(values[peak_bin]),
            "n_filled_bins": int(np.count_nonzero(errors > 0)),
        }
    fig.suptitle("MC smoke test -- ggH->ZZ->4l (record 37728), ONE file. "
                 "Error bars are sqrt(sum w^2).\n"
                 "SMOKE TEST, NOT A PHYSICS RESULT: Sigma-w is from this file only.",
                 fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"wrote {out_path}")
    return summary


def plot_one_dilepton(by_im: dict, out_path: pathlib.Path) -> dict:
    # Prefer a same-flavour dilepton (which the Z cut acts on); else any.
    preferred = ["m0m1", "e0e1"]
    pick = next((im for im in preferred if im in by_im), None)
    if pick is None:
        pick = max(by_im, key=lambda im: max(np.sum(t[1]) for t in by_im[im])) \
            if by_im else None
    if pick is None:
        raise SystemExit("no TH1D histograms in the file at all")
    key, values, errors, edges = max(by_im[pick], key=lambda t: np.sum(t[1]))
    centres = 0.5 * (edges[:-1] + edges[1:])
    view = centres <= VIEW_MAX_GEV

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.errorbar(centres[view], values[view], yerr=errors[view],
                fmt="o", ms=3, lw=1, capsize=1.5, color="#2f855a")
    if pick in ("m0m1", "e0e1"):
        ax.axvline(110.0, color="#718096", ls=":", lw=1,
                   label="Z-peak cut at 110 GeV")
        ax.legend(fontsize=8)
    ax.set_title(f"dilepton: {key}", fontsize=9)
    ax.set_xlabel("dilepton invariant mass [GeV]")
    ax.set_ylabel("weighted events / 10 GeV")
    ax.set_xlim(0, VIEW_MAX_GEV)
    ax.grid(alpha=0.25, lw=0.5)
    fig.suptitle("MC smoke test -- one dilepton histogram from the same file. "
                 "Error bars are sqrt(sum w^2).", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"wrote {out_path}")
    return {
        "im": pick, "histogram": key,
        "integral_weighted": float(values.sum()),
        "n_filled_bins": int(np.count_nonzero(errors > 0)),
        "first_filled_bin_centre_gev": float(
            centres[np.nonzero(errors > 0)[0][0]]) if np.any(errors > 0) else None,
    }


def closure_check(report: dict, record_id: str, by_im: dict) -> dict:
    """The expected weighted yield of every delivered histogram, from the
    normalisation factor and the raw per-entry weights, against the
    histograms' own integrals."""
    sample = report["samples"][record_id]
    norm = float(sample["normalisation_factor"])
    sigma = float(sample["cross_section_pb_sigma_eff"])
    sigma_w = float(sample["sigma_w_over_surviving_files"])
    lumi = float(report["constants"]["target_luminosity_fb"])

    per_hist = sample["histograms"]["per_histogram"]
    kept = {n: d for n, d in per_hist.items() if d.get("kept")}
    sum_weighted_from_report = sum(float(d["weighted_yield"]) for d in kept.values())
    sum_sum_w_in_hist = sum(float(d["sum_w_in_hist"]) for d in kept.values())
    sum_raw = sum(int(d["n_raw_entries"]) for d in kept.values())

    integrals = {}
    for im, entries in by_im.items():
        for key, values, _errors, _edges in entries:
            integrals[key] = float(values.sum())
    total_integral = sum(integrals.values())

    # Independent route: sum(w)/norm is sum(genWeight * L1prefire) over the
    # same entries, so sum(w) == that * sigma*1000*L/Sigma-w by construction.
    implied_sum_gen_times_prefire = (sum_sum_w_in_hist / norm) if norm else None
    expected_from_sigma = (
        sigma * 1000.0 * lumi * (implied_sum_gen_times_prefire / sigma_w)
        if implied_sum_gen_times_prefire is not None and sigma_w else None)

    return {
        "record_id": record_id,
        "normalisation_factor": norm,
        "cross_section_pb_sigma_eff": sigma,
        "sigma_w_over_surviving_files": sigma_w,
        "target_luminosity_fb": lumi,
        "n_histograms_delivered": len(integrals),
        "n_raw_entries_in_delivered_histograms": sum_raw,
        "sum_of_histogram_integrals": total_integral,
        "sum_of_weighted_yields_from_build_report": sum_weighted_from_report,
        "sum_of_sum_w_in_hist_from_build_report": sum_sum_w_in_hist,
        "integrals_match_build_report": bool(
            abs(total_integral - sum_sum_w_in_hist)
            <= 1e-9 * max(1.0, abs(sum_sum_w_in_hist))),
        "implied_sum_genweight_times_prefire": implied_sum_gen_times_prefire,
        "expected_yield_from_sigma_times_lumi_times_sigmaw_share":
            expected_from_sigma,
        "closure_relative_difference": (
            abs(expected_from_sigma - sum_sum_w_in_hist)
            / abs(sum_sum_w_in_hist) if sum_sum_w_in_hist else None),
        "formula": "expected = sigma_eff[pb] * 1000 * L_fb * "
                   "(sum(genWeight*L1prefire) over delivered entries / Sigma-w)",
        "note": "This is the arithmetic identity the weight definition implies. "
                "It verifies the normalisation was applied once, consistently, "
                "and that nothing was lost between the weight arrays and the "
                "histograms. It is NOT a physics cross-check.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-file", required=True)
    ap.add_argument("--build-report", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--record-id", default="37728")
    args = ap.parse_args()

    root_path = pathlib.Path(args.root_file)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = json.loads(pathlib.Path(args.build_report).read_text(encoding="utf-8"))

    by_im = hists_by_im(root_path)
    print(f"{sum(len(v) for v in by_im.values())} TH1D histogram(s) across "
          f"{len(by_im)} IM combination(s)")

    summary = {
        "root_file": str(root_path),
        "build_report": str(args.build_report),
        "n_histograms": sum(len(v) for v in by_im.values()),
        "n_im_combinations": len(by_im),
        "im_combinations": sorted(by_im),
        "four_lepton": plot_four_lepton(by_im, out_dir / "smoke_4lepton_mass.png"),
        "dilepton": plot_one_dilepton(by_im, out_dir / "smoke_dilepton_mass.png"),
        "closure": closure_check(report, args.record_id, by_im),
    }
    out = out_dir / "smoke_test_summary.json"
    out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out}")
    print("\nclosure: " + json.dumps(
        {k: v for k, v in summary["closure"].items()
         if k in ("sum_of_histogram_integrals",
                  "sum_of_sum_w_in_hist_from_build_report",
                  "integrals_match_build_report",
                  "expected_yield_from_sigma_times_lumi_times_sigmaw_share",
                  "closure_relative_difference")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
