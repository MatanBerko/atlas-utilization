"""Shared helpers for the peak-fix comparison scripts (18-19 Oct 2026).

Reuses the full run's reader, groups, palette and category definitions
(fullrun/sanity_and_plots.py) so the new plots are drawn exactly like the
old ones; adds a stack drawer that can share an axis with data points."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_mc_weights_v3.fullrun.sanity_and_plots import (  # noqa: E402,F401
    CATEGORIES, GROUPS, GRID, INK, INK2, RECORDS, SURF, parse, read_all, style,
)
from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402,F401

LUMI = B.TARGET_LUMINOSITY_FB


def read_build(build_dir: Path, prefix: str) -> tuple[dict, dict]:
    per = {}
    for rid in RECORDS:
        p = build_dir / f"{prefix}_record{rid}_mc.root"
        per[rid] = read_all(p) if p.exists() else {}
    return per, read_all(build_dir / f"{prefix}_summedSM_mc.root")


def category_names(summed: dict) -> list:
    """[(index, title, histogram name)] -- each category's most-populated
    histogram, the same rule as the full run's stack plots."""
    parsed = {n: parse(n) for n in summed}
    out = []
    for i, (title, pred) in enumerate(CATEGORIES, 1):
        cands = [n for n, d in parsed.items() if d and pred(d)]
        out.append((i, title, max(cands, key=lambda n: summed[n]["entries"]) if cands else None))
    return out


def group_parts(name: str, per: dict, nbins: int) -> list:
    parts = []
    for label, recs, color in GROUPS:
        v = np.zeros(nbins)
        w2 = np.zeros(nbins)
        for r in recs:
            if name in per.get(r, {}):
                v += per[r][name]["values"][1:-1]
                w2 += per[r][name]["variances"][1:-1]
        parts.append((label, color, v, w2))
    return parts


def filled_range(values: np.ndarray):
    nz = np.flatnonzero(values != 0)
    return (int(nz[0]), int(nz[-1])) if nz.size else None


def draw_stack(ax, edges, parts, lo, hi, logy):
    """Stack the groups (smallest at the bottom) over bins [lo, hi)."""
    e = edges[lo:hi + 1]
    base = np.zeros(hi - lo)
    order = sorted(range(len(parts)), key=lambda i: parts[i][2].sum())
    for i in order:
        label, color, v, _w2 = parts[i]
        vv = np.clip(v[lo:hi], 0, None)
        if vv.sum() <= 0:
            continue
        ax.fill_between(np.repeat(e, 2)[1:-1], np.repeat(base, 2), np.repeat(base + vv, 2),
                        color=color, lw=0, label=f"{label}  ({v.sum():,.4g})")
        base = base + vv
    return base
