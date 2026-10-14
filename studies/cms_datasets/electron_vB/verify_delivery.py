#!/usr/bin/env python
"""
Step D2 + D3: read the delivered ROOT files back and check them, then
compare the counts against the muon-only delivery.

D2 -- every check is made against the REAL file, read with uproot:
  * every histogram name is what UPSTREAM's own naming code produces for
    the same (final state, mass combination), including the `_width_10.0`
    ending. Upstream's code is imported from a read-only extract of
    upstream master, never re-implemented.
  * no duplicate names, and every name appears exactly once in the file
    (BumpNet expects one ROOT file per delivery).
  * every final state has >= 100 events summed over its histograms.
  * no histogram is empty.
  * bin edges are exactly 10 GeV over 0-10000 GeV (uncropped). The cropped
    file keeps the same 10 GeV pitch on a trimmed range, which is checked
    as a pitch, not as a range.

D3 -- counts against the muon-only delivery, split by electron content,
and a per-final-state comparison sorted by relative change. Any 0-electron
final state moving by more than 1% is flagged for investigation.

Usage:
    python verify_delivery.py \
        --delivery-dir /storage/.../deliver/four_dataset_..._20261007 \
        --reference /storage/.../muon_combined_..._w10p0_bumpnet_cropped.root \
        --out evidence/D2_D3_delivery_checks.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.m0m1j0_cms.histograms import (  # noqa: E402
    BIN_WIDTH_GEV, FIXED_MASS_MIN_GEV, FIXED_MASS_MAX_GEV,
)

NAME_RE = re.compile(r"^ROI_mass_(?P<im>[0-9a-z]*)_cat_(?P<cat>[0-9a-z_]+)_width_(?P<w>[0-9.]+)$")
CAT_FIELD_RE = re.compile(r"^(\d+)([emjgtb])x$")
MIN_EVENTS_PER_FINAL_STATE = 100
ZERO_ELECTRON_FLAG_PCT = 1.0


def read_histograms(path: Path) -> dict:
    """{name: (values, edges)} plus the raw key list, read-only."""
    out = {}
    keys = []
    with uproot.open(str(path)) as f:
        for key in f.keys():
            name = key.split(";")[0]
            keys.append(name)
            h = f[key]
            out[name] = (h.values(), h.axis().edges())
    return out, keys


def parse_name(name: str):
    m = NAME_RE.match(name)
    if not m:
        return None
    cat = m.group("cat")
    counts = {}
    for field in cat.split("_"):
        fm = CAT_FIELD_RE.match(field)
        if not fm:
            return None
        counts[fm.group(2)] = int(fm.group(1))
    return {"im": m.group("im"), "cat": cat, "counts": counts, "width": m.group("w")}


def final_state_from_cat(cat: str) -> str:
    """`0ex_2mx_5jx_1bx` -> `0e_2m_5j_1b` (the delivery's own final state)."""
    return "_".join(f[:-1] for f in cat.split("_"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--delivery-dir", required=True)
    p.add_argument("--reference", required=True, help="the muon-only cropped ROOT file")
    p.add_argument("--out", required=True)
    p.add_argument("--skip-upstream-name-check", action="store_true")
    args = p.parse_args()

    ddir = Path(args.delivery_dir)
    uncropped = sorted(ddir.glob("*_bumpnet.root"))
    cropped = sorted(ddir.glob("*_bumpnet_cropped.root"))
    if len(uncropped) != 1 or len(cropped) != 1:
        raise SystemExit(f"expected exactly one uncropped and one cropped ROOT file in "
                         f"{ddir}; found {len(uncropped)} and {len(cropped)}")
    uncropped, cropped = uncropped[0], cropped[0]

    report = {"what": "D2 delivery read-back checks and D3 counts vs the muon-only delivery",
              "uncropped": str(uncropped), "cropped": str(cropped),
              "reference": str(args.reference), "checks": {}, "failures": []}

    def check(name, ok, detail=""):
        report["checks"][name] = {"pass": bool(ok), "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        if not ok:
            report["failures"].append(name)

    hists_u, keys_u = read_histograms(uncropped)
    hists_c, keys_c = read_histograms(cropped)
    report["n_histograms_uncropped"] = len(hists_u)
    report["n_histograms_cropped"] = len(hists_c)

    # ---- names parse, and no duplicates ---------------------------------
    unparsed = [n for n in hists_u if parse_name(n) is None]
    check("every histogram name matches the upstream ROI_mass_<combo>_cat_<fs>_width_<w> shape",
          not unparsed, f"{len(unparsed)} unparsed, e.g. {unparsed[:3]}")
    check("every name ends with _width_10.0",
          all(n.endswith("_width_10.0") for n in hists_u),
          f"{sum(1 for n in hists_u if not n.endswith('_width_10.0'))} do not")
    check("no duplicate histogram names (uncropped)",
          len(set(keys_u)) == len(keys_u),
          f"{len(keys_u)} keys, {len(set(keys_u))} distinct")
    check("no duplicate histogram names (cropped)",
          len(set(keys_c)) == len(keys_c),
          f"{len(keys_c)} keys, {len(set(keys_c))} distinct")
    check("the cropped file holds exactly the same names as the uncropped one",
          set(hists_u) == set(hists_c),
          f"only-uncropped {len(set(hists_u) - set(hists_c))}, "
          f"only-cropped {len(set(hists_c) - set(hists_u))}")

    # ---- no empty histograms, bin edges ---------------------------------
    empty_u = [n for n, (v, _e) in hists_u.items() if float(v.sum()) == 0.0]
    check("no histogram is empty (uncropped)", not empty_u,
          f"{len(empty_u)} empty, e.g. {empty_u[:3]}")
    empty_c = [n for n, (v, _e) in hists_c.items() if float(v.sum()) == 0.0]
    check("no histogram is empty (cropped)", not empty_c, f"{len(empty_c)} empty")

    bad_edges = []
    for n, (_v, e) in hists_u.items():
        if abs(e[0] - FIXED_MASS_MIN_GEV) > 1e-6 or abs(e[-1] - FIXED_MASS_MAX_GEV) > 1e-6 \
                or not np.allclose(np.diff(e), BIN_WIDTH_GEV, atol=1e-6):
            bad_edges.append(n)
    check(f"uncropped bin edges are exactly {BIN_WIDTH_GEV} GeV over "
          f"{FIXED_MASS_MIN_GEV}-{FIXED_MASS_MAX_GEV} GeV",
          not bad_edges, f"{len(bad_edges)} wrong, e.g. {bad_edges[:3]}")
    bad_pitch = [n for n, (_v, e) in hists_c.items()
                 if not np.allclose(np.diff(e), BIN_WIDTH_GEV, atol=1e-6)]
    check(f"cropped histograms keep the {BIN_WIDTH_GEV} GeV pitch",
          not bad_pitch, f"{len(bad_pitch)} wrong, e.g. {bad_pitch[:3]}")

    # ---- >= 100 events per final state ----------------------------------
    per_fs = {}
    for n, (v, _e) in hists_u.items():
        info = parse_name(n)
        if info is None:
            continue
        fs = final_state_from_cat(info["cat"])
        per_fs.setdefault(fs, 0.0)
        per_fs[fs] += float(v.sum())
    thin = {fs: int(tot) for fs, tot in per_fs.items() if tot < MIN_EVENTS_PER_FINAL_STATE}
    check(f"every final state has >= {MIN_EVENTS_PER_FINAL_STATE} entries summed over its "
          "histograms", not thin, f"{len(thin)} below, e.g. {list(thin.items())[:3]}")
    report["n_final_states"] = len(per_fs)

    # ---- upstream's own naming code -------------------------------------
    if not args.skip_upstream_name_check:
        from studies.cms_datasets.tests.test_electron_datasets import upstream_names
        pairs = []
        for n in sorted(hists_u):
            info = parse_name(n)
            if info is None:
                continue
            pairs.append([final_state_from_cat(info["cat"]), info["im"], BIN_WIDTH_GEV])
        try:
            commit, up = upstream_names(pairs, [])
            mismatches = [(e["fs"], e["im"], e["full"]) for e in up["names"]
                          if e["full"] not in hists_u]
            check(f"every delivered name equals what UPSTREAM's own naming code produces "
                  f"(upstream master {commit[:7]}, {len(pairs)} names)",
                  not mismatches, f"{len(mismatches)} mismatch, e.g. {mismatches[:3]}")
            report["upstream_commit"] = commit
            report["upstream_roi_fstring"] = up["roi_fstring"]
            report["n_names_checked_against_upstream"] = len(pairs)
        except Exception as exc:                                   # noqa: BLE001
            check("upstream naming code could be fetched and called", False, str(exc)[:300])

    # ---- D3: counts vs the muon-only delivery ---------------------------
    ref_hists, _ref_keys = read_histograms(Path(args.reference))
    ref_per_fs = {}
    for n, (v, _e) in ref_hists.items():
        info = parse_name(n)
        if info is None:
            continue
        fs = final_state_from_cat(info["cat"])
        ref_per_fs[fs] = ref_per_fs.get(fs, 0.0) + float(v.sum())

    def has_electrons(fs: str) -> bool:
        for field in fs.split("_"):
            if field.endswith("e"):
                return int(field[:-1]) > 0
        return False

    n_entries_u = int(sum(float(v.sum()) for v, _e in hists_u.values()))
    n_entries_c = int(sum(float(v.sum()) for v, _e in hists_c.values()))
    n_entries_ref = int(sum(ref_per_fs.values()))
    with_e = {fs: t for fs, t in per_fs.items() if has_electrons(fs)}
    without_e = {fs: t for fs, t in per_fs.items() if not has_electrons(fs)}
    hist_with_e = sum(1 for n in hists_u if has_electrons(final_state_from_cat(parse_name(n)["cat"])))

    common = sorted(set(per_fs) & set(ref_per_fs))
    comparison = []
    flagged = []
    for fs in common:
        new, old = per_fs[fs], ref_per_fs[fs]
        rel = (new - old) / old * 100.0 if old else None
        row = {"final_state": fs, "entries_new": int(new), "entries_muon_only": int(old),
               "difference": int(new - old), "relative_change_pct": (None if rel is None
                                                                     else round(rel, 4)),
               "has_electrons": has_electrons(fs)}
        comparison.append(row)
        if (not has_electrons(fs)) and rel is not None and abs(rel) > ZERO_ELECTRON_FLAG_PCT:
            flagged.append(row)
    comparison.sort(key=lambda r: -abs(r["relative_change_pct"] or 0.0))

    report["d3"] = {
        "n_histograms": {"new_uncropped": len(hists_u), "new_cropped": len(hists_c),
                         "muon_only": len(ref_hists)},
        "n_final_states": {"new": len(per_fs), "muon_only": len(ref_per_fs)},
        "n_entries": {"new_uncropped": n_entries_u, "new_cropped": n_entries_c,
                      "muon_only": n_entries_ref},
        "electron_content": {
            "n_final_states_with_electrons": len(with_e),
            "n_final_states_without_electrons": len(without_e),
            "n_histograms_with_electrons": hist_with_e,
            "n_histograms_without_electrons": len(hists_u) - hist_with_e,
            "entries_in_final_states_with_electrons": int(sum(with_e.values())),
            "entries_in_final_states_without_electrons": int(sum(without_e.values())),
        },
        "n_final_states_common": len(common),
        "n_final_states_only_new": len(set(per_fs) - set(ref_per_fs)),
        "n_final_states_only_muon_only": len(set(ref_per_fs) - set(per_fs)),
        "final_states_only_muon_only": sorted(set(ref_per_fs) - set(per_fs)),
        "comparison_sorted_by_relative_change": comparison,
        "zero_electron_final_states_changing_more_than_1pct": flagged,
        "n_zero_electron_final_states_flagged": len(flagged),
    }
    report["per_final_state_entries_new"] = {k: int(v) for k, v in sorted(per_fs.items())}

    print(f"\nD3: histograms {len(hists_u)} (muon-only {len(ref_hists)}); "
          f"final states {len(per_fs)} (muon-only {len(ref_per_fs)}); "
          f"entries {n_entries_u} (muon-only {n_entries_ref})")
    print(f"    with electrons: {len(with_e)} final states, {hist_with_e} histograms")
    print(f"    0-electron final states changing >1%: {len(flagged)}")
    for row in flagged[:10]:
        print(f"      {row['final_state']}: {row['entries_muon_only']} -> "
              f"{row['entries_new']} ({row['relative_change_pct']:+.2f}%)")

    report["all_d2_checks_pass"] = not report["failures"]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nall D2 checks pass = {report['all_d2_checks_pass']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
