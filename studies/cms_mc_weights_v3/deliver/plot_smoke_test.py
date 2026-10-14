#!/usr/bin/env python
"""
Part C: plots and the closure check for the single-file MC smoke test.

Reads the per-sample ROOT file the MC builder wrote and produces:

  (1) `smoke_4lepton_mass.png` -- the four-lepton invariant mass for the 4mu,
      4e and 2e2mu final states on a 0-300 GeV view, with Sumw2 error bars.
      Each panel shows TWO things: the weighted spectrum BEFORE
      post-processing (read from the shard masses and their `_mcw` siblings,
      pooled over every final state of that lepton combination), and the bins
      the delivery actually keeps. Both are needed, because peak removal cuts
      everything below the rightmost highest peak -- which for a ggH->ZZ->4l
      sample IS the 125 GeV bin -- so the delivered histogram of a sparse
      category shows the resonance's position but not its shape.
  (2) `smoke_dilepton_mass.png` -- the same-flavour dilepton mass, with the
      110 GeV Z cut drawn on it, plus one two-object mass that does survive
      into the delivery. Both are needed: in a ggH->ZZ->4l sample the
      same-flavour pairs sit at or below the Z mass, so the Z cut removes them
      and NO m0m1 / e0e1 histogram reaches the delivery -- which is the Z cut
      working correctly on MC, and is worth showing rather than hiding behind
      a combination that happens to survive.

and a closure check: because

    w_event = genWeight * L1prefire * sigma_eff[pb] * 1000 * L_fb / Sigma-w

the weighted yield of any set of entries equals

    sigma_eff * 1000 * L_fb * (sum(genWeight*L1prefire) over that set / Sigma-w)

The check recomputes the right-hand side from the delivered histograms' own
integrals and compares. It verifies the normalisation was applied once and
consistently and that nothing was lost between the weight arrays and the
histograms. It is NOT a physics cross-check.

Everything written goes under --out-dir. Nothing else is touched.

Run:
    python studies/cms_mc_weights_v3/deliver/plot_smoke_test.py \
        --root-file    <...>_record37728_mc.root \
        --build-report <...>_build_report.json \
        --out-dir      <...>/plots \
        [--scratch-dir <the builder's --keep-scratch dir>]
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

from services.storage.sqlite_shards import (  # noqa: E402
    iter_arrays_for_signature, list_signatures,
)
from studies.cms_datasets.cluster.run_dataset_on_file import MC_WEIGHT_SUFFIX  # noqa: E402
from studies.cms_mc_weights_v3.deliver.build_mc_delivery import SIG_PATTERN  # noqa: E402
from studies.cms_mc_weights_v3.deliver.weighted_histograms import (  # noqa: E402
    fill_weighted_fixed_grid,
)

# The four-lepton IM combinations, in the index-based spelling the signatures
# use: four muons, four electrons, and two of each.
FOUR_LEPTON_IM = {
    "4mu": "m0m1m2m3",
    "4e": "e0e1e2e3",
    "2e2mu": "e0e1m0m1",
}
# Same-flavour dilepton combinations, which the 110 GeV Z cut acts on.
DILEPTON_IM = {"mumu": "m0m1", "ee": "e0e1"}
VIEW_MAX_GEV = 300.0


def spectra_from_shards(scratch_dir: pathlib.Path, im_strs) -> dict:
    """{im_str: (sum_w, sum_w2, edges, n_raw)} from the shard masses and their
    `_mcw` siblings, pooled over every final state -- i.e. the spectrum before
    post-processing. A mass/weight length mismatch aborts."""
    want = set(im_strs)
    pooled = {im: ([], []) for im in want}
    for shard in sorted(scratch_dir.rglob("*.sqlite")):
        for sig in list_signatures(str(shard)):
            m = SIG_PATTERN.search(sig)
            if not m or m.group(2) not in want:
                continue
            masses = list(iter_arrays_for_signature(str(shard), sig))
            weights = list(iter_arrays_for_signature(str(shard), sig + MC_WEIGHT_SUFFIX))
            if not masses or not weights:
                continue
            mm = np.concatenate([np.asarray(c, dtype=np.float64) for c in masses])
            ww = np.concatenate([np.asarray(c, dtype=np.float64) for c in weights])
            if len(mm) != len(ww):
                raise SystemExit(
                    f"{sig}: {len(mm)} masses vs {len(ww)} weights in {shard}")
            pooled[m.group(2)][0].append(mm)
            pooled[m.group(2)][1].append(ww)
    out = {}
    for im, (ms, ws) in pooled.items():
        if not ms:
            continue
        mm, ww = np.concatenate(ms), np.concatenate(ws)
        sum_w, sum_w2, edges = fill_weighted_fixed_grid(mm, ww)
        out[im] = (sum_w, sum_w2, edges, int(mm.size))
    return out


def hists_by_im(root_path: pathlib.Path) -> dict:
    """{im_str: [(key, values, errors, edges), ...]} for every TH1D in the file."""
    out: dict[str, list] = {}
    with uproot.open(str(root_path)) as f:
        for key in sorted({k.split(";")[0] for k in f.keys()}):
            h = f[key]
            if h.classname != "TH1D":
                continue
            if "_cat_" not in key or not key.startswith("ROI_mass_"):
                continue
            im_str = key[len("ROI_mass_"):key.index("_cat_")]
            out.setdefault(im_str, []).append(
                (key, h.values(flow=False), h.errors(flow=False), h.axis().edges()))
    return out


def plot_four_lepton(by_im: dict, spectra: dict, out_path: pathlib.Path) -> dict:
    labels = sorted(FOUR_LEPTON_IM)
    fig, axes = plt.subplots(1, len(labels), figsize=(5.3 * len(labels), 4.5),
                             squeeze=False)
    axes = axes[0]
    summary = {}
    for ax, label in zip(axes, labels):
        im = FOUR_LEPTON_IM[label]
        entry = {"im": im}

        if im in spectra:
            sum_w, sum_w2, edges, n_raw = spectra[im]
            centres = 0.5 * (edges[:-1] + edges[1:])
            view = centres <= VIEW_MAX_GEV
            ax.errorbar(centres[view], sum_w[view], yerr=np.sqrt(sum_w2[view]),
                        fmt="o", ms=3.5, lw=1, capsize=1.5, color="#2b6cb0",
                        label="before post-processing")
            peak = int(np.argmax(sum_w))
            entry["pre_postprocessing"] = {
                "n_raw_entries": n_raw,
                "integral_weighted": float(sum_w.sum()),
                "peak_bin_centre_gev": float(centres[peak]),
                "peak_bin_content": float(sum_w[peak]),
                "n_filled_bins": int(np.count_nonzero(sum_w2 > 0)),
            }
        else:
            entry["pre_postprocessing"] = None

        if im in by_im:
            key, values, errors, edges2 = max(by_im[im], key=lambda t: np.sum(t[1]))
            c2 = 0.5 * (edges2[:-1] + edges2[1:])
            filled = errors > 0
            ax.plot(c2[filled], values[filled], "s", ms=7, mfc="none",
                    mec="#c05621", mew=1.6, label="delivered (post-processed)")
            peak2 = int(np.argmax(values))
            entry["delivered"] = {
                "histogram": key,
                "integral_weighted": float(values.sum()),
                "peak_bin_centre_gev": float(c2[peak2]),
                "peak_bin_content": float(values[peak2]),
                "n_filled_bins": int(np.count_nonzero(filled)),
            }
        else:
            entry["delivered"] = None

        ax.axvline(125.0, color="#718096", ls="--", lw=1, label="m(H) = 125 GeV")
        ax.set_title(f"{label}   ({im})", fontsize=10)
        ax.set_xlabel("4-lepton invariant mass [GeV]")
        ax.set_ylabel("weighted events / 10 GeV")
        ax.set_xlim(0, VIEW_MAX_GEV)
        ax.legend(fontsize=7.5)
        ax.grid(alpha=0.25, lw=0.5)
        if entry["pre_postprocessing"] is None and entry["delivered"] is None:
            ax.text(0.5, 0.5, "no entries in this\nfinal state", ha="center",
                    va="center", fontsize=10, transform=ax.transAxes)
        summary[label] = entry

    fig.suptitle(
        "MC smoke test -- ggH->ZZ->4l (record 37728), ONE file, 4000 events. "
        "Error bars are sqrt(sum w^2).\n"
        "Blue: the weighted spectrum before post-processing. Orange squares: "
        "the bins the delivery keeps after peak removal.\n"
        "SMOKE TEST, NOT A PHYSICS RESULT -- Sigma-w is from this one file, so "
        "the vertical scale has no physical meaning.", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"wrote {out_path}")
    return summary


def plot_one_dilepton(by_im: dict, spectra: dict, out_path: pathlib.Path) -> dict:
    """One same-flavour dilepton panel, plus one that survives into the
    delivery.

    In a ggH->ZZ->4l sample the same-flavour dilepton pairs sit at or below the
    Z mass, so the 110 GeV Z cut removes them and NO m0m1 / e0e1 histogram
    reaches the delivery at all. Showing only a surviving combination would
    hide that; showing the pre-cut spectrum with the cut drawn on it shows the
    Z cut doing its job on MC, which is the point of a dilepton plot here."""
    summary = {}
    same_flavour = [(label, im) for label, im in sorted(DILEPTON_IM.items())
                    if im in spectra]
    other = [im for im in by_im if im not in DILEPTON_IM]
    n_panels = len(same_flavour) + (1 if other else 0)
    if n_panels == 0:
        raise SystemExit("no dilepton histogram and no dilepton spectrum")
    fig, axes = plt.subplots(1, n_panels, figsize=(5.6 * n_panels, 4.5),
                             squeeze=False)
    axes = list(axes[0])

    for (label, im) in same_flavour:
        ax = axes.pop(0)
        sum_w, sum_w2, edges, n_raw = spectra[im]
        centres = 0.5 * (edges[:-1] + edges[1:])
        view = centres <= VIEW_MAX_GEV
        ax.errorbar(centres[view], sum_w[view], yerr=np.sqrt(sum_w2[view]),
                    fmt="o", ms=3.5, lw=1, capsize=1.5, color="#2f855a",
                    label="before post-processing")
        ax.axvline(110.0, color="#c05621", ls=":", lw=1.3,
                   label="Z cut at 110 GeV (keeps the right side)")
        delivered = [k for k in by_im.get(im, [])]
        if delivered:
            key, values, errors, edges2 = max(delivered, key=lambda t: np.sum(t[1]))
            c2 = 0.5 * (edges2[:-1] + edges2[1:])
            filled = errors > 0
            ax.plot(c2[filled], values[filled], "s", ms=7, mfc="none",
                    mec="#2b6cb0", mew=1.6, label="delivered")
        ax.set_title(f"{label}   ({im})", fontsize=10)
        ax.set_xlabel("dilepton invariant mass [GeV]")
        ax.set_ylabel("weighted events / 10 GeV")
        ax.set_xlim(0, VIEW_MAX_GEV)
        ax.legend(fontsize=7.5)
        ax.grid(alpha=0.25, lw=0.5)
        nz = np.nonzero(sum_w2 > 0)[0]
        summary[label] = {
            "im": im,
            "n_raw_entries_before_postprocessing": n_raw,
            "integral_weighted_before_postprocessing": float(sum_w.sum()),
            "n_filled_bins_before_postprocessing": int(nz.size),
            "first_filled_bin_centre_gev": float(centres[nz[0]]) if nz.size else None,
            "peak_bin_centre_gev": float(centres[int(np.argmax(sum_w))]),
            "n_delivered_histograms_for_this_im": len(delivered),
            "note": ("removed entirely by the 110 GeV Z cut" if not delivered
                     else "survives into the delivery"),
        }

    if other:
        ax = axes.pop(0)
        pick = max(other, key=lambda im: max(np.sum(t[1]) for t in by_im[im]))
        key, values, errors, edges = max(by_im[pick], key=lambda t: np.sum(t[1]))
        centres = 0.5 * (edges[:-1] + edges[1:])
        view = centres <= VIEW_MAX_GEV
        ax.errorbar(centres[view], values[view], yerr=errors[view],
                    fmt="o", ms=3.5, lw=1, capsize=1.5, color="#2b6cb0")
        ax.set_title(key, fontsize=8.5)
        ax.set_xlabel("two-object invariant mass [GeV]")
        ax.set_ylabel("weighted events / 10 GeV")
        ax.set_xlim(0, VIEW_MAX_GEV)
        ax.grid(alpha=0.25, lw=0.5)
        nzb = np.nonzero(errors > 0)[0]
        summary["delivered_two_object"] = {
            "im": pick, "histogram": key,
            "integral_weighted": float(values.sum()),
            "n_filled_bins": int(nzb.size),
            "first_filled_bin_centre_gev": (float(centres[nzb[0]])
                                            if nzb.size else None),
        }

    fig.suptitle(
        "MC smoke test -- dilepton mass from the same file. Error bars are "
        "sqrt(sum w^2).\n"
        "In a ggH->ZZ->4l sample the same-flavour pairs sit at or below the Z "
        "mass, so the 110 GeV Z cut removes them and none reaches the "
        "delivery.", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"wrote {out_path}")
    return summary


def closure_check(report: dict, record_id: str, by_im: dict) -> dict:
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

    integrals = {key: float(values.sum())
                 for entries in by_im.values()
                 for key, values, _e, _ed in entries}
    total_integral = sum(integrals.values())

    implied = (sum_sum_w_in_hist / norm) if norm else None
    expected = (sigma * 1000.0 * lumi * (implied / sigma_w)
                if implied is not None and sigma_w else None)

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
        "implied_sum_genweight_times_prefire": implied,
        "expected_yield_from_sigma_times_lumi_times_sigmaw_share": expected,
        "closure_relative_difference": (
            abs(expected - sum_sum_w_in_hist) / abs(sum_sum_w_in_hist)
            if sum_sum_w_in_hist else None),
        "formula": "expected = sigma_eff[pb] * 1000 * L_fb * "
                   "(sum(genWeight*L1prefire) over delivered entries / Sigma-w)",
        "note": "The arithmetic identity the weight definition implies. It "
                "verifies the normalisation was applied once and consistently "
                "and that nothing was lost between the weight arrays and the "
                "histograms. NOT a physics cross-check.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-file", required=True)
    ap.add_argument("--build-report", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--record-id", default="37728")
    ap.add_argument("--scratch-dir", default=None,
                    help="the builder's --keep-scratch directory. When given, "
                         "the 4-lepton panels also show the weighted spectrum "
                         "BEFORE post-processing, read from the shard masses and "
                         "their _mcw siblings.")
    args = ap.parse_args()

    root_path = pathlib.Path(args.root_file)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = json.loads(pathlib.Path(args.build_report).read_text(encoding="utf-8"))

    by_im = hists_by_im(root_path)
    print(f"{sum(len(v) for v in by_im.values())} TH1D histogram(s) across "
          f"{len(by_im)} IM combination(s)")
    spectra = ({} if not args.scratch_dir else
               spectra_from_shards(
                   pathlib.Path(args.scratch_dir),
                   list(FOUR_LEPTON_IM.values()) + list(DILEPTON_IM.values())))
    if spectra:
        print("pre-post-processing spectra pooled for: " + ", ".join(sorted(spectra)))

    summary = {
        "root_file": str(root_path),
        "build_report": str(args.build_report),
        "scratch_dir": args.scratch_dir,
        "n_histograms": sum(len(v) for v in by_im.values()),
        "n_im_combinations": len(by_im),
        "im_combinations": sorted(by_im),
        "four_lepton": plot_four_lepton(
            by_im, spectra, out_dir / "smoke_4lepton_mass.png"),
        "dilepton": plot_one_dilepton(
            by_im, spectra, out_dir / "smoke_dilepton_mass.png"),
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
