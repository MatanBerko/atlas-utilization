#!/usr/bin/env python
"""
m0m1j0 CMS histogram -- verifies that fixing the x-axis DISPLAY range
(matching services/pipelines/histograms_pipeline.py's trim_empty_tail,
see histograms.py's own derivation) changed NOTHING else: for every
histogram in every regenerated ROOT file, bin contents (and bin edges)
must equal the file as committed BEFORE the fix, byte-for-byte in value;
for every merge summary JSON, every per-category count must be unchanged.

Run AFTER re-running the existing merge steps (merge_full_v2.py,
merge_ttbar.py, merge_variants.py) from the per-job outputs already on
disk -- this script does not run any merge or analysis step itself, it
only compares.

"Before" content is read directly from git history at --before-commit
(the tip before this fix's own commits) via `git show <commit>:<path>`,
piped to a temp file and opened with uproot/json -- never by trusting
whatever happens to be checked out; "after" content is read from the
current working tree (the just-regenerated files).

Usage:
    python check_display_range_fix_preserves_content.py --before-commit bf7f5f7
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

ROOT_FILES = [
    "studies/m0m1j0_cms/v2/data/m0m1j0_data_postprocessed.root",
    "studies/m0m1j0_cms/v2/ttbar/m0m1j0_ttbar_postprocessed.root",
    "studies/m0m1j0_cms/v2/ttbar/m0m1j0_ttbar_postprocessed_weighted.root",
    "studies/m0m1j0_cms/v3_variants/data_V0_baseline.root",
    "studies/m0m1j0_cms/v3_variants/data_V1_no_muon_iso.root",
    "studies/m0m1j0_cms/v3_variants/data_V2_no_jet_lepton_cleaning.root",
    "studies/m0m1j0_cms/v3_variants/data_V3_single_muon_trigger.root",
    "studies/m0m1j0_cms/v3_variants/ttbar_V0_baseline.root",
    "studies/m0m1j0_cms/v3_variants/ttbar_V1_no_muon_iso.root",
    "studies/m0m1j0_cms/v3_variants/ttbar_V2_no_jet_lepton_cleaning.root",
    "studies/m0m1j0_cms/v3_variants/ttbar_V3_single_muon_trigger.root",
]

# (path, dotted-path-to-the-per-category-count-dict, count-field-name(s) to compare)
JSON_CATEGORY_CHECKS = [
    ("studies/m0m1j0_cms/v2/data/merge_v2_summary.json", ["per_category"],
     ("n_raw", "n_after_z_peak", "n_after_max_mass", "peak_mass", "n_after_peak_removal",
      "split_mass", "n_main", "n_outliers", "pruned_by_min_events_per_fs")),
    ("studies/m0m1j0_cms/v2/ttbar/merge_ttbar_summary.json", ["per_category"],
     ("n_raw", "n_after_z_peak", "n_after_max_mass", "peak_mass", "n_after_peak_removal",
      "split_mass", "n_main", "n_outliers", "pruned_by_min_events_per_fs")),
]
for _sample in ("data", "ttbar"):
    for _variant in ("V0_baseline", "V1_no_muon_iso", "V2_no_jet_lepton_cleaning", "V3_single_muon_trigger"):
        JSON_CATEGORY_CHECKS.append((
            f"studies/m0m1j0_cms/v3_variants/merge_variants_{_sample}_summary.json",
            ["per_variant", _variant, "per_category"],
            ("n_raw", "n_after_z_peak", "n_after_max_mass", "peak_mass", "n_after_peak_removal",
             "split_mass", "n_main", "n_outliers", "pruned_by_min_events_per_fs"),
        ))


def git_show(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=str(REPO_ROOT))


def load_histograms(root_path) -> dict:
    f = uproot.open(root_path)
    out = {}
    for key in f.keys(cycle=False):
        h = f[key]
        out[key] = (h.values(), h.axis().edges())
    return out


def compare_root_file(before_commit: str, rel_path: str, problems: list) -> int:
    n_checked = 0
    try:
        before_bytes = git_show(before_commit, rel_path)
    except subprocess.CalledProcessError as e:
        problems.append(f"{rel_path}: could not read from {before_commit} -- {e}")
        return 0

    after_path = REPO_ROOT / rel_path
    if not after_path.exists():
        problems.append(f"{rel_path}: does not exist in the working tree (after regeneration)")
        return 0

    with tempfile.NamedTemporaryFile(suffix=".root", delete=False) as tmp:
        tmp.write(before_bytes)
        before_path = tmp.name

    before_hists = load_histograms(before_path)
    after_hists = load_histograms(str(after_path))

    if set(before_hists) != set(after_hists):
        problems.append(
            f"{rel_path}: histogram key set changed -- "
            f"only-before={sorted(set(before_hists) - set(after_hists))}, "
            f"only-after={sorted(set(after_hists) - set(before_hists))}"
        )

    for key in sorted(set(before_hists) & set(after_hists)):
        b_values, b_edges = before_hists[key]
        a_values, a_edges = after_hists[key]
        n_checked += 1
        if not np.array_equal(b_edges, a_edges):
            problems.append(f"{rel_path}::{key}: bin EDGES changed")
            continue
        if not np.array_equal(b_values, a_values):
            max_diff = float(np.max(np.abs(a_values.astype(np.float64) - b_values.astype(np.float64))))
            problems.append(f"{rel_path}::{key}: bin CONTENT changed (max abs diff {max_diff:.6g})")
    return n_checked


def _dig(d: dict, path: list):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def compare_json_categories(before_commit: str, rel_path: str, dig_path: list, fields: tuple, problems: list) -> int:
    n_checked = 0
    try:
        before_json = json.loads(git_show(before_commit, rel_path))
    except subprocess.CalledProcessError as e:
        problems.append(f"{rel_path}: could not read from {before_commit} -- {e}")
        return 0

    after_path = REPO_ROOT / rel_path
    if not after_path.exists():
        problems.append(f"{rel_path}: does not exist in the working tree (after regeneration)")
        return 0
    after_json = json.loads(after_path.read_text(encoding="utf-8"))

    before_cat = _dig(before_json, dig_path)
    after_cat = _dig(after_json, dig_path)
    if before_cat is None or after_cat is None:
        problems.append(f"{rel_path}: path {dig_path} not found in before or after JSON")
        return 0

    if set(before_cat) != set(after_cat):
        problems.append(
            f"{rel_path}[{'/'.join(dig_path)}]: category set changed -- "
            f"only-before={sorted(set(before_cat) - set(after_cat))}, "
            f"only-after={sorted(set(after_cat) - set(before_cat))}"
        )

    for cat in sorted(set(before_cat) & set(after_cat)):
        n_checked += 1
        b = before_cat[cat]
        a = after_cat[cat]
        for field in fields:
            if field not in b and field not in a:
                continue
            if b.get(field) != a.get(field):
                problems.append(
                    f"{rel_path}[{'/'.join(dig_path)}][{cat}].{field}: "
                    f"before={b.get(field)!r} after={a.get(field)!r}"
                )
    return n_checked


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--before-commit", required=True)
    args = p.parse_args()

    problems: list = []
    total_hists_checked = 0
    for rel_path in ROOT_FILES:
        n = compare_root_file(args.before_commit, rel_path, problems)
        total_hists_checked += n
        print(f"{rel_path}: {n} histogram(s) compared")

    total_cats_checked = 0
    for rel_path, dig_path, fields in JSON_CATEGORY_CHECKS:
        n = compare_json_categories(args.before_commit, rel_path, dig_path, fields, problems)
        total_cats_checked += n
        print(f"{rel_path}[{'/'.join(dig_path)}]: {n} categor(y/ies) compared")

    print()
    print(f"TOTAL histograms compared: {total_hists_checked}")
    print(f"TOTAL categories compared: {total_cats_checked}")
    print()
    if problems:
        print(f"{len(problems)} PROBLEM(S) FOUND -- bin content or category counts CHANGED:")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    else:
        print("RESULT: PASS -- every histogram's bin contents and edges, and every category's "
              "post-processing counts, are UNCHANGED between the before-commit and the "
              "regenerated files. Only the x-axis display range metadata differs.")


if __name__ == "__main__":
    main()
