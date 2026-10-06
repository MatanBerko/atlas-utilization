#!/usr/bin/env python
"""
E5: the pilot plots.

  1. m(e, mu) over every selected electron-muon pair in accepted MuonEG
     pilot events, overlap removal OFF vs ON overlaid, 0-20 GeV in 0.1 GeV
     diagnostic bins, log y. The near-zero spike should disappear with the
     removal ON. These fine bins are DIAGNOSTIC ONLY -- the delivery
     binning (fixed 10 GeV, 0-10000 GeV) is untouched.
  2. m(e,e) in accepted DoubleEG pilot events, 60-120 GeV, split
     barrel-barrel vs other.
  3. light-jet multiplicity per dataset, accepted events.
  4. four example delivery-format histograms (10 GeV bins) of final states
     containing electrons, read from the ROOT file the B3 builder wrote
     from the pilot shards.

Everything except (4) comes from the per-job job_metadata.json files the
driver already wrote, so no event is re-read.

Usage:
    python make_pilot_plots.py --on-root /storage/.../pilot_on \
        --off-root /storage/.../pilot_off \
        --delivery-root /storage/.../deliver/four_pilot \
        --out-dir studies/cms_datasets/electron_vB/plots \
        --out-json studies/cms_datasets/electron_vB/evidence/E5_plot_inputs.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from studies.cms_datasets.cluster.run_dataset_on_file import DELIVERY_VETO_ORDER_4  # noqa: E402


def load_metadata(root: Path) -> dict:
    """{dataset: [job_metadata dicts]}"""
    out = {}
    for dataset in DELIVERY_VETO_ORDER_4:
        metas = []
        for d in sorted((root / dataset).glob("job_*")) if (root / dataset).exists() else []:
            f = d / "job_metadata.json"
            if f.exists():
                metas.append(json.loads(f.read_text(encoding="utf-8")))
        out[dataset] = metas
    return out


def sum_hist(metas, *path):
    """Sum a nested histogram dict across jobs. Returns (edges, counts, overflow)."""
    edges = None
    total = None
    overflow = 0
    for m in metas:
        node = m.get("matched4_diagnostics")
        for key in path:
            if node is None:
                break
            node = node.get(key)
        if not node:
            continue
        e = np.asarray(node["bin_edges_gev"], dtype=float)
        c = np.asarray(node["counts"], dtype=float)
        overflow += int(node.get("n_overflow", 0))
        if edges is None:
            edges, total = e, c.copy()
        else:
            assert np.array_equal(edges, e), "histogram binning differs between jobs"
            total += c
    return edges, total, overflow


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--on-root", required=True)
    p.add_argument("--off-root", required=True)
    p.add_argument("--delivery-root", default=None)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-json", required=True)
    args = p.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    on = load_metadata(Path(args.on_root))
    off = load_metadata(Path(args.off_root))
    evidence = {"what": "E5 pilot plot inputs", "on_root": args.on_root,
                "off_root": args.off_root, "plots": {}}

    # ---- 1. m(e, mu), MuonEG, OFF vs ON ------------------------------
    e_on, c_on, of_on = sum_hist(on["MuonEG"], "emu_pair_mass_fine_histogram_accepted_events")
    e_off, c_off, of_off = sum_hist(off["MuonEG"], "emu_pair_mass_fine_histogram_accepted_events")
    if e_on is not None and e_off is not None:
        fig, ax = plt.subplots(figsize=(7.5, 4.4))
        centres = 0.5 * (e_off[:-1] + e_off[1:])
        ax.step(centres, c_off, where="mid", label=f"removal OFF ({int(c_off.sum())} pairs)",
                color="crimson", lw=1.2)
        ax.step(0.5 * (e_on[:-1] + e_on[1:]), c_on, where="mid",
                label=f"removal ON ({int(c_on.sum())} pairs)", color="C0", lw=1.2)
        ax.set_yscale("log")
        ax.set_xlabel("m(e, $\\mu$) [GeV], every selected pair (0.1 GeV diagnostic bins)")
        ax.set_ylabel("pairs")
        ax.set_title("MuonEG pilot, accepted events: electron-muon pair mass\n"
                     "the near-zero spike is what the dR < 0.05 removal takes out")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "E5_muoneg_emu_mass_on_vs_off.png", dpi=140)
        plt.close(fig)
        low = e_off[:-1] < 1.0
        evidence["plots"]["muoneg_emu_mass"] = {
            "file": "E5_muoneg_emu_mass_on_vs_off.png",
            "n_pairs_off": int(c_off.sum()), "n_pairs_on": int(c_on.sum()),
            "n_pairs_below_1gev_off": int(c_off[low].sum()),
            "n_pairs_below_1gev_on": int(c_on[low].sum()),
            "n_overflow_above_20gev_off": of_off, "n_overflow_above_20gev_on": of_on,
        }
        print(f"m(e,mu) below 1 GeV: OFF {int(c_off[low].sum())} -> ON {int(c_on[low].sum())}")

    # ---- 2. m(e,e), DoubleEG, barrel-barrel vs other -----------------
    hists = {}
    for region in ("barrel_barrel", "other"):
        e, c, _ = sum_hist(on["DoubleEG"], "ee_pair_mass_z_histograms_accepted_events", region)
        if e is not None:
            hists[region] = (e, c)
    if hists:
        fig, ax = plt.subplots(figsize=(7.5, 4.4))
        for region, (e, c) in hists.items():
            ax.step(0.5 * (e[:-1] + e[1:]), c, where="mid",
                    label=f"{region.replace('_', '-')} ({int(c.sum())} pairs)", lw=1.2)
        ax.axvline(91.2, color="grey", ls=":", lw=1, label="91.2 GeV")
        ax.set_xlabel("m(e, e) [GeV], every selected pair (0.5 GeV diagnostic bins)")
        ax.set_ylabel("pairs")
        ax.set_title("DoubleEG pilot, accepted events: dielectron mass around the Z")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "E5_doubleeg_ee_mass_zpeak.png", dpi=140)
        plt.close(fig)
        evidence["plots"]["doubleeg_ee_mass"] = {
            "file": "E5_doubleeg_ee_mass_zpeak.png",
            "n_pairs": {r: int(c.sum()) for r, (e, c) in hists.items()},
            "peak_bin_gev": {r: float(0.5 * (e[int(np.argmax(c))] + e[int(np.argmax(c)) + 1]))
                             for r, (e, c) in hists.items() if c.sum()},
        }

    # ---- 3. light-jet multiplicity per dataset -----------------------
    mult = {}
    for dataset in DELIVERY_VETO_ORDER_4:
        total = {}
        for m in on[dataset]:
            d = (m.get("matched4_diagnostics") or {}).get(
                "light_jet_multiplicity_accepted_events", {})
            for k, v in d.items():
                total[int(k)] = total.get(int(k), 0) + int(v)
        if total:
            mult[dataset] = total
    if mult:
        fig, ax = plt.subplots(figsize=(7.5, 4.4))
        max_n = max(max(v) for v in mult.values())
        xs = np.arange(0, max_n + 1)
        width = 0.8 / max(len(mult), 1)
        for i, (dataset, total) in enumerate(mult.items()):
            ys = [total.get(int(x), 0) for x in xs]
            ax.bar(xs + i * width - 0.4 + width / 2, ys, width=width,
                   label=f"{dataset} ({sum(ys)} events)")
        ax.set_yscale("log")
        ax.set_xlabel("number of selected light jets")
        ax.set_ylabel("accepted events")
        ax.set_xticks(xs)
        ax.set_title("Light-jet multiplicity per dataset, pilot accepted events "
                     "(overlap removal ON)")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(out_dir / "E5_light_jet_multiplicity.png", dpi=140)
        plt.close(fig)
        evidence["plots"]["light_jet_multiplicity"] = {
            "file": "E5_light_jet_multiplicity.png",
            "counts": {d: {str(k): v for k, v in sorted(t.items())} for d, t in mult.items()},
        }

    # ---- 4. four delivery-format histograms with electrons -----------
    if args.delivery_root:
        import uproot
        roots = sorted(Path(args.delivery_root).glob("*_bumpnet.root"))
        if roots:
            with uproot.open(roots[0]) as f:
                names = [k.rstrip(";1") for k in f.keys()]
                with_e = [n for n in names
                          if "_cat_" in n and not n.split("_cat_")[1].startswith("0ex")]
                # most-populated first, so the examples are readable
                picked = sorted(with_e, key=lambda n: -float(f[n].values().sum()))[:4]
                fig, axes = plt.subplots(2, 2, figsize=(10.0, 6.4))
                details = []
                for ax, name in zip(axes.flat, picked):
                    h = f[name]
                    values = h.values()
                    edges = h.axis().edges()
                    nz = np.flatnonzero(values)
                    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, 1)
                    ax.step(0.5 * (edges[lo:hi] + edges[lo + 1:hi + 1]), values[lo:hi],
                            where="mid", lw=1.0)
                    ax.set_title(name, fontsize=7)
                    ax.set_xlabel("mass [GeV] (10 GeV bins)", fontsize=8)
                    ax.set_ylabel("entries", fontsize=8)
                    ax.tick_params(labelsize=7)
                    ax.grid(alpha=0.3)
                    details.append({"name": name, "n_entries": int(values.sum()),
                                    "n_filled_bins": int(np.count_nonzero(values))})
                for ax in axes.flat[len(picked):]:
                    ax.axis("off")
                fig.suptitle("Four delivery-format histograms (10 GeV bins) of final "
                             "states containing electrons,\nbuilt from the pilot shards "
                             "by build_four_dataset_delivery.py", fontsize=10)
                fig.tight_layout(rect=(0, 0, 1, 0.93))
                fig.savefig(out_dir / "E5_delivery_examples_with_electrons.png", dpi=140)
                plt.close(fig)
                evidence["plots"]["delivery_examples"] = {
                    "file": "E5_delivery_examples_with_electrons.png",
                    "root_file": str(roots[0]),
                    "n_histograms_in_file": len(names),
                    "n_with_electrons": len(with_e),
                    "examples": details,
                }
                print(f"delivery file {roots[0].name}: {len(names)} histograms, "
                      f"{len(with_e)} with electrons")
        else:
            print(f"no *_bumpnet.root under {args.delivery_root}")

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"wrote {args.out_json}")
    for name in sorted(p.name for p in out_dir.glob("E5_*.png")):
        print(f"  plot: {name}")


if __name__ == "__main__":
    main()
