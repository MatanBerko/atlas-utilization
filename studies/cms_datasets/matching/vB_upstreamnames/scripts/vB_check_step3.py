"""
upstream-names task, Step 3: checks on the rebuilt full muon delivery.

Compares the new delivery against the 5 Oct one (opened read-only):

  1. Every one of the 5 Oct delivery's histograms appears in the new file
     under its CONVERTED name, with identical bin contents and bin edges.
  2. The only additional histograms are the ones the 5 Oct build excluded
     solely by its per-histogram >=100-entries rule -- identified by name
     from the 5 Oct build summary's own exclusion list, not by assumption.
     Those among them with zero surviving entries must stay out, because
     upstream does not write an empty histogram either.
  3. Every delivered name matches the upstream format exactly: a
     mass_<combo>_cat_ prefix, every category field <count><letter>x, and
     only the configured object types e, m, j, b -- no photon or tau field.
  4. No duplicate names.
  5. Final-state count, and (information only) how many histograms have
     >=25 filled bins.

Usage:
    python vB_check_step3.py --old-dir <5 Oct delivery dir> \
        --new-dir <new delivery dir> [--json <out>]
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

from studies.cms_datasets.deliver.build_muon_combined_delivery import (  # noqa: E402
    convert_legacy_fs_label,
)
from studies.m0m1j0_cms.histograms import _convert_to_bumpnet_name  # noqa: E402

FAILURES = []
ALLOWED_LETTERS = ("e", "m", "j", "b")
CAT_FIELD = re.compile(r"^(\d+)([emjgtb])x$")


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)
    return bool(condition)


def load(path: Path) -> dict:
    out = {}
    with uproot.open(str(path)) as f:
        for key in f.keys():
            out[key.split(";")[0]] = (
                np.asarray(f[key].values(), dtype=float),
                np.asarray(f[key].axis().edges(), dtype=float),
            )
    return out


def strip_width(key: str):
    for marker in ("_width_10", "_width_10.0"):
        if key.endswith(marker):
            return key[: -len(marker)], marker
    return key, ""


def convert_root_key(key: str) -> str:
    body, suffix = strip_width(key)
    head, rest = body.split("_cat_", 1)
    plain = "_".join(f[:-1] if f.endswith("x") else f for f in rest.split("_"))
    converted = convert_legacy_fs_label(plain)
    return f"{head}_cat_" + "_".join(f"{t}x" for t in converted.split("_")) + suffix


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old-dir", required=True)
    p.add_argument("--new-dir", required=True)
    p.add_argument("--json")
    args = p.parse_args()

    old_dir, new_dir = Path(args.old_dir), Path(args.new_dir)
    old_root = old_dir / "muon_combined_matched_vB_exactlabels_bumpnet.root"
    new_root = new_dir / "muon_combined_matched_vB_upstreamnames_bumpnet.root"
    old_summary = json.loads(
        (old_dir / "build_summary_rare4_nobincut.json").read_text())

    old = load(old_root)
    new = load(new_root)
    print(f"5 Oct delivery: {len(old)} histograms")
    print(f"new delivery:   {len(new)} histograms")

    # ---------------- 1. every 5 Oct histogram reappears, identical ----------
    print("\n--- 1. Every 5 Oct histogram reappears under its converted name ---")
    converted = {}
    collisions = []
    for k, v in old.items():
        ck = convert_root_key(k)
        if ck in converted:
            collisions.append((ck, k))
        converted[ck] = v
    check("converting the 5 Oct names produces no duplicates", not collisions,
          f"{len(collisions)}: {collisions[:2]}")
    check(f"conversion preserves the count ({len(old)})", len(converted) == len(old),
          f"{len(old)} -> {len(converted)}")

    missing = sorted(set(converted) - set(new))
    check(f"all {len(converted)} converted 5 Oct names are present in the new file",
          not missing, f"{len(missing)} missing, first: {missing[:3]}")

    bad_vals, bad_edges = [], []
    for name, (ov, oe) in converted.items():
        if name not in new:
            continue
        nv, ne = new[name]
        if ov.shape != nv.shape or not np.array_equal(ov, nv):
            bad_vals.append(name)
        elif not np.allclose(oe, ne, rtol=0, atol=1e-9):
            bad_edges.append(name)
    check("every reappearing histogram has identical bin contents", not bad_vals,
          f"{len(bad_vals)} differ, first: {bad_vals[:3]}")
    check("every reappearing histogram has identical bin edges", not bad_edges,
          f"{len(bad_edges)} differ, first: {bad_edges[:3]}")

    # ---------------- 2. the additional histograms are the expected ones -----
    print("\n--- 2. The additional histograms are exactly the ones the >=100-entries "
          "rule had excluded ---")
    excluded = old_summary["per_histogram_min_100_entries_rule_UNCHANGED"][
        "names_excluded_at_postprocessing_step"]
    excl_nonzero = {name: n for name, n in excluded if n > 0}
    excl_zero = {name: n for name, n in excluded if n == 0}
    print(f"       5 Oct excluded {len(excluded)} histograms by that rule: "
          f"{len(excl_nonzero)} had >=1 entry, {len(excl_zero)} had none")

    expected_extra = set()
    for name in excl_nonzero:
        fs = name.split("_cat_", 1)[1]
        combo = name[len("mass_"):].split("_cat_")[0]
        expected_extra.add(
            "ROI_" + _convert_to_bumpnet_name(convert_legacy_fs_label(fs), combo)
            + "_width_10")

    extra = set(new) - set(converted)
    check(f"the new file has exactly {len(expected_extra)} additional histograms",
          len(extra) == len(expected_extra),
          f"got {len(extra)}, expected {len(expected_extra)}")
    unexplained = sorted(extra - expected_extra)
    check("every additional histogram is one the >=100-entries rule had excluded",
          not unexplained, f"{len(unexplained)} unexplained, first: {unexplained[:3]}")
    still_missing = sorted(expected_extra - extra)
    check("every previously-excluded histogram with at least one entry is now present",
          not still_missing,
          f"{len(still_missing)} still absent, first: {still_missing[:3]}")

    zero_back = []
    for name in excl_zero:
        fs = name.split("_cat_", 1)[1]
        combo = name[len("mass_"):].split("_cat_")[0]
        k = ("ROI_" + _convert_to_bumpnet_name(convert_legacy_fs_label(fs), combo)
             + "_width_10")
        if k in new:
            zero_back.append(k)
    check("histograms that had NO entries stay out, as upstream would also not "
          "write them", not zero_back, f"{len(zero_back)} came back: {zero_back[:3]}")

    empties = [n for n, (v, _e) in new.items() if v.sum() == 0]
    check("no delivered histogram is empty", not empties,
          f"{len(empties)} empty, first: {empties[:3]}")

    # ---------------- 3 + 4. name format and uniqueness ---------------------
    print("\n--- 3/4. Every name matches the upstream format; no duplicates ---")
    bad_names, bad_fields, gt_names = [], [], []
    for key in new:
        body, suffix = strip_width(key)
        if not suffix or not body.startswith("ROI_mass_") or "_cat_" not in body:
            bad_names.append(key)
            continue
        cat = body.split("_cat_", 1)[1]
        for field in cat.split("_"):
            m = CAT_FIELD.match(field)
            if not m:
                bad_fields.append((key, field))
            elif m.group(2) not in ALLOWED_LETTERS:
                gt_names.append((key, field))
    check("every name has the ROI_mass_<combo>_cat_...  _width_10 shape",
          not bad_names, f"{len(bad_names)}: {bad_names[:3]}")
    check("every category field is <count><letter>x", not bad_fields,
          f"{len(bad_fields)}: {bad_fields[:3]}")
    check("no name carries a photon or tau field", not gt_names,
          f"{len(gt_names)}: {gt_names[:3]}")
    check("no duplicate names", len(set(new)) == len(new))

    # Independent re-derivation: rebuilding each name from its own parts with
    # the same function upstream uses must give the name back unchanged.
    rebuilt_bad = []
    for key in new:
        body, suffix = strip_width(key)
        head, cat = body.split("_cat_", 1)
        combo = head[len("ROI_mass_"):]
        plain = "_".join(f[:-1] for f in cat.split("_"))
        if "ROI_" + _convert_to_bumpnet_name(plain, combo) + suffix != key:
            rebuilt_bad.append(key)
    check("every name is exactly what upstream's own name builder produces for "
          "its parts", not rebuilt_bad, f"{len(rebuilt_bad)}: {rebuilt_bad[:3]}")

    # ---------------- 5. counts -------------------------------------------
    print("\n--- 5. Counts ---")
    old_cats = {k.split("_cat_", 1)[1] for k in converted}
    new_cats = {k.split("_cat_", 1)[1] for k in new}
    print(f"       distinct final states: 5 Oct {len(old_cats)} -> new {len(new_cats)}")
    check("the new delivery contains every 5 Oct final state",
          old_cats <= new_cats,
          f"missing: {sorted(old_cats - new_cats)[:3]}")
    ge25 = sum(1 for v, _e in new.values() if int(np.count_nonzero(v)) >= 25)
    print(f"       histograms with >=25 filled bins (information only): {ge25}")

    result = {
        "n_old": len(old), "n_new": len(new),
        "n_additional": len(extra),
        "n_expected_additional": len(expected_extra),
        "n_excluded_by_old_rule": len(excluded),
        "n_excluded_with_entries": len(excl_nonzero),
        "n_excluded_with_zero_entries": len(excl_zero),
        "n_final_states_old": len(old_cats), "n_final_states_new": len(new_cats),
        "new_final_states": sorted(new_cats - old_cats)[:50],
        "n_with_ge25_filled_bins": ge25,
        "failures": FAILURES,
    }
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2))
        print(f"\nwrote {args.json}")

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL STEP 3 CHECKS PASSED")


if __name__ == "__main__":
    main()
