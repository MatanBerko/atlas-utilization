#!/usr/bin/env python
"""
Full-run preparation (17 Oct 2026), Part B2 finding: why 4 sparse ggH
histograms changed beyond the expected x0.99167 scale.

For every ggH histogram whose recorded peak_mass differs between the 10 Oct
and 17 Oct build reports, rebuild its (masses, weights) from each build's
kept scratch shards with the builder's OWN functions, then show the weighted
counts in the bins tied (or near-tied) for the maximum, how far apart they
are in units of float64 round-off, and where the builder's find_peak_mass
puts the peak on each side.

Reads local copies only (the shards are opened read-only by the builder's
reader). Writes one JSON.

Run:
    python studies/cms_mc_weights_v3/fullrun_prep/diagnose_peak_flips.py \
        --old-scratch <dir> --new-scratch <dir> \
        --old-report <json> --new-report <json> --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from studies.cms_mc_weights_v3.deliver import build_mc_delivery as B  # noqa: E402


def per_hist(report: dict) -> dict:
    s = report["samples"]["37728"]
    for v in s.values():
        if isinstance(v, dict) and "per_histogram" in v:
            return v["per_histogram"]
    raise SystemExit("no per_histogram in the report")


def arrays_for(shards: list, name: str) -> tuple[np.ndarray, np.ndarray, str]:
    masses = B.collect_signature_arrays(shards)
    weights = B.collect_signature_arrays(shards, B.MC_WEIGHT_SUFFIX)
    acc = B.collect_signature_arrays(shards, B.MC_SIBLING_ACCEPTANCE)
    mm, ww, im = [], [], None
    for sig in sorted(masses):
        fs, im_str = B.SIG_PATTERN.search(sig).groups()
        if B._convert_to_bumpnet_name(fs, im_str) != name:
            continue
        im = im_str
        m = np.concatenate([np.asarray(c, dtype=np.float64) for c in masses[sig]])
        w = np.concatenate([np.asarray(c, dtype=np.float64) for c in weights[sig]])
        a = np.concatenate([np.asarray(c) for c in acc[sig]])
        u = B.event_union_mask(a)
        mm.append(m[u])
        ww.append(w[u])
    return np.concatenate(mm), np.concatenate(ww), im


def main() -> int:
    ap = argparse.ArgumentParser()
    for a in ("--old-scratch", "--new-scratch", "--old-report", "--new-report", "--out"):
        ap.add_argument(a, required=True)
    args = ap.parse_args()
    po = per_hist(json.loads(Path(args.old_report).read_text()))
    pn = per_hist(json.loads(Path(args.new_report).read_text()))
    flipped = sorted(k for k in po if po[k].get("peak_mass") != pn.get(k, {}).get("peak_mass"))
    so = sorted(str(p) for p in Path(args.old_scratch).glob("*.sqlite"))
    sn = sorted(str(p) for p in Path(args.new_scratch).glob("*.sqlite"))
    r = 0.013335 / 0.013447
    out = {"n_histograms_in_report": len(po), "flipped": []}
    for name in flipped:
        mo, wo, im = arrays_for(so, name)
        mn, wn, _ = arrays_for(sn, name)
        keep = B.z_peak_keep_mask(mo, f"x_FS_x_IM_{im}") & (mo <= B.MAX_MASS_CUTOFF)
        mo, wo, mn, wn = mo[keep], wo[keep], mn[keep], wn[keep]
        edges = B._aligned_bin_edges(mo, B.BIN_WIDTH_GEV)
        co, _ = np.histogram(mo, bins=edges, weights=wo)
        cn, _ = np.histogram(mn, bins=edges, weights=wn)
        top = np.argsort(-co)[:4]
        rows = []
        for i in sorted(top):
            rows.append({"bin_low_gev": float(edges[i]), "n_entries": int(((mo >= edges[i]) & (mo < edges[i + 1])).sum()),
                         "old_weighted": float(co[i]), "new_weighted": float(cn[i]),
                         "old_minus_old_max_in_ulps": float((co[i] - co.max()) / np.spacing(co.max())),
                         "new_minus_new_max_in_ulps": float((cn[i] - cn.max()) / np.spacing(cn.max()))})
        entry = {
            "histogram": name,
            "masses_identical_old_new": bool(np.array_equal(mo, mn)),
            "max_rel_dev_new_weight_vs_old_times_r": float(np.max(np.abs(wn / (wo * r) - 1))),
            "peak_old_report": po[name]["peak_mass"], "peak_new_report": pn[name]["peak_mass"],
            "peak_old_recomputed": B.find_peak_mass(mo, wo),
            "peak_new_recomputed": B.find_peak_mass(mn, wn),
            "peak_unweighted": B.find_peak_mass(mo, None),
            "entries_kept_old": po[name].get("n_raw_entries"),
            "entries_kept_new": pn[name].get("n_raw_entries"),
            "top_bins": rows,
        }
        out["flipped"].append(entry)
        print(json.dumps(entry, indent=1))
    Path(args.out).write_text(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
