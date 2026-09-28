#!/usr/bin/env python
"""
One PNG: the same histogram shown uncropped (full 0-10,000 GeV fixed
grid, empty bin 1 and all) and cropped (leading/trailing empty region
actually removed) side by side, so the difference is obvious at a glance.
Reads only the already-written ROOT files -- no shard access, no
recomputation.

Usage:
    python make_crop_comparison_plot.py \
        --out-dir /storage/.../deliver_doublemuon_bumpnet \
        --name mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import uproot  # noqa: E402

BIN_WIDTH_GEV = 10


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--name", required=True, help="BumpNet name, e.g. mass_m0m1j0_cat_0ex_2mx_1jx_0gx_0tx_0bx")
    p.add_argument("--uncropped-file", default="doublemuon_bumpnet_min31bins.root")
    p.add_argument("--cropped-file", default="doublemuon_bumpnet_min31bins_cropped.root")
    args = p.parse_args()
    out_dir = Path(args.out_dir)

    key = f"ROI_{args.name}_width_{BIN_WIDTH_GEV}"
    f_uncropped = uproot.open(str(out_dir / args.uncropped_file))
    f_cropped = uproot.open(str(out_dir / args.cropped_file))

    h_un = f_uncropped[key]
    h_cr = f_cropped[key]
    v_un, e_un = h_un.values(), h_un.axis().edges()
    v_cr, e_cr = h_cr.values(), h_cr.axis().edges()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    ax1.stairs(v_un, e_un, fill=False, linewidth=1.0)
    ax1.set_yscale("log")
    ax1.set_xlabel("Invariant mass [GeV]")
    ax1.set_ylabel("Events / 10 GeV")
    ax1.set_title(f"UNCROPPED ({args.uncropped_file})\nfull 0-10,000 GeV grid, {v_un.size} bins, "
                  f"bin 1 = {v_un[0]:.0f}", fontsize=9)
    ax1.set_xlim(0, e_un[-1])

    ax2.stairs(v_cr, e_cr, fill=False, linewidth=1.2, color="darkorange")
    ax2.set_yscale("log")
    ax2.set_xlabel("Invariant mass [GeV]")
    ax2.set_ylabel("Events / 10 GeV")
    ax2.set_title(f"CROPPED ({args.cropped_file})\n{e_cr[0]:.0f}-{e_cr[-1]:.0f} GeV, {v_cr.size} bins, "
                  f"bin 1 = {v_cr[0]:.0f}", fontsize=9)
    ax2.set_xlim(e_cr[0], e_cr[-1])

    fig.suptitle(args.name, fontsize=10)
    fig.tight_layout()
    out_png = out_dir / "plot_4_crop_comparison.png"
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"wrote {out_png}")
    print(f"uncropped: {v_un.size} bins (0-{e_un[-1]:.0f} GeV), bin1={v_un[0]}")
    print(f"cropped:   {v_cr.size} bins ({e_cr[0]:.0f}-{e_cr[-1]:.0f} GeV), bin1={v_cr[0]}")


if __name__ == "__main__":
    main()
