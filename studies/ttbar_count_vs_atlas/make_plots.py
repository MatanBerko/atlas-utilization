#!/usr/bin/env python
"""
Step 9 (ttbar_count_vs_atlas): the four required PNG plots.

  1 categories_by_lepton_content.png
      Categories per notrigger variant, stacked by lepton content, with
      our delivered CMS DATA result (muon-triggered, 55 categories) as a
      reference bar.
  2 per_category_pr31_vs_cms_data.png
      Per-category histogram counts, variant (b) pr31 vs the CMS data
      delivery, restricted to the categories the two have in common.
  3 example_histograms.png
      Three example ttbar histograms from variant (a) rare4: the one with
      the most events, the median one, and the one closest to the 25-bin
      boundary.
  4 overlap_removal_effect.png
      One category's mass distribution with (variant b) and without
      (variant c) our jet-lepton dR < 0.4 overlap removal.

Colour: the three categorical slots that are documented as validating on
the all-pairs test in both modes (blue / orange / aqua). No hue is
cycled, no dual axis is used, a legend is present whenever more than one
series is drawn, every bar carries a direct value label, and the grid is
recessive. Reference (non-series) quantities are drawn in neutral grey so
they never read as a fourth category.

Usage:
    python make_plots.py --study-dir <dir with the per-variant outputs> \
        --cms-delivery-root <our delivered CMS data min26bins ROOT file> \
        --out-dir <plots dir>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import uproot

# --- palette ---------------------------------------------------------
# Categorical slots 1-3 (blue, orange, aqua): the documented subset that
# passes the all-pairs colour-vision checks in both light and dark modes.
C_BLUE = "#2a78d6"
C_ORANGE = "#eb6834"
C_AQUA = "#1baf7a"
# Reference / non-series ink.
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#8a8984"
GRID = "#e3e2de"
REF_GREY = "#b4b3ad"
SURFACE = "#fcfcfb"

LEPTON_ORDER = ["at_least_one_muon", "electrons_but_no_muon", "no_lepton"]
LEPTON_LABEL = {
    "at_least_one_muon": "at least one muon",
    "electrons_but_no_muon": "electrons, no muon",
    "no_lepton": "no lepton",
}
LEPTON_COLOR = {
    "at_least_one_muon": C_BLUE,
    "electrons_but_no_muon": C_ORANGE,
    "no_lepton": C_AQUA,
}
VARIANT_LABEL = {
    "rare4": "(a) rare4\nour rule",
    "pr31": "(b) pr31\n>=5 light jets dropped",
    "pr31_noOR": "(c) pr31_noOR\nno overlap removal",
}

THRESHOLD_KEY = "d_ge25_bins"  # the ATLAS wording: >= 25 filled bins


def style(ax, title=None, xlabel=None, ylabel=None):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=3, color=GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, color=INK, fontsize=12, loc="left", pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_2, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_2, fontsize=10)


def strip_key(k: str) -> str:
    n = k.split(";")[0]
    if n.startswith("ROI_"):
        n = n[len("ROI_"):]
    if "_width_" in n:
        n = n.rsplit("_width_", 1)[0]
    return n


def category_of(name: str) -> str:
    return name.split("_cat_", 1)[1] if "_cat_" in name else "UNKNOWN"


def lepton_content(category: str) -> str:
    counts = {}
    for tok in category.split("_"):
        tok = tok[:-1] if tok.endswith("x") else tok
        if len(tok) >= 2 and tok[:-1].isdigit():
            counts[tok[-1]] = int(tok[:-1])
    if counts.get("m", 0) >= 1:
        return "at_least_one_muon"
    if counts.get("e", 0) >= 1:
        return "electrons_but_no_muon"
    return "no_lepton"


def read_root(path):
    out = {}
    with uproot.open(path) as f:
        for key in sorted(set(k.split(";")[0] for k in f.keys())):
            obj = f[key]
            if not hasattr(obj, "values"):
                continue
            out[strip_key(key)] = (np.asarray(obj.values(), dtype=float),
                                   np.asarray(obj.axis().edges(), dtype=float))
    return out


# --- plot 1 ----------------------------------------------------------
def plot_categories(summaries, cms_cats, out_path):
    bars = []
    for v in ("rare4", "pr31", "pr31_noOR"):
        counts = summaries[v]["breakdown"][THRESHOLD_KEY]["n_categories_by_lepton_content"]
        bars.append((VARIANT_LABEL[v], {k: counts.get(k, 0) for k in LEPTON_ORDER}, False))
    ref = {k: 0 for k in LEPTON_ORDER}
    for c in cms_cats:
        ref[lepton_content(c)] += 1
    bars.append(("CMS DATA delivery\n(muon-triggered, reference)", ref, True))

    fig, ax = plt.subplots(figsize=(9.5, 5.6), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    x = np.arange(len(bars))
    bottoms = np.zeros(len(bars))
    for comp in LEPTON_ORDER:
        vals = np.array([b[1][comp] for b in bars], dtype=float)
        colors = [REF_GREY if b[2] else LEPTON_COLOR[comp] for b in bars]
        ax.bar(x, vals, bottom=bottoms, width=0.58, color=colors,
               edgecolor=SURFACE, linewidth=2, zorder=3)
        for xi, (v0, b0) in enumerate(zip(vals, bottoms)):
            if v0 > 0:
                ax.text(xi, b0 + v0 / 2, f"{int(v0)}", ha="center", va="center",
                        color="white" if v0 > 6 else INK, fontsize=9, zorder=4)
        bottoms += vals
    for xi, tot in enumerate(bottoms):
        ax.text(xi, tot + max(bottoms) * 0.02, f"{int(tot)}", ha="center", va="bottom",
                color=INK, fontsize=11, fontweight="bold", zorder=4)

    ax.set_xticks(x)
    ax.set_xticklabels([b[0] for b in bars], fontsize=9, color=INK_2)
    style(ax, title="CMS ttbar (TTTo2L2Nu, record 67801) categories at >= 25 filled bins",
          ylabel="categories")
    handles = [plt.Rectangle((0, 0), 1, 1, color=LEPTON_COLOR[k]) for k in LEPTON_ORDER]
    handles.append(plt.Rectangle((0, 0), 1, 1, color=REF_GREY))
    labels = [LEPTON_LABEL[k] for k in LEPTON_ORDER] + ["CMS data delivery (reference)"]
    ax.legend(handles, labels, frameon=False, fontsize=9, ncol=4,
              loc="upper center", bbox_to_anchor=(0.5, -0.13), labelcolor=INK_2)
    ax.set_ylim(0, max(bottoms) * 1.12)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}")


# --- plot 2 ----------------------------------------------------------
def plot_per_category(pr31_hists, cms_hists, out_path):
    def per_cat(hists):
        d = {}
        for name in hists:
            d[category_of(name)] = d.get(category_of(name), 0) + 1
        return d

    a, b = per_cat(pr31_hists), per_cat(cms_hists)
    shared = sorted(set(a) & set(b), key=lambda c: -(a[c] + b[c]))
    if not shared:
        print("plot 2: no shared categories, skipping")
        return
    h = max(4.0, 0.30 * len(shared) + 2.2)
    fig, ax = plt.subplots(figsize=(10.5, h), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    y = np.arange(len(shared))
    ax.barh(y + 0.19, [a[c] for c in shared], height=0.34, color=C_BLUE,
            edgecolor=SURFACE, linewidth=2, zorder=3,
            label="ttbar MC, variant (b) pr31 (> 25 bins)")
    ax.barh(y - 0.19, [b[c] for c in shared], height=0.34, color=C_ORANGE,
            edgecolor=SURFACE, linewidth=2, zorder=3, label="CMS data delivery (rare4)")
    for yi, c in zip(y, shared):
        ax.text(a[c] + 0.6, yi + 0.19, str(a[c]), va="center", fontsize=7.5, color=INK_2)
        ax.text(b[c] + 0.6, yi - 0.19, str(b[c]), va="center", fontsize=7.5, color=INK_2)
    ax.set_yticks(y)
    ax.set_yticklabels([c.replace("x", "") for c in shared], fontsize=7)
    ax.invert_yaxis()
    style(ax, title=f"Histograms per category, {len(shared)} shared categories "
                    f"(both sides at > 25 filled bins)", xlabel="histograms")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.legend(frameon=False, fontsize=9, loc="lower right", labelcolor=INK_2)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path} ({len(shared)} shared categories)")


# --- plot 3 ----------------------------------------------------------
def plot_examples(hists, out_path):
    stats = []
    for name, (values, edges) in hists.items():
        stats.append((name, float(values.sum()), int(np.count_nonzero(values))))
    if not stats:
        print("plot 3: no histograms, skipping")
        return
    by_events = sorted(stats, key=lambda s: -s[1])
    largest = by_events[0]
    median = by_events[len(by_events) // 2]
    near25 = min(stats, key=lambda s: (abs(s[2] - 25), -s[1]))
    picks = [("most events", largest), ("median by events", median),
             ("closest to the 25-bin boundary", near25)]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    for ax, (why, (name, n_ev, n_bins)) in zip(axes, picks):
        values, edges = hists[name]
        nz = np.nonzero(values)[0]
        lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, 1)
        centers = 0.5 * (edges[:-1] + edges[1:])
        ax.step(centers[lo:hi], values[lo:hi], where="mid", color=C_BLUE, linewidth=2, zorder=3)
        ax.fill_between(centers[lo:hi], values[lo:hi], step="mid",
                        color=C_BLUE, alpha=0.14, zorder=2)
        short = name.replace("mass_", "").replace("_cat_", "  cat ").replace("x", "")
        style(ax, title=f"{why}\n{short}", xlabel="invariant mass [GeV]", ylabel="events")
        ax.set_title(f"{why}\n{short}", color=INK, fontsize=9, loc="left", pad=10)
        ax.text(0.98, 0.95, f"{int(n_ev)} events\n{n_bins} filled bins",
                transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=INK_2)
    fig.suptitle("CMS ttbar example histograms, variant (a) rare4",
                 color=INK, fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}")
    return [{"why": w, "name": n, "n_events": e, "n_filled_bins": b} for w, (n, e, b) in picks]


# --- plot 4 ----------------------------------------------------------
def plot_overlap_effect(pr31_hists, noor_hists, out_path):
    shared = set(pr31_hists) & set(noor_hists)
    if not shared:
        print("plot 4: no shared histogram between (b) and (c), skipping")
        return None
    # The shared histogram where the two differ most in total events --
    # i.e. where overlap removal actually did something visible.
    name = max(shared, key=lambda n: abs(float(pr31_hists[n][0].sum())
                                         - float(noor_hists[n][0].sum())))
    vb, eb = pr31_hists[name]
    vc, _ec = noor_hists[name]
    nz = np.nonzero(vb + vc)[0]
    lo, hi = (nz[0], nz[-1] + 1) if nz.size else (0, 1)
    centers = 0.5 * (eb[:-1] + eb[1:])

    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.step(centers[lo:hi], vb[lo:hi], where="mid", color=C_BLUE, linewidth=2, zorder=4,
            label=f"(b) pr31, overlap removal ON  -  {int(vb.sum())} events")
    ax.step(centers[lo:hi], vc[lo:hi], where="mid", color=C_ORANGE, linewidth=2, zorder=3,
            label=f"(c) pr31_noOR, overlap removal OFF  -  {int(vc.sum())} events")
    short = name.replace("mass_", "").replace("_cat_", "  cat ").replace("x", "")
    style(ax, title=f"Effect of the jet-lepton dR < 0.4 overlap removal\n{short}",
          xlabel="invariant mass [GeV]", ylabel="events (log scale)")
    # Log y: on a linear scale the very-low-mass spike that overlap removal
    # exists to kill -- a muon also reconstructed as a jet right next to it, so
    # the pair carries almost no invariant mass -- is so tall that the rest of
    # the distribution is squashed flat and the two curves cannot be compared.
    ax.set_yscale("log")
    both = np.concatenate([vb[lo:hi], vc[lo:hi]])
    positive = both[both > 0]
    if positive.size:
        ax.set_ylim(bottom=max(1.0, float(positive.min()) * 0.5))
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_2, loc="upper right")
    ax.annotate("low-mass spike: \"jets\" that are really the muon\n"
                "(removed by the dR < 0.4 cut)",
                xy=(0.04, 0.10), xycoords="axes fraction", fontsize=8.5, color=INK_2)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path} (histogram {name})")
    return {"name": name, "n_events_pr31": float(vb.sum()), "n_events_pr31_noOR": float(vc.sum())}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--study-dir", required=True)
    p.add_argument("--cms-delivery-root", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--prefix", default="ttbar_notrigger")
    args = p.parse_args()

    study = Path(args.study_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries = {}
    roots = {}        # >= 25 filled bins (the ATLAS wording)
    roots_gt25 = {}   # >  25 filled bins (what our CMS data delivery uses)
    for v in ("rare4", "pr31", "pr31_noOR"):
        summaries[v] = json.loads((study / v / f"build_summary_{v}.json").read_text())
        roots[v] = read_root(str(study / v / f"{args.prefix}_{v}_ge25bins.root"))
        roots_gt25[v] = read_root(str(study / v / f"{args.prefix}_{v}_min26bins.root"))
        print(f"{v}: {len(roots[v])} histograms at >= 25 filled bins, "
              f"{len(roots_gt25[v])} at > 25")

    cms = read_root(args.cms_delivery_root)
    cms_cats = sorted({category_of(n) for n in cms})
    print(f"CMS data delivery: {len(cms)} histograms, {len(cms_cats)} categories")

    manifest = {}
    plot_categories(summaries, cms_cats, out_dir / "1_categories_by_lepton_content.png")
    plot_per_category(roots_gt25["pr31"], cms, out_dir / "2_per_category_pr31_vs_cms_data.png")
    manifest["examples"] = plot_examples(roots["rare4"], out_dir / "3_example_histograms.png")
    manifest["overlap"] = plot_overlap_effect(
        roots["pr31"], roots["pr31_noOR"], out_dir / "4_overlap_removal_effect.png")
    (out_dir / "plots_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {out_dir}/plots_manifest.json")


if __name__ == "__main__":
    main()
