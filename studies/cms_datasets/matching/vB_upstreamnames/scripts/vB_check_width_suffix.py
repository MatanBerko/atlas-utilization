"""
width-suffix task, Step 2: checks on the rebuilt delivery.

Compares the new `_width_10.0` delivery against the current `_width_10` one
(opened read-only), by reading the real ROOT files back:

  1. Exactly the expected number of TH1F histograms in each file (uncropped
     and cropped).
  2. Every name equals the corresponding name in the current delivery with
     `_width_10` replaced by `_width_10.0` and nothing else changed; the
     mapping is one-to-one; no duplicates on either side.
  3. Bin contents, bin edges and total entries identical for every
     histogram, in both the uncropped and the cropped file.
  4. Every name is reproduced exactly by upstream's own naming rule
     (_convert_to_bumpnet_name plus upstream's ROI_/width f-string) from the
     final-state and combination parts the name itself carries.
  5. Each histogram's internal ROOT name equals its key name in the file.

Usage:
    python vB_check_width_suffix.py --old-dir <current delivery dir> \
        --new-dir <new delivery dir> [--expect 1496] [--json <out>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.histograms import BIN_WIDTH_GEV  # noqa: E402
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name  # noqa: E402

OLD_SUFFIX = "_width_10"
NEW_SUFFIX = "_width_10.0"

FAILURES = []
RESULTS = {}


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)
    return bool(condition)


def upstream_hist_name(hist_name_base: str, bin_width) -> str:
    """Verbatim from upstream services/pipelines/histograms_pipeline.py at
    commit 88d7a4b: hist_name = f"ROI_{hist_name_base}_width_{bin_width}"."""
    return f"ROI_{hist_name_base}_width_{bin_width}"


def load(path: Path):
    """key -> (values, edges, internal_name, classname). Read back from the
    real file, not from anything the builder remembered."""
    out = {}
    with uproot.open(str(path)) as f:
        for key in f.keys():
            name = key.split(";")[0]
            obj = f[key]
            try:
                internal = obj.member("fName")
            except Exception:
                internal = None
            out[name] = (
                np.asarray(obj.values(), dtype=float),
                np.asarray(obj.axis().edges(), dtype=float),
                internal,
                obj.classname,
            )
    return out


def compare_pair(tag: str, old_path: Path, new_path: Path, expect: int):
    print(f"\n{'=' * 74}\n{tag}\n{'=' * 74}")
    old = load(old_path)
    new = load(new_path)
    print(f"  current ({old_path.name}): {len(old)} histograms")
    print(f"  new     ({new_path.name}): {len(new)} histograms")

    # ---- 1. counts and class ----
    check(f"{tag}: new file holds exactly {expect} histograms", len(new) == expect,
          f"got {len(new)}")
    check(f"{tag}: current file holds exactly {expect} histograms", len(old) == expect,
          f"got {len(old)}")
    bad_class = sorted(k for k, v in new.items() if v[3] != "TH1F")
    check(f"{tag}: every histogram in the new file is a TH1F", not bad_class,
          f"{len(bad_class)} are not: {bad_class[:3]}")

    # ---- 2. names ----
    bad_suffix = sorted(k for k in new if not k.endswith(NEW_SUFFIX))
    check(f"{tag}: every new name ends with {NEW_SUFFIX}", not bad_suffix,
          f"{len(bad_suffix)}: {bad_suffix[:3]}")
    old_bad = sorted(k for k in old if not k.endswith(OLD_SUFFIX))
    check(f"{tag}: every current name ends with {OLD_SUFFIX} (so the comparison is "
          f"meaningful)", not old_bad, f"{len(old_bad)}: {old_bad[:3]}")

    # expected new name = old name with the suffix swapped, nothing else
    expected = {}
    for k in old:
        expected[k[: -len(OLD_SUFFIX)] + NEW_SUFFIX] = k
    check(f"{tag}: swapping the suffix on the current names yields {len(expected)} "
          f"distinct names (one-to-one, no collisions)",
          len(expected) == len(old), f"{len(old)} -> {len(expected)}")
    check(f"{tag}: no duplicate keys in the new file", len(set(new)) == len(new))

    only_new = sorted(set(new) - set(expected))
    only_old = sorted(set(expected) - set(new))
    check(f"{tag}: the new names are exactly the swapped current names",
          not only_new and not only_old,
          f"{len(only_new)} unexpected new, {len(only_old)} missing; "
          f"new={only_new[:2]} missing={only_old[:2]}")

    # and nothing but the suffix changed
    bad_body = sorted(k for k in new
                      if k in expected
                      and k[: -len(NEW_SUFFIX)] != expected[k][: -len(OLD_SUFFIX)])
    check(f"{tag}: nothing but the width suffix differs in any name", not bad_body,
          f"{len(bad_body)}: {bad_body[:3]}")

    # ---- 3. contents ----
    bad_vals, bad_edges, bad_entries = [], [], []
    for k_new, k_old in expected.items():
        if k_new not in new:
            continue
        nv, ne, _n, _c = new[k_new]
        ov, oe, _n2, _c2 = old[k_old]
        if nv.shape != ov.shape or not np.array_equal(nv, ov):
            bad_vals.append(k_new)
            continue
        if ne.shape != oe.shape or not np.allclose(ne, oe, rtol=0, atol=1e-12):
            bad_edges.append(k_new)
            continue
        if float(nv.sum()) != float(ov.sum()):
            bad_entries.append(k_new)
    check(f"{tag}: bin contents identical for all {len(expected)} histograms",
          not bad_vals, f"{len(bad_vals)} differ: {bad_vals[:3]}")
    check(f"{tag}: bin edges identical for all {len(expected)} histograms",
          not bad_edges, f"{len(bad_edges)} differ: {bad_edges[:3]}")
    check(f"{tag}: total entries identical for all {len(expected)} histograms",
          not bad_entries, f"{len(bad_entries)} differ: {bad_entries[:3]}")

    # ---- 4. upstream re-derivation ----
    bad_rebuild = []
    for k in new:
        body = k[: -len(NEW_SUFFIX)]
        if not body.startswith("ROI_mass_") or "_cat_" not in body:
            bad_rebuild.append((k, "unexpected shape"))
            continue
        combo = body[len("ROI_mass_"):].split("_cat_", 1)[0]
        cat = body.split("_cat_", 1)[1]
        plain_fs = "_".join(f[:-1] if f.endswith("x") else f for f in cat.split("_"))
        rebuilt = upstream_hist_name(
            _convert_to_bumpnet_name(plain_fs, combo), BIN_WIDTH_GEV)
        if rebuilt != k:
            bad_rebuild.append((k, rebuilt))
    check(f"{tag}: every name is exactly what upstream's own rule produces from its "
          f"own parts", not bad_rebuild, f"{len(bad_rebuild)}: {bad_rebuild[:3]}")

    # ---- 5. internal name vs key name ----
    mismatched = [(k, v[2]) for k, v in new.items() if v[2] != k]
    check(f"{tag}: each histogram's internal ROOT name equals its key name",
          not mismatched, f"{len(mismatched)} differ: {mismatched[:3]}")
    if mismatched:
        print(f"       REPORTED: {len(mismatched)} internal/key name mismatches")

    total_new = sum(float(v[0].sum()) for v in new.values())
    total_old = sum(float(v[0].sum()) for v in old.values())
    print(f"       total entries: current={total_old:,.0f}  new={total_new:,.0f}")
    check(f"{tag}: total entries across the whole file identical",
          total_new == total_old, f"{total_old} vs {total_new}")

    RESULTS[tag] = {
        "n_old": len(old), "n_new": len(new),
        "n_not_th1f": len(bad_class),
        "n_name_mismatch": len(only_new) + len(only_old),
        "n_body_differs": len(bad_body),
        "n_values_differ": len(bad_vals), "n_edges_differ": len(bad_edges),
        "n_entries_differ": len(bad_entries),
        "n_rebuild_mismatch": len(bad_rebuild),
        "n_internal_name_mismatch": len(mismatched),
        "total_entries_old": total_old, "total_entries_new": total_new,
        "example_old": sorted(old)[0], "example_new": sorted(new)[0],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old-dir", required=True)
    p.add_argument("--new-dir", required=True)
    p.add_argument("--expect", type=int, default=1496)
    p.add_argument("--json")
    args = p.parse_args()

    old_dir, new_dir = Path(args.old_dir), Path(args.new_dir)
    pairs = [
        ("UNCROPPED",
         old_dir / "muon_combined_matched_vB_upstreamnames_bumpnet.root",
         new_dir / "muon_combined_matched_vB_upstreamnames_w10p0_bumpnet.root"),
        ("CROPPED",
         old_dir / "muon_combined_matched_vB_upstreamnames_bumpnet_cropped.root",
         new_dir / "muon_combined_matched_vB_upstreamnames_w10p0_bumpnet_cropped.root"),
    ]
    for tag, o, n in pairs:
        compare_pair(tag, o, n, args.expect)

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"failures": FAILURES, "results": RESULTS}, indent=2, default=str))
        print(f"\nwrote {args.json}")

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL WIDTH-SUFFIX CHECKS PASSED")


if __name__ == "__main__":
    main()
