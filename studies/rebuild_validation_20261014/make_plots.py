#!/usr/bin/env python
"""
Rebuild validation plots (14 Oct 2026): OLD vs NEW overlaid, with a NEW/OLD
ratio panel underneath, plus one summary-table image.

  * the N most populated histograms of the mini delivery (full 0-10000 GeV
    grid file), and
  * for each of the four datasets, the most populated mass array of its
    job_0 rare4 inclusive shard (10 GeV bins), so every dataset appears.

Usage:
  make_plots.py --old-runs DIR --new-runs DIR --old-delivery DIR --new-delivery DIR
                --prefix rv8_four_dataset --results DIR --out-dir DIR [--n-delivery 4]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from compare import DATASETS, _read_db  # noqa: E402  (same folder)

BIN_WIDTH = 10.0
OLD_STYLE = dict(color="#1f4e9c", lw=1.6, label="OLD (ba89791)")
NEW_STYLE = dict(color="#d9622b", lw=1.2, ls="--", label="NEW (rebuild)")


def overlay(edges, old, new, title, path, xlabel="mass [GeV]"):
    old = np.asarray(old, float)
    new = np.asarray(new, float)
    nz = np.flatnonzero((old > 0) | (new > 0))
    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, len(old))
    e, o, n = edges[lo:hi + 1], old[lo:hi], new[lo:hi]
    fig, (ax, rx) = plt.subplots(2, 1, figsize=(7, 5.2), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    ax.stairs(o, e, **OLD_STYLE)
    ax.stairs(n, e, **NEW_STYLE)
    ax.set_yscale("log")
    ax.set_ylabel("entries / 10 GeV")
    ax.set_title(title, fontsize=8)
    identical = np.array_equal(o, n)
    ax.legend(title=f"bins identical: {'YES' if identical else 'NO'}  |  "
                    f"entries {int(o.sum()):,} vs {int(n.sum()):,}", fontsize=8, title_fontsize=8)
    centers = 0.5 * (e[:-1] + e[1:])
    mask = o > 0
    ratio = np.divide(n, o, out=np.full_like(n, np.nan), where=mask)
    rx.axhline(1.0, color="0.5", lw=0.8)
    rx.plot(centers[mask], ratio[mask], "o", ms=2.5, color="black")
    rx.set_ylim(0.9, 1.1)
    rx.set_ylabel("NEW / OLD")
    rx.set_xlabel(xlabel)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return {"plot": Path(path).name, "title": title, "n_bins_nonempty": int(mask.sum()),
            "entries_old": int(o.sum()), "entries_new": int(n.sum()), "bins_identical": bool(identical),
            "max_abs_ratio_minus_1": float(np.nanmax(np.abs(ratio[mask] - 1))) if mask.any() else None}


def fixed_hist(values):
    values = values[np.isfinite(values)]
    hi = max(BIN_WIDTH, np.ceil(values.max() / BIN_WIDTH) * BIN_WIDTH) if values.size else BIN_WIDTH
    edges = np.arange(0.0, hi + BIN_WIDTH, BIN_WIDTH)
    return np.histogram(values, bins=edges)[0], edges


def _fmt(x):
    return "" if x is None else f"{x:,}"


def summary_table(results_dir: Path, path: Path):
    rows = []
    r = json.loads((results_dir / "runs_old_vs_new.json").read_text())
    r7 = results_dir / "runs_7oct_vs_new.json"
    r7 = json.loads(r7.read_text()) if r7.exists() else None
    for job, v in r["jobs"].items():
        n_arr = sum(s.get("n_arrays_compared", 0) for s in v["shards"].values())
        n_val = sum(s.get("n_values_compared", 0) for s in v["shards"].values())
        c = v["cutflow_a"]
        rows.append([job, _fmt(c.get("n_read")), _fmt(c.get("n_after_gate")), _fmt(c.get("n_exclusive")), f"{len(v['shards'])}", f"{n_arr:,}", f"{n_val:,}",
                     "IDENTICAL" if v["identical"] else "DIFFERS",
                     ("IDENTICAL" if r7["jobs"][job]["identical"] else "DIFFERS") if r7 else "n/a"])
    d = results_dir / "delivery_old_vs_new.json"
    if d.exists():
        dd = json.loads(d.read_text())
        for suffix, v in dd["root_files"].items():
            rows.append([f"mini delivery {suffix}", "", "", "", f"{v['n_histograms_a']} hists",
                         "", f"{v['n_bins_compared']:,} bins",
                         "IDENTICAL" if v["identical"] else "DIFFERS", ""])
    cols = ["job / file", "events read", "accepted", "exclusive", "shards", "arrays", "values",
            "OLD vs NEW", "7 Oct vs NEW"]
    fig, ax = plt.subplots(figsize=(13, 0.42 * (len(rows) + 2)))
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1, 1.3)
    for (i, j), cell in t.get_celld().items():
        if i > 0 and j >= 7 and cell.get_text().get_text() == "DIFFERS":
            cell.set_facecolor("#f4c7c3")
        elif i > 0 and j >= 7 and cell.get_text().get_text() == "IDENTICAL":
            cell.set_facecolor("#cfe8cf")
    ax.set_title("Rebuild validation, 14 Oct 2026: OLD (ba89791) vs NEW (rebuild/master-2026-10-14)",
                 fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    for a in ("--old-runs", "--new-runs", "--old-delivery", "--new-delivery", "--prefix",
              "--results", "--out-dir"):
        p.add_argument(a, required=True)
    p.add_argument("--n-delivery", type=int, default=4)
    args = p.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    info = []

    import uproot
    fo = uproot.open(Path(args.old_delivery) / f"{args.prefix}_bumpnet.root")
    fn = uproot.open(Path(args.new_delivery) / f"{args.prefix}_bumpnet.root")
    names = sorted(fo.keys(cycle=False), key=lambda k: -fo[k].values().sum())
    for i, name in enumerate(names[:args.n_delivery], 1):
        ho, hn = fo[name], fn[name]
        info.append(overlay(ho.axis().edges(), ho.values(), hn.values(),
                            f"mini delivery: {name}", out / f"delivery_{i}.png"))

    for ds in DATASETS:
        shard = "dataset_shard_rare4_inclusive.sqlite"
        a = _read_db(Path(args.old_runs) / ds / "job_0" / shard)["chunks"]
        b = _read_db(Path(args.new_runs) / ds / "job_0" / shard)["chunks"]
        key = max(a, key=lambda k: sum(x.size for _, x in a[k]))
        va = np.concatenate([x for _, x in a[key]]).astype(float)
        vb = np.concatenate([x for _, x in b[key]]).astype(float)
        ha, edges = fixed_hist(np.concatenate([va, vb]))
        ha = np.histogram(va, bins=edges)[0]
        hb = np.histogram(vb, bins=edges)[0]
        rec = overlay(edges, ha, hb, f"{ds} job_0 rare4 inclusive shard: {key[1]}",
                      out / f"perfile_{ds}.png")
        rec["arrays_bitwise_identical"] = bool(va.size == vb.size and va.tobytes() == vb.tobytes())
        info.append(rec)

    summary_table(Path(args.results), out / "summary_table.png")
    (out / "plots_info.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
