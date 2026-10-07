#!/usr/bin/env python
"""
Step D4: the delivery plots.

  (a) m(e,mu) 0-20 GeV in 0.1 GeV diagnostic bins, log y, over accepted
      events of MuonEG + DoubleMuon + SingleMuon -- the check that neither
      the near-zero spike nor the 1.5-5 GeV cluster survives.
  (b) m(e,e) 60-120 GeV around the Z, barrel-barrel vs other, from
      accepted DoubleEG events.
  (c) m(mu,mu) 60-120 GeV around the Z, for comparison.
  (d) light-jet multiplicity per dataset, accepted events.
  (e) number of delivered histograms per final state, coloured by whether
      the final state contains electrons.
  (f) six example delivered histograms on the real 10 GeV grid, at least
      four from final states containing electrons and at least one from an
      electron-muon final state.

(a), (b), (d) come from the per-job diagnostics the driver already wrote
for ACCEPTED events, so no event is re-read. (c) comes from the driver's
dimuon-mass diagnostic, which is filled over each dataset's TRIGGERED
events rather than its accepted ones -- that difference is stated on the
plot itself rather than glossed over. (e) and (f) are read from the
delivered ROOT file.

Usage:
    python make_delivery_plots.py --runs-root /storage/.../runs_matched4_full_<date> \
        --delivery-dir /storage/.../deliver/four_dataset_..._<date> \
        --out-dir plots --out-json evidence/D4_plot_inputs.json
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
from studies.cms_datasets.electron_vB.verify_delivery import (  # noqa: E402
    parse_name, final_state_from_cat, read_histograms,
)


def load_metadata(root: Path) -> dict:
    out = {}
    for dataset in DELIVERY_VETO_ORDER_4:
        metas = []
        d = root / dataset
        if d.exists():
            for job in sorted(d.glob("job_*")):
                f = job / "job_metadata.json"
                if f.exists():
                    metas.append(json.loads(f.read_text(encoding="utf-8")))
        out[dataset] = metas
    return out


def sum_hist(metas, getter):
    edges = None
    total = None
    overflow = 0
    for m in metas:
        node = getter(m)
        if not node:
            continue
        e = np.asarray(node["bin_edges_gev"], dtype=float)
        c = np.asarray(node["counts"], dtype=float)
        overflow += int(node.get("n_overflow", 0))
        if edges is None:
            edges, total = e, c.copy()
        else:
            if not np.array_equal(edges, e):
                raise SystemExit("histogram binning differs between jobs")
            total += c
    return edges, total, overflow


def _m4(key):
    return lambda m: (m.get("matched4_diagnostics") or {}).get(key)


def _m4_region(key, region):
    def g(m):
        node = (m.get("matched4_diagnostics") or {}).get(key) or {}
        return node.get(region)
    return g


def _diag(key):
    return lambda m: (m.get("diagnostics") or {}).get(key)


def has_electrons(fs: str) -> bool:
    for field in fs.split("_"):
        if field.endswith("e"):
            return int(field[:-1]) > 0
    return False


def has_muons(fs: str) -> bool:
    for field in fs.split("_"):
        if field.endswith("m"):
            return int(field[:-1]) > 0
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs-root", required=True)
    p.add_argument("--delivery-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--out-json", required=True)
    args = p.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = load_metadata(Path(args.runs_root))
    ev = {"what": "D4 delivery plot inputs", "runs_root": args.runs_root,
          "delivery_dir": args.delivery_dir, "plots": {}}

    # ---- (a) m(e,mu) over the three datasets that can have one ----------
    sets = ["MuonEG", "DoubleMuon", "SingleMuon"]
    metas = [m for ds in sets for m in meta[ds]]
    edges, counts, overflow = sum_hist(metas, _m4("emu_pair_mass_fine_histogram_accepted_events"))
    if edges is not None:
        fig, ax = plt.subplots(figsize=(7.8, 4.6))
        ax.step(0.5 * (edges[:-1] + edges[1:]), counts, where="mid", lw=1.2, color="C0")
        ax.set_yscale("log")
        ax.set_xlabel("m(e, $\\mu$) [GeV], every selected pair (0.1 GeV diagnostic bins)")
        ax.set_ylabel("pairs")
        ax.set_title("Accepted events of MuonEG + DoubleMuon + SingleMuon:\n"
                     "electron-muon pair mass after the dR < 0.12 overlap removal")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "D4a_emu_mass.png", dpi=140)
        plt.close(fig)
        lo = edges[:-1]
        ev["plots"]["a_emu_mass"] = {
            "file": "D4a_emu_mass.png", "datasets": sets,
            "n_pairs_0_20gev": int(counts.sum()),
            "n_pairs_below_1gev": int(counts[lo < 1.0].sum()),
            "n_pairs_1p5_to_5gev": int(counts[(lo >= 1.5) & (lo < 5.0)].sum()),
            "n_pairs_below_5gev": int(counts[lo < 5.0].sum()),
            "n_pairs_above_20gev_overflow": overflow,
        }
        print(f"(a) m(e,mu): <1 GeV {int(counts[lo < 1.0].sum())}, "
              f"1.5-5 GeV {int(counts[(lo >= 1.5) & (lo < 5.0)].sum())}, "
              f"<5 GeV {int(counts[lo < 5.0].sum())}")

    # ---- (b) m(ee) around the Z, by region ------------------------------
    regions = {}
    for region in ("barrel_barrel", "other"):
        e, c, _o = sum_hist(meta["DoubleEG"],
                            _m4_region("ee_pair_mass_z_histograms_accepted_events", region))
        if e is not None:
            regions[region] = (e, c)
    if regions:
        fig, ax = plt.subplots(figsize=(7.8, 4.6))
        for region, (e, c) in regions.items():
            ax.step(0.5 * (e[:-1] + e[1:]), c, where="mid", lw=1.2,
                    label=f"{region.replace('_', '-')} ({int(c.sum())} pairs)")
        ax.axvline(91.19, color="grey", ls=":", lw=1, label="m(Z) = 91.19 GeV")
        ax.set_xlabel("m(e, e) [GeV] (0.5 GeV diagnostic bins)")
        ax.set_ylabel("pairs")
        ax.set_title("Accepted DoubleEG events: dielectron mass around the Z")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "D4b_ee_mass_zpeak.png", dpi=140)
        plt.close(fig)
        ev["plots"]["b_ee_mass"] = {
            "file": "D4b_ee_mass_zpeak.png",
            "n_pairs": {r: int(c.sum()) for r, (e, c) in regions.items()},
            "peak_bin_centre_gev": {
                r: float(0.5 * (e[int(np.argmax(c))] + e[int(np.argmax(c)) + 1]))
                for r, (e, c) in regions.items() if c.sum()}}
        print(f"(b) m(ee) peak bins: {ev['plots']['b_ee_mass']['peak_bin_centre_gev']}")

    # ---- (c) m(mumu) around the Z ---------------------------------------
    mm = {}
    for ds in ("DoubleMuon", "SingleMuon"):
        e, c, _o = sum_hist(meta[ds], _diag("raw_dimuon_mass_mu0mu1"))
        if e is not None:
            mm[ds] = (e, c)
    if mm:
        fig, ax = plt.subplots(figsize=(7.8, 4.6))
        for ds, (e, c) in mm.items():
            lo = e[:-1]
            win = (lo >= 60.0) & (lo < 120.0)
            ax.step(0.5 * (e[:-1] + e[1:])[win], c[win], where="mid", lw=1.2,
                    label=f"{ds} ({int(c[win].sum())} pairs in 60-120)")
        ax.axvline(91.19, color="grey", ls=":", lw=1, label="m(Z) = 91.19 GeV")
        ax.set_xlabel("m($\\mu$, $\\mu$) of the two leading muons [GeV] (1 GeV bins)")
        ax.set_ylabel("events")
        ax.set_title("Dimuon mass around the Z, for comparison with the dielectron peak\n"
                     "(filled over each dataset's TRIGGERED events, not only accepted ones)")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "D4c_mumu_mass_zpeak.png", dpi=140)
        plt.close(fig)
        peaks = {}
        for ds, (e, c) in mm.items():
            lo = e[:-1]
            win = (lo >= 60.0) & (lo < 120.0)
            idx = int(np.argmax(np.where(win, c, -1)))
            peaks[ds] = float(0.5 * (e[idx] + e[idx + 1]))
        ev["plots"]["c_mumu_mass"] = {
            "file": "D4c_mumu_mass_zpeak.png", "peak_bin_centre_gev": peaks,
            "population": "each dataset's triggered events (driver diagnostic)"}
        print(f"(c) m(mumu) peak bins: {peaks}")

    # ---- (d) light-jet multiplicity per dataset -------------------------
    mult = {}
    for ds in DELIVERY_VETO_ORDER_4:
        total = {}
        for m in meta[ds]:
            d = (m.get("matched4_diagnostics") or {}).get(
                "light_jet_multiplicity_accepted_events", {})
            for k, v in d.items():
                total[int(k)] = total.get(int(k), 0) + int(v)
        if total:
            mult[ds] = total
    if mult:
        fig, ax = plt.subplots(figsize=(8.2, 4.6))
        max_n = max(max(v) for v in mult.values())
        xs = np.arange(0, max_n + 1)
        width = 0.8 / max(len(mult), 1)
        for i, (ds, total) in enumerate(mult.items()):
            ys = [total.get(int(x), 0) for x in xs]
            ax.bar(xs + i * width - 0.4 + width / 2, ys, width=width,
                   label=f"{ds} ({sum(ys):,} events)")
        ax.set_yscale("log")
        ax.set_xlabel("number of selected light jets")
        ax.set_ylabel("accepted events")
        ax.set_xticks(xs)
        ax.set_title("Light-jet multiplicity per dataset, accepted events (full production)")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(out_dir / "D4d_light_jet_multiplicity.png", dpi=140)
        plt.close(fig)
        ev["plots"]["d_light_jet_multiplicity"] = {
            "file": "D4d_light_jet_multiplicity.png",
            "counts": {d: {str(k): v for k, v in sorted(t.items())} for d, t in mult.items()}}

    # ---- (e) and (f) from the delivered file ----------------------------
    ddir = Path(args.delivery_dir)
    roots = sorted(ddir.glob("*_bumpnet.root"))
    if roots:
        hists, _keys = read_histograms(roots[0])
        per_fs = {}
        entries_fs = {}
        for n, (v, _e) in hists.items():
            info = parse_name(n)
            if info is None:
                continue
            fs = final_state_from_cat(info["cat"])
            per_fs[fs] = per_fs.get(fs, 0) + 1
            entries_fs[fs] = entries_fs.get(fs, 0.0) + float(v.sum())

        order = sorted(per_fs, key=lambda f: (-per_fs[f], f))
        colours = ["#c2185b" if has_electrons(f) else "#1976d2" for f in order]
        fig, ax = plt.subplots(figsize=(min(16, 0.18 * len(order) + 3), 4.8))
        ax.bar(np.arange(len(order)), [per_fs[f] for f in order], color=colours)
        ax.set_xlabel(f"final state ({len(order)} of them, most histograms first)")
        ax.set_ylabel("delivered histograms")
        n_e = sum(1 for f in order if has_electrons(f))
        ax.set_title("Delivered histograms per final state\n"
                     f"pink = contains electrons ({n_e} final states), "
                     f"blue = no electrons ({len(order) - n_e})")
        ax.set_xticks([])
        ax.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(out_dir / "D4e_histograms_per_final_state.png", dpi=140)
        plt.close(fig)
        ev["plots"]["e_histograms_per_final_state"] = {
            "file": "D4e_histograms_per_final_state.png",
            "n_final_states": len(order),
            "n_final_states_with_electrons": n_e,
            "max_histograms_in_one_final_state": max(per_fs.values()),
            "top_10": [{"final_state": f, "n_histograms": per_fs[f],
                        "entries": int(entries_fs[f])} for f in order[:10]]}

        # six examples: >=4 with electrons, >=1 from an e-mu final state
        with_emu = [n for n in hists
                    if has_electrons(final_state_from_cat(parse_name(n)["cat"]))
                    and has_muons(final_state_from_cat(parse_name(n)["cat"]))]
        with_e = [n for n in hists
                  if has_electrons(final_state_from_cat(parse_name(n)["cat"]))
                  and n not in with_emu]
        without_e = [n for n in hists
                     if not has_electrons(final_state_from_cat(parse_name(n)["cat"]))]
        by_entries = lambda ns: sorted(ns, key=lambda n: -float(hists[n][0].sum()))
        picked = (by_entries(with_emu)[:2] + by_entries(with_e)[:3]
                  + by_entries(without_e)[:1])[:6]
        fig, axes = plt.subplots(2, 3, figsize=(13.5, 6.6))
        details = []
        for ax, name in zip(axes.flat, picked):
            values, edges = hists[name]
            nz = np.flatnonzero(values)
            lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, 1)
            ax.step(0.5 * (edges[lo:hi] + edges[lo + 1:hi + 1]), values[lo:hi],
                    where="mid", lw=1.0)
            fs = final_state_from_cat(parse_name(name)["cat"])
            ax.set_title(name.replace("ROI_mass_", ""), fontsize=6.5)
            ax.set_xlabel("mass [GeV] (10 GeV bins)", fontsize=8)
            ax.set_ylabel("entries", fontsize=8)
            ax.tick_params(labelsize=7)
            ax.grid(alpha=0.3)
            details.append({"name": name, "final_state": fs,
                            "has_electrons": has_electrons(fs),
                            "has_muons": has_muons(fs),
                            "n_entries": int(values.sum()),
                            "n_filled_bins": int(np.count_nonzero(values))})
        for ax in axes.flat[len(picked):]:
            ax.axis("off")
        fig.suptitle("Six delivered histograms on the real 10 GeV grid "
                     "(four or more from final states containing electrons)", fontsize=10)
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        fig.savefig(out_dir / "D4f_delivery_examples.png", dpi=140)
        plt.close(fig)
        ev["plots"]["f_examples"] = {"file": "D4f_delivery_examples.png",
                                     "root_file": str(roots[0]), "examples": details}
        print(f"(f) examples: {sum(1 for d in details if d['has_electrons'])} with electrons, "
              f"{sum(1 for d in details if d['has_electrons'] and d['has_muons'])} e-mu")

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(ev, indent=2), encoding="utf-8")
    print(f"wrote {args.out_json}")
    for f in sorted(out_dir.glob("D4*.png")):
        print(f"  plot: {f.name}")


if __name__ == "__main__":
    main()
