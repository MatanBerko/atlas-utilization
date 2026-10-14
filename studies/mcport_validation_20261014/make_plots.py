#!/usr/bin/env python
"""
MC-port validation plots (14 Oct 2026): OLD vs NEW overlaid with a NEW/OLD
ratio panel, plus a summary-table image.

  MC   (weighted, from the two 6-file builds, build_default/):
       the 2 most populated histograms of 67801 (ttbar), the most populated
       of 35669 (DY) and of 37728 (ggH->4l), and the most populated of the
       summed-SM file.
  Data (from the 8-file mini deliveries, full 0-10000 GeV grid file):
       the 2 most populated histograms.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402


def overlay(edges, old, new, title, path, old_label, new_label, ylabel):
    old, new = np.asarray(old, float), np.asarray(new, float)
    nz = np.flatnonzero((old != 0) | (new != 0))
    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, len(old))
    e, o, n = edges[lo:hi + 1], old[lo:hi], new[lo:hi]
    fig, (ax, rx) = plt.subplots(2, 1, figsize=(7, 5.2), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    ax.stairs(o, e, color="#1f4e9c", lw=1.6, label=old_label)
    ax.stairs(n, e, color="#d9622b", lw=1.2, ls="--", label=new_label)
    if (o > 0).all() or (o >= 0).all() and (n >= 0).all():
        ax.set_yscale("log")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=8)
    identical = o.tobytes() == n.tobytes()
    ax.legend(title=f"bins identical: {'YES' if identical else 'NO'}  |  "
                    f"sum {o.sum():,.6g} vs {n.sum():,.6g}", fontsize=8, title_fontsize=8)
    centers = 0.5 * (e[:-1] + e[1:])
    mask = o != 0
    ratio = np.divide(n, o, out=np.full_like(n, np.nan), where=mask)
    rx.axhline(1.0, color="0.5", lw=0.8)
    rx.plot(centers[mask], ratio[mask], "o", ms=2.5, color="black")
    rx.set_ylim(0.9, 1.1)
    rx.set_ylabel("NEW / OLD")
    rx.set_xlabel("mass [GeV]")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return {"plot": Path(path).name, "title": title, "sum_old": float(o.sum()),
            "sum_new": float(n.sum()), "n_nonzero_bins": int(mask.sum()),
            "bins_identical": bool(identical),
            "max_abs_ratio_minus_1": float(np.nanmax(np.abs(ratio[mask] - 1))) if mask.any() else None}


def top_hists(path: Path, k: int):
    f = uproot.open(path)
    keys = f.keys(cycle=False)
    keys = [x for x in keys if hasattr(f[x], "values")]
    return f, sorted(keys, key=lambda x: -float(np.abs(f[x].values()).sum()))[:k]


def summary_table(res: Path, path: Path):
    rows = []
    d = json.loads((res / "data_runs_rebuild_vs_mcport.json").read_text())
    for job, v in d["jobs"].items():
        n_arr = sum(s.get("n_arrays_compared", 0) for s in v["shards"].values())
        n_val = sum(s.get("n_values_compared", 0) for s in v["shards"].values())
        rows.append(["data", job, f"{n_arr:,}", f"{n_val:,}", "",
                     "IDENTICAL" if v["identical"] else "DIFFERS"])
    dd = json.loads((res / "data_delivery_rebuild_vs_mcport.json").read_text())
    for suf, v in dd["root_files"].items():
        rows.append(["data", f"mini delivery{suf}", f"{v['n_histograms_a']} hists",
                     f"{v['n_bins_compared']:,} bins", "", "IDENTICAL" if v["identical"] else "DIFFERS"])
    m = json.loads((res / "mc_runs_pilot_vs_new.json").read_text())
    for job, v in m["jobs"].items():
        n_arr = sum(s.get("n_arrays_compared", 0) for s in v["shards"].values())
        n_val = sum(s.get("n_values_compared", 0) for s in v["shards"].values())
        n_sib = sum(s.get("siblings_side_a", {}).get("n_sibling_arrays", 0) for s in v["shards"].values())
        rows.append(["MC", job, f"{n_arr:,}", f"{n_val:,}", f"{n_sib:,}",
                     "IDENTICAL" if v["identical"] else "DIFFERS"])
    b = json.loads((res / "mc_builds_old_vs_new.json").read_text())
    for name, v in b["root_files"].items():
        rows.append(["MC build", name, f"{v['n_histograms_a']} hists", f"{v['n_bins_compared']:,} bins",
                     "", "IDENTICAL" if v["identical"] else "DIFFERS"])
    cols = ["kind", "job / file", "arrays", "values", "MC sibling arrays", "result"]
    fig, ax = plt.subplots(figsize=(12, 0.4 * (len(rows) + 2)))
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center",
                 colWidths=[0.09, 0.36, 0.13, 0.15, 0.13, 0.12])
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1, 1.3)
    for (i, j), cell in t.get_celld().items():
        txt = cell.get_text().get_text()
        if i > 0 and j == 5:
            cell.set_facecolor("#cfe8cf" if txt == "IDENTICAL" else "#f4c7c3")
    ax.set_title("MC-port validation, 14 Oct 2026 — data: rebuild master vs MC-port branch; "
                 "MC: 10 Oct pilot / old MC branch vs MC-port branch", fontsize=9)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    for a in ("--mc-old-build", "--mc-new-build", "--data-old-delivery", "--data-new-delivery",
              "--prefix", "--results", "--out-dir"):
        p.add_argument(a, required=True)
    args = p.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    info = []
    mo, mn = Path(args.mc_old_build), Path(args.mc_new_build)
    picks = [("pilot_record67801_mc.root", 2, "ttbar 67801"), ("pilot_record35669_mc.root", 1, "DY 35669"),
             ("pilot_record37728_mc.root", 1, "ggH->4l 37728"), ("pilot_summedSM_mc.root", 1, "summed SM")]
    i = 0
    for fname, k, lab in picks:
        fo, names = top_hists(mo / fname, k)
        fn = uproot.open(mn / fname)
        for name in names:
            i += 1
            ho, hn = fo[name], fn[name]
            info.append(overlay(ho.axis().edges(), ho.values(), hn.values(),
                                f"MC {lab} (weighted, 6 files): {name}", out / f"mc_{i}.png",
                                "OLD (feature/cms-mc-weights-v3)", "NEW (cms-mc-on-master)",
                                "weighted events / bin"))
    fo, names = top_hists(Path(args.data_old_delivery) / f"{args.prefix}_bumpnet.root", 2)
    fn = uproot.open(Path(args.data_new_delivery) / f"{args.prefix}_bumpnet.root")
    for j, name in enumerate(names, 1):
        ho, hn = fo[name], fn[name]
        info.append(overlay(ho.axis().edges(), ho.values(), hn.values(),
                            f"data mini delivery (8 files): {name}", out / f"data_{j}.png",
                            "OLD (rebuilt master 6a055e8)", "NEW (cms-mc-on-master)", "entries / 10 GeV"))
    summary_table(Path(args.results), out / "summary_table.png")
    (out / "plots_info.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
