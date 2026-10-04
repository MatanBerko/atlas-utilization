#!/usr/bin/env python
"""
Step 8 (ttbar_count_vs_atlas): side-by-side comparison of an ATLAS BumpNet
histogram file against one of ours.

Given an ATLAS BumpNet ROOT file and one of our study/delivery ROOT files,
this normalises the two naming conventions onto a common form and prints
(and writes as JSON) the category and histogram lists split three ways:
in BOTH, ATLAS ONLY, CMS ONLY -- with per-category histogram counts.

NAMING
------
Both sides name a histogram `mass_<combination>_cat_<final state>`, but the
final-state part is written differently:

  ATLAS (as reported by Maryna):  mass_e0m0_cat_1e_2m_3j_1b
  ours:                           mass_e0m0_cat_1ex_2mx_3jx_0gx_0tx_1bx
  ours, inside a ROOT file:       ROI_mass_e0m0_cat_1ex_..._1bx_width_10

Three differences, all handled here:
  1. our ROOT keys carry a `ROI_` prefix and a `_width_<N>` suffix;
  2. our final-state tokens carry a trailing `x` (`2mx` vs `2m`);
  3. we always write all six object types including the zero counts
     (`0gx`, `0tx`); the ATLAS side writes only the types present.

Normalisation therefore parses the final state into per-letter counts and
re-emits the canonical six-type form `<e>e_<m>m_<j>j_<g>g_<t>t_<b>b`, so
`1e_2m_3j_1b` and `1ex_2mx_3jx_0gx_0tx_1bx` both become `1e_2m_3j_0g_0t_1b`.
A missing type is read as zero -- which is what it means on the ATLAS side.
The combination part is left verbatim (both sides build it with the same
PARTICLE_ORDER code) but is additionally canonicalised, by sorting its
letter+rank tokens, for the comparison itself, so that an ordering
difference between the two writers could never masquerade as a missing
histogram.

Nothing here is specific to a particular ATLAS file: it reads whatever
TH1-like keys the file has.

Usage:
    python compare_with_atlas.py --atlas <atlas.root> --cms <ours.root> \
        --out-json <report.json> [--out-md <report.md>] \
        [--atlas-label ATLAS] [--cms-label CMS]

Self-test (no ATLAS file needed):
    python compare_with_atlas.py --self-test --cms <ours.root> --out-json <report.json>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import uproot

# Canonical object order; the same six types, in the same order, that
# services.calculations.consts.LETTER_PARTICLE_MAPPING covers and that our
# own final-state strings are built in.
LETTERS = ("e", "m", "j", "g", "t", "b")

# One final-state token: a count, a type letter, and an optional trailing
# "x" (our convention) -- e.g. "2m" or "2mx".
_FS_TOKEN = re.compile(r"^(\d+)([emjgtb])x?$")
# One combination token: a type letter plus a rank index -- e.g. "e0", "j1".
_IM_TOKEN = re.compile(r"([emjgtb])(\d+)")


def strip_root_key(key: str) -> str:
    """ROOT key -> bare histogram name.

    Drops the cycle suffix uproot appends (`;1`), our `ROI_` prefix and our
    `_width_<N>` suffix. A name that has none of those is returned as-is,
    which is what lets the same function read an ATLAS file.
    """
    name = key.split(";")[0]
    if name.startswith("ROI_"):
        name = name[len("ROI_"):]
    name = re.sub(r"_width_\d+$", "", name)
    return name


def parse_name(name: str):
    """`mass_<combo>_cat_<fs>` -> (canonical_category, canonical_combo).

    Returns (None, None) for a name that does not follow the convention,
    so an unexpected key in either file is reported rather than crashing
    the comparison.
    """
    if not name.startswith("mass_") or "_cat_" not in name:
        return None, None
    body = name[len("mass_"):]
    combo_str, fs_str = body.split("_cat_", 1)

    counts = {letter: 0 for letter in LETTERS}
    for token in fs_str.split("_"):
        m = _FS_TOKEN.match(token)
        if not m:
            return None, None
        count, letter = m.groups()
        # A repeated type would make the final state ambiguous.
        counts[letter] = max(counts[letter], int(count))
    category = "_".join(f"{counts[letter]}{letter}" for letter in LETTERS)

    im_tokens = _IM_TOKEN.findall(combo_str)
    if not im_tokens:
        # "none" is the documented empty-combination spelling.
        combo = combo_str
    else:
        combo = "".join(f"{letter}{rank}" for letter, rank in sorted(im_tokens))
    return category, combo


def read_file(path: str) -> dict:
    """{histogram_key: (category, combo, n_filled_bins, n_events)}.

    Only TH1-like objects are read; anything else in the file is listed
    under "skipped" by the caller.
    """
    out = {}
    unparsed = []
    with uproot.open(path) as f:
        for key in sorted(set(k.split(";")[0] for k in f.keys())):
            obj = f[key]
            if not hasattr(obj, "values"):
                continue
            name = strip_root_key(key)
            category, combo = parse_name(name)
            if category is None:
                unparsed.append(key)
                continue
            values = np.asarray(obj.values())
            out[(category, combo)] = {
                "root_key": key,
                "name": name,
                "category": category,
                "combination": combo,
                "n_filled_bins": int(np.count_nonzero(values)),
                "n_events": float(values.sum()),
            }
    return out, unparsed


def summarise(entries: dict) -> dict:
    per_cat = defaultdict(int)
    for (category, _combo) in entries:
        per_cat[category] += 1
    return dict(per_cat)


def compare(atlas: dict, cms: dict, atlas_label: str, cms_label: str) -> dict:
    atlas_keys, cms_keys = set(atlas), set(cms)
    both_keys = atlas_keys & cms_keys

    atlas_cats = summarise(atlas)
    cms_cats = summarise(cms)
    all_cats = sorted(set(atlas_cats) | set(cms_cats))

    per_category = []
    for cat in all_cats:
        n_a = atlas_cats.get(cat, 0)
        n_c = cms_cats.get(cat, 0)
        shared = len({k for k in both_keys if k[0] == cat})
        per_category.append({
            "category": cat,
            f"n_histograms_{atlas_label}": n_a,
            f"n_histograms_{cms_label}": n_c,
            "n_histograms_in_both": shared,
            "where": ("both" if n_a and n_c else (atlas_label if n_a else cms_label)),
        })

    def names(keys, src):
        return sorted(src[k]["name"] for k in keys)

    return {
        "labels": {"atlas": atlas_label, "cms": cms_label},
        "n_histograms": {atlas_label: len(atlas_keys), cms_label: len(cms_keys),
                         "both": len(both_keys),
                         f"{atlas_label}_only": len(atlas_keys - cms_keys),
                         f"{cms_label}_only": len(cms_keys - atlas_keys)},
        "n_categories": {atlas_label: len(atlas_cats), cms_label: len(cms_cats),
                         "both": len(set(atlas_cats) & set(cms_cats)),
                         f"{atlas_label}_only": len(set(atlas_cats) - set(cms_cats)),
                         f"{cms_label}_only": len(set(cms_cats) - set(atlas_cats))},
        "categories_in_both": sorted(set(atlas_cats) & set(cms_cats)),
        f"categories_{atlas_label}_only": sorted(set(atlas_cats) - set(cms_cats)),
        f"categories_{cms_label}_only": sorted(set(cms_cats) - set(atlas_cats)),
        "histograms_in_both": sorted(atlas[k]["name"] for k in both_keys),
        f"histograms_{atlas_label}_only": names(atlas_keys - cms_keys, atlas),
        f"histograms_{cms_label}_only": names(cms_keys - atlas_keys, cms),
        "per_category": per_category,
    }


def write_md(report: dict, path: Path, atlas_label: str, cms_label: str):
    L = []
    L.append(f"# {atlas_label} vs {cms_label}: categories and histograms")
    L.append("")
    nh, nc = report["n_histograms"], report["n_categories"]
    L.append("| quantity | " + atlas_label + " | " + cms_label + " | both | "
             + f"{atlas_label} only | {cms_label} only |")
    L.append("|---|---:|---:|---:|---:|---:|")
    L.append(f"| histograms | {nh[atlas_label]} | {nh[cms_label]} | {nh['both']} | "
             f"{nh[atlas_label + '_only']} | {nh[cms_label + '_only']} |")
    L.append(f"| categories | {nc[atlas_label]} | {nc[cms_label]} | {nc['both']} | "
             f"{nc[atlas_label + '_only']} | {nc[cms_label + '_only']} |")
    L.append("")
    L.append("## Per-category histogram counts")
    L.append("")
    L.append(f"| category (e_m_j_g_t_b) | {atlas_label} | {cms_label} | in both | where |")
    L.append("|---|---:|---:|---:|---|")
    for row in report["per_category"]:
        L.append(f"| `{row['category']}` | {row[f'n_histograms_{atlas_label}']} | "
                 f"{row[f'n_histograms_{cms_label}']} | {row['n_histograms_in_both']} | "
                 f"{row['where']} |")
    L.append("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def make_synthetic_atlas_file(path: Path, source_entries: dict, n_keep: int = 12):
    """A small ATLAS-STYLE file for the self-test.

    Takes a handful of our own category/combination pairs, re-spells them
    in the ATLAS convention (no `ROI_`/`_width_`, no trailing `x`, zero-count
    types omitted) and adds two categories that exist only on the ATLAS
    side -- so the self-test exercises the normaliser rather than merely
    round-tripping our own strings.
    """
    import uproot as _uproot
    picked = sorted(source_entries)[:n_keep]
    atlas_names = []
    for (category, combo) in picked:
        counts = {token[-1]: int(token[:-1]) for token in category.split("_")}
        present = "_".join(f"{counts[letter]}{letter}" for letter in LETTERS
                           if counts[letter] > 0)
        atlas_names.append(f"mass_{combo}_cat_{present}")
    # Two ATLAS-only categories (3 taus / 2 photons never occur on our side:
    # taus and photons are not read at all by the CMS pipeline).
    atlas_names.append("mass_t0t1_cat_0e_0m_0j_0g_3t_0b")
    atlas_names.append("mass_g0g1_cat_0e_0m_0j_2g_0t_0b")

    edges = np.arange(0.0, 1000.0 + 10.0, 10.0)
    with _uproot.recreate(str(path)) as fout:
        for i, name in enumerate(atlas_names):
            values = np.zeros(len(edges) - 1, dtype=np.float32)
            values[: 30 + i] = 5.0
            fout[name] = (values, edges)
    return atlas_names


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--atlas", help="ATLAS BumpNet ROOT file")
    p.add_argument("--cms", required=True, help="our BumpNet ROOT file")
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-md")
    p.add_argument("--atlas-label", default="ATLAS")
    p.add_argument("--cms-label", default="CMS")
    p.add_argument("--self-test", action="store_true",
                   help="run the two built-in checks (CMS file against itself, and "
                        "against a synthetic ATLAS-style file made from it) instead of "
                        "comparing against a real ATLAS file")
    args = p.parse_args()

    cms_entries, cms_unparsed = read_file(args.cms)
    print(f"{args.cms_label}: {len(cms_entries)} histograms, "
          f"{len(summarise(cms_entries))} categories "
          f"({len(cms_unparsed)} keys not in mass_<combo>_cat_<fs> form)")

    if args.self_test:
        results = {}

        # Check 1: our own file against itself -- everything must be shared.
        r1 = compare(cms_entries, cms_entries, args.atlas_label, args.cms_label)
        ok1 = (r1["n_histograms"][f"{args.atlas_label}_only"] == 0
               and r1["n_histograms"][f"{args.cms_label}_only"] == 0
               and r1["n_histograms"]["both"] == len(cms_entries)
               and r1["n_categories"][f"{args.atlas_label}_only"] == 0
               and r1["n_categories"][f"{args.cms_label}_only"] == 0)
        print(f"self-test 1 (own file against itself): {'PASS' if ok1 else 'FAIL'} "
              f"-- {r1['n_histograms']['both']} shared, "
              f"{r1['n_histograms'][f'{args.atlas_label}_only']} + "
              f"{r1['n_histograms'][f'{args.cms_label}_only']} unmatched")
        results["self_test_1_identity"] = {"pass": ok1, "summary": r1["n_histograms"]}

        # Check 2: a synthetic ATLAS-style file built from our own names,
        # re-spelled in the ATLAS convention, plus 2 ATLAS-only categories.
        synth_path = Path(args.out_json).with_suffix(".synthetic_atlas.root")
        atlas_names = make_synthetic_atlas_file(synth_path, cms_entries)
        atlas_entries, atlas_unparsed = read_file(str(synth_path))
        r2 = compare(atlas_entries, cms_entries, args.atlas_label, args.cms_label)
        n_resp = len(atlas_names) - 2
        ok2 = (len(atlas_unparsed) == 0
               and r2["n_histograms"]["both"] == n_resp
               and r2["n_histograms"][f"{args.atlas_label}_only"] == 2)
        print(f"self-test 2 (synthetic ATLAS-style file, {len(atlas_names)} histograms: "
              f"{n_resp} re-spelled from ours + 2 ATLAS-only): "
              f"{'PASS' if ok2 else 'FAIL'} -- matched {r2['n_histograms']['both']}/{n_resp}, "
              f"ATLAS-only {r2['n_histograms'][f'{args.atlas_label}_only']}")
        results["self_test_2_synthetic_atlas"] = {
            "pass": ok2,
            "synthetic_file": str(synth_path),
            "n_synthetic_histograms": len(atlas_names),
            "n_respelled_from_ours": n_resp,
            "summary": r2["n_histograms"],
            "atlas_only_categories": r2[f"categories_{args.atlas_label}_only"],
        }

        results["overall_pass"] = bool(ok1 and ok2)
        Path(args.out_json).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nSELF-TEST OVERALL: {'PASS' if results['overall_pass'] else 'FAIL'}")
        print(f"wrote {args.out_json}")
        sys.exit(0 if results["overall_pass"] else 1)

    if not args.atlas:
        p.error("--atlas is required unless --self-test is given")

    atlas_entries, atlas_unparsed = read_file(args.atlas)
    print(f"{args.atlas_label}: {len(atlas_entries)} histograms, "
          f"{len(summarise(atlas_entries))} categories "
          f"({len(atlas_unparsed)} keys not in mass_<combo>_cat_<fs> form)")

    report = compare(atlas_entries, cms_entries, args.atlas_label, args.cms_label)
    report["atlas_file"] = args.atlas
    report["cms_file"] = args.cms
    report["unparsed_keys"] = {args.atlas_label: atlas_unparsed, args.cms_label: cms_unparsed}
    Path(args.out_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.out_md:
        write_md(report, Path(args.out_md), args.atlas_label, args.cms_label)

    nh, nc = report["n_histograms"], report["n_categories"]
    print(f"\nhistograms: {args.atlas_label}={nh[args.atlas_label]} "
          f"{args.cms_label}={nh[args.cms_label]} both={nh['both']} "
          f"{args.atlas_label}_only={nh[args.atlas_label + '_only']} "
          f"{args.cms_label}_only={nh[args.cms_label + '_only']}")
    print(f"categories: {args.atlas_label}={nc[args.atlas_label]} "
          f"{args.cms_label}={nc[args.cms_label]} both={nc['both']} "
          f"{args.atlas_label}_only={nc[args.atlas_label + '_only']} "
          f"{args.cms_label}_only={nc[args.cms_label + '_only']}")
    print(f"wrote {args.out_json}" + (f" and {args.out_md}" if args.out_md else ""))


if __name__ == "__main__":
    main()
