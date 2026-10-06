"""
Compare two delivery ROOT files exhaustively: histogram names and, for every
shared name, bin-by-bin contents and bin edges.

Used by the upstream-names task for three separate comparisons:
  - pilot delivery built from the NEW native shards vs built from the OLD
    5 Oct shards through the legacy conversion (must be identical);
  - a pre-existing invocation re-run with the new code vs the file it
    produced on 5 Oct (must be identical -- proves old behaviour unchanged);
  - the 5 Oct full delivery vs the new one (names converted; the 5 Oct
    histograms must all reappear with identical contents).

Usage:
    python compare_root_files.py --a <file> --b <file> [--convert-a-names]
        [--allow-b-extra] [--json <out>]

--convert-a-names   apply the legacy final-state conversion to A's names
                    before comparing (use when A is a pre-change file).
--allow-b-extra     B may contain histograms A does not; they are reported
                    rather than treated as a failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import uproot  # noqa: E402

from studies.cms_datasets.deliver.build_muon_combined_delivery import (  # noqa: E402
    convert_legacy_fs_label,
)

FAILURES = []


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
            name = key.split(";")[0]
            obj = f[key]
            out[name] = (np.asarray(obj.values(), dtype=float),
                         np.asarray(obj.axis().edges(), dtype=float))
    return out


def convert_root_key(key: str) -> str:
    """ROI_mass_<combo>_cat_<fs-with-x>_width_10 -> the same with the photon
    and tau fields removed, i.e. what the name becomes under the upstream
    format. Works on the 'x'-suffixed cat part."""
    if "_cat_" not in key:
        return key
    head, rest = key.split("_cat_", 1)
    suffix = ""
    for marker in ("_width_10", "_width_10.0"):
        if rest.endswith(marker):
            suffix, rest = marker, rest[: -len(marker)]
            break
    # rest is like 0ex_2mx_5jx_0gx_0tx_1bx -> strip the trailing x, convert, re-add
    fields = rest.split("_")
    plain = "_".join(f[:-1] if f.endswith("x") else f for f in fields)
    converted = convert_legacy_fs_label(plain)
    new_rest = "_".join(f"{tok}x" for tok in converted.split("_"))
    return f"{head}_cat_{new_rest}{suffix}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--label-a", default="A")
    p.add_argument("--label-b", default="B")
    p.add_argument("--convert-a-names", action="store_true")
    p.add_argument("--allow-b-extra", action="store_true")
    p.add_argument("--json")
    args = p.parse_args()

    a_raw = load(Path(args.a))
    b = load(Path(args.b))
    print(f"{args.label_a}: {len(a_raw)} histograms  ({args.a})")
    print(f"{args.label_b}: {len(b)} histograms  ({args.b})")

    if args.convert_a_names:
        a = {}
        collisions = []
        for k, v in a_raw.items():
            ck = convert_root_key(k)
            if ck in a:
                collisions.append((ck, k))
            a[ck] = v
        check("converting A's names produces no duplicates", not collisions,
              f"{len(collisions)} collisions: {collisions[:2]}")
        check("conversion preserves the histogram count",
              len(a) == len(a_raw), f"{len(a_raw)} -> {len(a)}")
    else:
        a = a_raw

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    check(f"every {args.label_a} histogram is present in {args.label_b}",
          not only_a, f"{len(only_a)} missing, first: {only_a[:3]}")
    if args.allow_b_extra:
        print(f"       {args.label_b} has {len(only_b)} histogram(s) "
              f"{args.label_a} does not (allowed)")
    else:
        check(f"{args.label_b} has no histogram {args.label_a} lacks",
              not only_b, f"{len(only_b)} extra, first: {only_b[:3]}")

    shared = sorted(set(a) & set(b))
    bad_vals, bad_edges = [], []
    for name in shared:
        av, ae = a[name]
        bv, be = b[name]
        if av.shape != bv.shape or not np.array_equal(av, bv):
            bad_vals.append(name)
        elif ae.shape != be.shape or not np.allclose(ae, be, rtol=0, atol=1e-9):
            bad_edges.append(name)
    check(f"all {len(shared)} shared histograms have identical bin contents",
          not bad_vals, f"{len(bad_vals)} differ, first: {bad_vals[:3]}")
    check(f"all {len(shared)} shared histograms have identical bin edges",
          not bad_edges, f"{len(bad_edges)} differ, first: {bad_edges[:3]}")

    total_a = sum(int(v.sum()) for v, _e in a.values())
    total_b = sum(int(v.sum()) for v, _e in b.values())
    print(f"       total entries: {args.label_a}={total_a:,}  {args.label_b}={total_b:,}")

    result = {
        "a": args.a, "b": args.b,
        "n_a": len(a_raw), "n_b": len(b), "n_shared": len(shared),
        "only_a": only_a[:50], "n_only_a": len(only_a),
        "only_b": only_b[:50], "n_only_b": len(only_b),
        "n_differing_contents": len(bad_vals), "n_differing_edges": len(bad_edges),
        "total_entries_a": total_a, "total_entries_b": total_b,
        "failures": FAILURES,
    }
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.json}")

    if FAILURES:
        print(f"\n{len(FAILURES)} CHECK(S) FAILED")
        sys.exit(1)
    print("\nALL COMPARISON CHECKS PASSED")


if __name__ == "__main__":
    main()
